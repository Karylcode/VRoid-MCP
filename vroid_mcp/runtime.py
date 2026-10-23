from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import pathlib
import re
import time
import uuid
from typing import Any

import frida

PROJECT = pathlib.Path(__file__).resolve().parents[1]
TESTED_ASSEMBLY_SHA256 = '793eb5fcff3093f344ee930fbfa0c0796ed7780ac91c45bdb7ce6bd34d62fd3c'
CAPTURE_VIEWS = ('front', 'side', 'back', 'three_quarter', 'full_front', 'full_side', 'full_back', 'full_three_quarter', 'photo')


def validate_capture(views: list[str], size: int) -> None:
    if not views or len(views)>6 or len(set(views))!=len(views) or any(v not in CAPTURE_VIEWS for v in views):
        raise ValueError('Choose 1-6 distinct supported views')
    if type(size) is not int or not 256<=size<=2048:
        raise ValueError('Capture size must be an integer from 256 to 2048')


def review_folder(lab: pathlib.Path, capture_id: str) -> pathlib.Path:
    if not re.fullmatch('[0-9a-f]{32}', capture_id):
        raise ValueError('Use a capture_id returned by capture_review')
    folder=lab.resolve()/'reviews'/capture_id
    if folder.resolve()!=folder:
        raise ValueError('Review directories must not be links or junctions')
    return folder


def require_model_token(expected_model: str) -> str:
    """Every write names the model it changes; an empty token must not mean 'any model'."""
    if not isinstance(expected_model,str) or not expected_model:
        raise ValueError('EXPECTED_MODEL_REQUIRED: pass the model_token from list_face_params')
    return expected_model


def save_destination(lab: pathlib.Path, filename: str, folder_name: str = 'saves', suffix: str = '.vroid') -> pathlib.Path:
    """A single filename in saves/ (or exports/), never an absolute path or alternate stream."""
    if not filename or any(ord(c)<32 or c in '\\/:<>"|?*' for c in filename) or filename.rstrip(' .') != filename:
        raise ValueError(f'Use a plain {suffix} filename without path separators')
    if not filename.lower().endswith(suffix) or filename.lower() in (suffix, '.'+suffix):
        raise ValueError(f'A nonempty {suffix} filename is required')
    if filename.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError('Reserved Windows filename')
    folder = lab.resolve() / folder_name
    folder.mkdir(exist_ok=True)
    if folder.resolve() != folder:
        raise ValueError('The saves directory must not be a link or junction')
    destination = folder / filename
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Refusing to overwrite an existing file: ' + filename)
    return destination


def find_open_vroid(lab: pathlib.Path) -> list[dict]:
    """VRoid processes the user opened, excluding this lab's copy.

    Frida omits processes with higher privileges, so tasklist supplies every PID;
    those come back with path None and need an elevated MCP client.
    """
    import csv
    import subprocess
    app = (lab.resolve() / 'app').resolve()
    visible = {p.pid: p.parameters.get('path') for p in frida.get_local_device().enumerate_processes(scope='full')
               if p.name.lower() == 'vroidstudio.exe'}
    listing = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq VRoidStudio.exe', '/FO', 'CSV', '/NH'],
                             capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    pids = {int(row[1]) for row in csv.reader(listing.splitlines()) if len(row) > 1 and row[0].lower() == 'vroidstudio.exe'}
    found = []
    for pid in sorted(pids | visible.keys()):
        path = visible.get(pid)
        if path and pathlib.Path(path).resolve().is_relative_to(app):
            continue
        found.append({'pid': pid, 'path': path})
    return found


class Runtime:
    """One Frida owner per lab: spawns the designated copy, or attaches to a VRoid the user opened."""
    def __init__(self, lab: pathlib.Path, bridge_js: pathlib.Path | None = None):
        self.lab = lab.resolve()
        self.exe = self.lab / 'app' / 'VRoidStudio.exe'
        self.bridge_js = bridge_js or PROJECT / 'node_modules/frida-il2cpp-bridge/dist/index.js'
        self.mode = 'copy'
        self.target: str | None = None
        self.pid: int | None = None
        self.device = self.session = self.script = None
        self.lock = asyncio.Lock()
        self.file_lock = None
        self.dead = False
        self.uncertain = False
        self.events: list[dict] = []
        self.run_dir = self.lab / 'runs' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])

    def _event(self, data: dict) -> None:
        record = {'time': time.time(), **data}
        self.events.append(record)
        with (self.run_dir/'bridge.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps(record, ensure_ascii=False) + '\n')

    def _detached(self, reason, *unused) -> None:
        self.dead = True
        self._event({'event':'detached','reason':reason})

    def _own_lab(self) -> None:
        import msvcrt
        self.file_lock=(self.lab/'.mcp-owner.lock').open('a+b')
        self.file_lock.seek(0);self.file_lock.write(b'0');self.file_lock.flush();self.file_lock.seek(0)
        try:msvcrt.locking(self.file_lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            self.file_lock.close();self.file_lock=None
            raise RuntimeError('Another MCP process already owns this lab')
        self.run_dir.mkdir(parents=True)

    def _agent(self, attached: bool, probe: dict | None = None) -> str:
        parts=['const ATTACHED='+json.dumps(attached)+';',(PROJECT/'agent/traps.js').read_text(encoding='utf-8')]
        if probe is not None:
            parts+=['const PROBE='+json.dumps(probe)+';',(PROJECT/'agent/isolate.js').read_text(encoding='utf-8')]
        parts+=[self.bridge_js.read_text(encoding='utf-8'),
                (PROJECT/'agent/bootstrap.js').read_text(encoding='utf-8'),
                (PROJECT/'agent/parameters.js').read_text(encoding='utf-8'),
                (PROJECT/'agent/operations.js').read_text(encoding='utf-8')]
        return '\n'.join(parts)

    def start(self) -> None:
        if os.name != 'nt':
            raise RuntimeError('This prototype is validated only on Windows')
        if not self.exe.is_file() or not self.bridge_js.is_file():
            raise FileNotFoundError('VRoid copy or frida-il2cpp-bridge is missing')
        # Reject a junction/symlink that could redirect app/ to the original install.
        if self.exe.resolve() != self.exe or (self.lab/'app').resolve() != self.lab/'app':
            raise ValueError('app/ must be a physical copy, not a link')
        digest=hashlib.sha256((self.lab/'app/GameAssembly.dll').read_bytes()).hexdigest()
        if digest != TESTED_ASSEMBLY_SHA256:
            raise RuntimeError('Untested VRoid binary: refusing native calls')
        self._own_lab()
        for rel in ['Documents','AppData/Local','AppData/LocalLow/pixiv/VRoid Studio/custom_items',
                    'AppData/LocalLow/pixiv/VRoid Studio/XWear/Closet','AppData/Roaming','Temp']:
            (self.lab/'profile'/rel).mkdir(parents=True,exist_ok=True)
        env=dict(os.environ)
        env.update(USERPROFILE=str(self.lab/'profile'),APPDATA=str(self.lab/'profile/AppData/Roaming'),
                   LOCALAPPDATA=str(self.lab/'profile/AppData/Local'),TEMP=str(self.lab/'profile/Temp'),TMP=str(self.lab/'profile/Temp'))
        config={'root':str(self.lab),'exe':str(self.exe),'originalProfile':os.environ['USERPROFILE'],'excludedPids':[],
                'registryKey':'Software\\VRoidFaceMCP\\'+hashlib.sha256(str(self.lab).lower().encode()).hexdigest()[:16]}
        self.device=frida.get_local_device()
        try:
            argv=[str(self.exe),'-logFile',str(self.run_dir/'Player.log'),
                '-screen-fullscreen','0','-screen-width','960','-screen-height','720']
            self.pid=self.device.spawn(argv,cwd=str(self.exe.parent),env=env,stdio='pipe')
            self.session=self.device.attach(self.pid)
            self.session.on('detached',self._detached)
            self.script=self.session.create_script(self._agent(False,config))
            self.script.on('message',lambda message,data:self._event({'event':'agent','message':message}))
            self.script.load();self.device.resume(self.pid)
            self._event({'event':'spawned-copy','pid':self.pid,'exe':str(self.exe)})
        except BaseException:
            self.close();raise

    def attach(self, pid: int) -> None:
        """Attach to a VRoid the user opened. No isolation hooks: its files and settings stay its own."""
        if os.name != 'nt':
            raise RuntimeError('This prototype is validated only on Windows')
        if not self.bridge_js.is_file():
            raise FileNotFoundError('frida-il2cpp-bridge is missing')
        target=next((p for p in find_open_vroid(self.lab) if p['pid']==pid),None)
        if target is None:
            raise ValueError(f'PID {pid} is not a VRoid Studio opened outside this lab')
        if not target['path']:
            raise PermissionError(f'VRoid (PID {pid}) runs with higher privileges; run the MCP client as administrator, '
                                  'or start Steam/VRoid without administrator rights')
        exe=pathlib.Path(target['path'])
        digest=hashlib.sha256((exe.parent/'GameAssembly.dll').read_bytes()).hexdigest()
        if digest != TESTED_ASSEMBLY_SHA256:
            raise RuntimeError('Untested VRoid binary: refusing native calls')
        self._own_lab()
        self.mode='attached';self.target=str(exe)
        self.device=frida.get_local_device()
        try:
            try:self.session=self.device.attach(pid)
            except frida.PermissionDeniedError as error:
                raise PermissionError(f'Cannot attach to VRoid (PID {pid}); run the MCP client as administrator '
                                      'if VRoid runs as administrator') from error
            self.pid=pid
            self.session.on('detached',self._detached)
            self.script=self.session.create_script(self._agent(True))
            self.script.on('message',lambda message,data:self._event({'event':'agent','message':message}))
            self.script.load()
            self._event({'event':'attached','pid':pid,'exe':str(exe)})
        except BaseException:
            self.close();raise

    async def adopt(self) -> dict:
        """Find the live view models and keep the attached VRoid processing in the background."""
        async with self.lock:
            deadline=time.monotonic()+20
            while True:
                health=await asyncio.to_thread(self.script.exports_sync.health)
                if health['error']:raise RuntimeError(health['error'])
                if health['ready']:break
                if time.monotonic()>deadline:raise TimeoutError('Bridge did not become ready in the attached VRoid')
                await asyncio.sleep(.2)
            try:
                adopted=await asyncio.wait_for(asyncio.to_thread(self.script.exports_sync.adopt),30)
            except (asyncio.TimeoutError,frida.core.RPCException) as error:
                if 'MAIN_THREAD_TIMEOUT' in str(error) or isinstance(error,asyncio.TimeoutError):
                    raise TimeoutError('VRoid main thread did not respond; click the VRoid window once, then attach again') from error
                raise
            self._event({'event':'adopted',**adopted})
            return adopted

    async def _call(self, operation: str, args: dict | None = None) -> Any:
        if self.dead or self.script is None:
            if self.mode=='attached':
                raise RuntimeError('ATTACHED_VROID_DISCONNECTED: call attach_open_vroid again')
            raise RuntimeError('COPY_DISCONNECTED: restart the MCP server')
        if self.uncertain and operation != 'status':
            raise RuntimeError('PREVIOUS_CALL_UNCERTAIN: restart; do not retry a mutation')
        try:
            return await asyncio.wait_for(asyncio.to_thread(self.script.exports_sync.call,operation,args or {}),30)
        except asyncio.TimeoutError:
            self.uncertain=True
            raise RuntimeError('Native call timed out; result is uncertain and further calls are blocked')

    async def _check_model(self, expected_model: str) -> None:
        """First step of every write, before any native change: expected_model must name the open model."""
        require_model_token(expected_model)
        status=await self._call('status')
        if status.get('model_token')!=expected_model:
            raise ValueError('STALE_MODEL: list parameters again' if status.get('model_ready') else status.get('reason','MODEL_NOT_READY'))

    async def initialize(self, variant: str = 'F00', model_file: pathlib.Path | None = None) -> dict:
        async with self.lock:
            deadline=time.monotonic()+40
            while time.monotonic()<deadline:
                health=await asyncio.to_thread(self.script.exports_sync.health)
                if health['error']:raise RuntimeError(health['error'])
                if health['ready']:
                    status=await self._call('status')
                    if not status.get('reason','').startswith('Error: NOT_READY'):break
                await asyncio.sleep(.2)
            else:raise TimeoutError('VRoid initialization timed out')
            if model_file is None:
                await self._call('new_model',{'variant':variant})
            else:
                path=model_file.resolve()
                if not path.is_relative_to(self.lab) or path.suffix.lower()!='.vroid' or not path.is_file():
                    raise ValueError('Startup models must be .vroid files already inside the lab')
                await self._task(await self._call('open_model',{'path':str(path)}))
            return await self._settle()

    async def _task(self, task: dict) -> None:
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            result=await self._call('task_status',task)
            if result['completed']:
                if result['faulted'] or result['canceled']:raise RuntimeError(result.get('error','Operation canceled'))
                return
            await asyncio.sleep(.1)
        self.uncertain=True
        raise TimeoutError('Managed task did not complete; restart before further changes')

    async def _settle(self, after_frame: int = -1) -> dict:
        deadline=time.monotonic()+30
        quiet=0
        while time.monotonic()<deadline:
            result=await self._call('status')
            if result['model_ready'] and not result['updating'] and not result.get('photo_updating',False) and not result.get('command_busy',False) and (result.get('photo_active',False) or not result.get('presets_loading',False)) and result['frame']>=after_frame+2:
                quiet+=1
                if quiet>=2:return result
            else:quiet=0
            await asyncio.sleep(.1)
        self.uncertain=True
        raise TimeoutError('Model did not finish updating: '+json.dumps(result))

    def _disconnected(self) -> dict:
        if self.mode=='attached':
            return {'mode':self.mode,'target':self.target,'model_ready':False,'connected':False,'writes_blocked':True,
                    'reason':'ATTACHED_VROID_DISCONNECTED','recovery':'attach_open_vroid again, or detach_open_vroid'}
        return {'mode':self.mode,'model_ready':False,'connected':False,'writes_blocked':True,
                'reason':'COPY_DISCONNECTED','recovery':'restart_session requires discard_unsaved=true'}

    async def status(self) -> dict:
        async with self.lock:
            if self.dead:
                return self._disconnected()
            try:
                status=await self._call('status')
            except frida.InvalidOperationError as error:
                if 'script has been destroyed' not in str(error):
                    raise
                self.dead=True
                return self._disconnected()
            status.update(mode=self.mode,target=self.target or str(self.exe),connected=True,writes_blocked=self.uncertain)
            return status

    async def list_face_params(self) -> dict:
        return await self.list_params('face')

    async def list_params(self, area: str) -> dict:
        if area not in ('face','body','clothing'):raise ValueError('Unsupported parameter area')
        async with self.lock:return await self._call('list_'+area+'_params')

    async def set_face_params(self, expected_model: str, changes: list[dict], allow_out_of_ui_range: bool = False) -> dict:
        return await self.set_params('face',expected_model,changes,allow_out_of_ui_range)

    async def set_params(self, area: str, expected_model: str, changes: list[dict], allow_out_of_ui_range: bool = False) -> dict:
        if area not in ('face','body','clothing'):raise ValueError('Unsupported parameter area')
        async with self.lock:
            await self._check_model(expected_model)
            result=await self._call('set_'+area+'_params',{'expected_model':expected_model,'changes':changes,
                                                          'allow_out_of_ui_range':allow_out_of_ui_range})
            settled=await self._settle(result['frame'])
            if settled['model_token']!=expected_model:raise RuntimeError('MODEL_CHANGED_DURING_OPERATION')
            result['settled']=True
            return result

    async def list_presets(self,area: str,category: str|None=None,offset:int=0,limit:int=100) -> dict:
        if area not in ('face','body','hair','clothing'):raise ValueError('Unsupported preset area')
        async with self.lock:
            return await self._call('list_presets',{'area':area,'category':category,'offset':offset,'limit':limit,'owned_only':True})

    async def apply_preset(self,area:str,expected_model:str,preset_id:str) -> dict:
        if area not in ('face','body','hair','clothing'):raise ValueError('Unsupported preset area')
        async with self.lock:
            await self._check_model(expected_model)
            result=await self._call('apply_preset',{'area':area,'expected_model':expected_model,'preset_id':preset_id})
            await self._settle(result['frame'])
            before=result.pop('before_groups',None)
            if result.get('clear'):
                result.update(settled=True,selected=None)
                return result
            deadline=time.monotonic()+1
            while time.monotonic()<deadline:
                state=await self._call('preset_state',{'area':area,'expected_model':expected_model,'preset_id':preset_id})
                if state['selected']:
                    result.update(settled=True,selected=True);return result
                await asyncio.sleep(.15)
            # Some native hair sets are expanded into parts and no longer retain
            # a selected whole-set checkbox. The native operation has settled;
            # report the evidence without inventing selection or freezing reads.
            groups=state.get('active_groups',[])
            changed=before is not None and groups!=before
            result.update(settled=True,selected=False,changed=changed,
                          confirmation='model_changed_without_preset_checkmark' if changed else 'selection_unconfirmed',
                          active_groups=groups,
                          message='Inspect the model and screenshot; an unchecked set does not establish failure or exact preset equivalence.')
            return result

    async def parameter_call(self,operation: str,args:dict|None=None,mutating:bool=False)->dict:
        async with self.lock:
            if mutating:await self._check_model((args or {}).get('expected_model'))
            await self._settle()
            result=await self._call(operation,args or {})
            if mutating:
                settled=await self._settle(result.get('frame',-1))
                if settled['model_token']!=(args or {}).get('expected_model'):raise RuntimeError('MODEL_CHANGED_DURING_OPERATION')
                result['settled']=True
            return result

    async def set_height(self,expected_model:str,centimeters:float,tolerance_cm:float=.05)->dict:
        import math
        if not math.isfinite(centimeters) or not 20<=centimeters<=400:raise ValueError('Height must be 20..400 cm; native model range can be narrower')
        if not .01<=tolerance_cm<=.5:raise ValueError('Tolerance must be .01...5 cm')
        async with self.lock:
            await self._check_model(expected_model)
            await self._settle()
            args={'expected_model':expected_model}
            body=await self._call('list_body_params',args)
            p=next(p for p in body['parameters'] if p['id']=='body/WholeBody/002')
            initial=p['value'];x=initial;history=[]
            async def measure():return (await self._call('get_height',args))['centimeters']
            async def change(v):
                result=await self._call('set_body_params',{**args,'changes':[{'id':p['id'],'value':v}]})
                if not result['ok']:raise RuntimeError(result)
                await self._settle(result['frame'])
                return await measure()
            y=await measure()
            for i in range(14):
                history.append({'scale_parameter':x,'centimeters':y})
                if abs(y-centimeters)<=tolerance_cm:
                    return {'model_token':expected_model,'target_cm':centimeters,'measured_cm':y,'error_cm':y-centimeters,
                            'tolerance_cm':tolerance_cm,'scale_parameter':x,'samples':history,'settled':True,
                            'measurement':'VRoid native BodyHeightValue; hairstyle and model proportions can affect this measurement'}
                if len(history)==1:next_x=min(1,x+.05) if x<.95 else x-.05
                else:
                    prev=history[-2];slope=(y-prev['centimeters'])/(x-prev['scale_parameter']) if x!=prev['scale_parameter'] else 0
                    if abs(slope)<1e-6:break
                    next_x=max(p['min'],min(p['max'],x+(centimeters-y)/slope))
                if abs(next_x-x)<1e-7:break
                x=next_x;y=await change(x)
            restored=await change(initial)
            raise ValueError(f'Height did not converge within native range; original scale restored ({restored:.3f} cm)')

    async def history(self, method: str, expected_model: str, steps: int = 1) -> dict:
        if method not in ('undo','redo') or not 1<=steps<=32:raise ValueError('Invalid history operation')
        async with self.lock:
            await self._check_model(expected_model)
            for _ in range(steps):
                result=await self._call(method,{'expected_model':expected_model})
                await self._task(result);await self._settle(result['frame'])
            return await self._call('list_face_params',{'expected_model':expected_model})

    async def _capture(self, view: str, expected_model: str, size: int) -> bytes:
        result=await self._call('screenshot',{'view':view,'expected_model':expected_model,'size':size})
        data=base64.b64decode(result['base64'],validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid image from VRoid')
        if (int.from_bytes(data[16:20],'big'),int.from_bytes(data[20:24],'big'))!=(size,size):
            raise ValueError('Unexpected native capture resolution')
        return data

    async def screenshot(self, view: str, expected_model: str, size: int = 512) -> bytes:
        validate_capture([view],size)
        async with self.lock:
            await self._settle()
            prepared=await self._call('prepare_capture',{'expected_model':expected_model})
            await self._settle(prepared['frame'])
            return await self._capture(view,expected_model,size)

    async def capture_review(self, expected_model: str, views: list[str], size: int = 1024,
                             label: str = '', baseline_id: str | None = None) -> tuple[dict,list[tuple[str,bytes]]]:
        """Native views plus numeric evidence; visual quality is assessed by the caller."""
        validate_capture(views,size)
        if 'photo' in views:
            raise ValueError('Use screenshot for animated photo previews; review uses reproducible model views')
        if len(label)>80:raise ValueError('Label must be at most 80 characters')
        baseline=None;images=[]
        if baseline_id:
            previous=review_folder(self.lab,baseline_id)
            metadata=previous/'review.json'
            if metadata.resolve()!=metadata:raise ValueError('Baseline metadata must not be a link')
            baseline=json.loads(metadata.read_text(encoding='utf8'))
            if baseline['views']!=views or baseline['size']!=size:
                raise ValueError('Baseline views and size must match for a fair comparison')
            for view in views:
                source=previous/(view+'.png')
                if source.resolve()!=source:raise ValueError('Baseline images must not be links')
                data=source.read_bytes()
                if hashlib.sha256(data).hexdigest()!=baseline['images'][view]['sha256']:
                    raise ValueError('Baseline image was modified')
                images.append(('before / '+view,data))
        async with self.lock:
            status=await self._settle()
            if status['model_token']!=expected_model:raise ValueError('MODEL_CHANGED')
            if status.get('photo_active'):raise ValueError('Return to edit mode before capture_review')
            prepared=await self._call('prepare_capture',{'expected_model':expected_model})
            await self._settle(prepared['frame'])
            current=[]
            for view in views:
                current.append((view,await self._capture(view,expected_model,size)))
            state={}
            for area in ('face','body','clothing'):
                state[area]=await self._call('list_'+area+'_params',{'expected_model':expected_model})
            state['colors']=await self._call('list_parameters',{'domain':'colors','limit':200,'expected_model':expected_model})
            state['height']=await self._call('get_height',{'expected_model':expected_model})
            final=await self._call('status')
            if final['model_token']!=expected_model:raise ValueError('MODEL_CHANGED_DURING_CAPTURE')
        capture_id=uuid.uuid4().hex;folder=review_folder(self.lab,capture_id)
        folder.mkdir(parents=True,exist_ok=False)
        manifest={'capture_id':capture_id,'label':label,'model_token':expected_model,
                  'created_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'views':views,'size':size,
                  'baseline_id':baseline_id,'state':state,'images':{},
                  'visual_review_required':True,
                  'checklist':['eye and eyebrow balance','bangs obscuring eyes','hair/scalp gaps',
                               'hair/clothing intersections','head/body and limb proportions','front/side/back silhouette'],
                  'limitations':'Native rendered evidence, not an automated beauty score or geometry collision test. Hair simulation may vary between frames.'}
        for view,data in current:
            path=folder/(view+'.png');path.write_bytes(data)
            manifest['images'][view]={'path':str(path),'sha256':hashlib.sha256(data).hexdigest()}
            images.append(('after / '+view if baseline else view,data))
        if baseline:
            changes=[]
            for area in ('face','body','clothing','colors'):
                old={p['id']:p['value'] for p in baseline['state'][area]['parameters']}
                for p in state[area]['parameters']:
                    if not p.get('alias_of') and old.get(p['id'])!=p['value']:
                        changes.append({'area':area,'id':p['id'],'label':p['label'],'before':old.get(p['id']),'after':p['value']})
            manifest['parameter_changes']=changes
            manifest['baseline_same_model_token']=baseline['model_token']==expected_model
        manifest['manifest_path']=str(folder/'review.json')
        (folder/'review.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
        return manifest,images

    async def save_as(self, filename: str, expected_model: str) -> dict:
        if self.mode=='attached':
            raise ValueError('Attached to your own VRoid: save there with Ctrl+S; save_as would re-point its file path')
        async with self.lock:
            await self._check_model(expected_model)
            destination=save_destination(self.lab,filename)
            staging=destination.parent/('stage-'+uuid.uuid4().hex+'.vroid')
            await self._settle()
            await self._call('save_as',{'path':str(staging),'expected_model':expected_model})
            if not staging.is_file() or staging.stat().st_size<100:
                raise RuntimeError('VRoid did not produce a valid-sized file')
            # On Windows os.rename fails if destination exists; never use os.replace.
            os.rename(staging,destination)
            return {'path':str(destination),'bytes':destination.stat().st_size,'model_token':expected_model,
                    'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}

    async def list_start_models(self) -> dict:
        async with self.lock:
            return await self._call('list_start_models')

    async def open_start_model(self, name: str, group: str | None = None) -> dict:
        """Click a start-screen card, then wait for the model; a slow download or a dialog is reported, not fatal."""
        async with self.lock:
            requested=await self._call('open_start_model',{'name':name,'group':group})
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                status=await self._call('status')
                if status['model_ready'] and not status['updating'] and not status.get('presets_loading'):
                    return {**requested,'opened':True,'model_token':status['model_token']}
                await asyncio.sleep(.3)
            return {**requested,'opened':False,'status':status,
                    'message':'Not loaded yet: VRoid may still be downloading or showing a dialog; check get_status'}

    async def list_parts(self) -> dict:
        async with self.lock:
            await self._settle()
            return await self._call('list_parts')

    async def replace_part(self, expected_model: str, part_id: str) -> dict:
        """Swap one transferable group by id, wait for the command to finish, then confirm the part is active."""
        async with self.lock:
            await self._check_model(expected_model)
            await self._settle()
            requested=await self._call('replace_part',{'expected_model':expected_model,'part_id':part_id})
            await asyncio.sleep(.3)
            settled=await self._settle(requested['frame'])
            parts=(await self._call('list_parts'))['parts']
            if not any(p['id']==part_id for p in parts):
                raise RuntimeError('REPLACE_PART_FAILED: part is not active afterwards; VRoid logs the native error in Player.log')
            return {'part_id':part_id,'replaced':True,'model_token':settled['model_token']}

    async def save_custom_items(self, expected_model: str, types: list[str] | None = None) -> dict:
        return await self.parameter_call('save_custom_items',{'expected_model':expected_model,'types':types},True)

    async def export_vrm(self, expected_model: str, filename: str, version: int = 1) -> dict:
        """Export through VRoid's exporter into lab/exports; enters and leaves the export screen if needed."""
        if version not in (0,1):raise ValueError('version must be 0 (VRM 0.x) or 1 (VRM 1.0)')
        args={'expected_model':expected_model}
        async with self.lock:
            await self._check_model(expected_model)
            destination=save_destination(self.lab,filename,'exports','.vrm')
            await self._settle()
            state=await self._call('vrm_export_state',args)
            entered=not state['export_screen']
            if entered:await self._call('enter_vrm_export',args)
            deadline=time.monotonic()+60
            while not (await self._call('vrm_export_state',args))['ready']:
                if time.monotonic()>deadline:raise TimeoutError('VRM export screen did not become ready')
                await asyncio.sleep(.3)
            try:
                await self._call('start_vrm_export',{**args,'version':version,'path':str(destination)})
                deadline=time.monotonic()+900
                while True:
                    status=await self._call('vrm_export_status')
                    if not status['running']:break
                    if time.monotonic()>deadline:raise TimeoutError('VRM export did not finish within 15 minutes')
                    await asyncio.sleep(1)
            finally:
                if entered:await self._call('leave_vrm_export',args)
            if not status.get('done') or not destination.is_file():
                raise RuntimeError('VRM_EXPORT_FAILED: VRoid reported failure; see its Player.log')
            return {'path':str(destination),'bytes':destination.stat().st_size,'version':version,
                    'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()}

    async def reopen_for_test(self, path: pathlib.Path) -> dict:
        if self.mode=='attached':raise ValueError('Never open another model in the user\'s own VRoid')
        resolved=path.resolve()
        if not resolved.is_relative_to(self.lab) or not resolved.is_file():raise ValueError('Only lab models may be opened')
        async with self.lock:
            await self._task(await self._call('open_model',{'path':str(resolved)}))
            return await self._settle()

    def close(self) -> None:
        # Kill only the process returned by this instance's spawn. An attached VRoid is
        # only detached from: it keeps running with the user's unsaved work.
        try:
            if self.mode=='attached':
                if self.script is not None and not self.dead:
                    try:self._event({'event':'released',**self.script.exports_sync.release()})
                    except Exception as error:self._event({'event':'release-error','error':str(error)})
                    try:self.script.unload()
                    except frida.InvalidOperationError:pass
                if self.session is not None and not self.dead:
                    self.session.detach()
            elif self.pid is not None and self.device is not None and not self.dead:
                try:self.device.kill(self.pid)
                except frida.ProcessNotFoundError:pass
        finally:
            self.dead=True
            if self.file_lock:
                import msvcrt
                self.file_lock.seek(0);msvcrt.locking(self.file_lock.fileno(),msvcrt.LK_UNLCK,1)
                self.file_lock.close();self.file_lock=None
