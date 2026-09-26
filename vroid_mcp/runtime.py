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


def save_destination(lab: pathlib.Path, filename: str) -> pathlib.Path:
    """A single filename in saves/, never an absolute path or alternate stream."""
    if not filename or any(ord(c)<32 or c in '\\/:<>"|?*' for c in filename) or filename.rstrip(' .') != filename:
        raise ValueError('Use a plain .vroid filename without path separators')
    if not filename.lower().endswith('.vroid') or filename in ('.vroid', '..vroid'):
        raise ValueError('A nonempty .vroid filename is required')
    if filename.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]}:
        raise ValueError('Reserved Windows filename')
    folder = lab.resolve() / 'saves'
    folder.mkdir(exist_ok=True)
    if folder.resolve() != folder:
        raise ValueError('The saves directory must not be a link or junction')
    destination = folder / filename
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Refusing to overwrite an existing file: ' + filename)
    return destination


class Runtime:
    """One Frida owner per lab. It only spawns and owns the designated copy."""
    def __init__(self, lab: pathlib.Path, bridge_js: pathlib.Path | None = None):
        self.lab = lab.resolve()
        self.exe = self.lab / 'app' / 'VRoidStudio.exe'
        self.bridge_js = bridge_js or PROJECT / 'node_modules/frida-il2cpp-bridge/dist/index.js'
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

    def start(self) -> None:
        if os.name != 'nt':
            raise RuntimeError('This prototype is validated only on Windows')
        import msvcrt
        if not self.exe.is_file() or not self.bridge_js.is_file():
            raise FileNotFoundError('VRoid copy or frida-il2cpp-bridge is missing')
        # Reject a junction/symlink that could redirect app/ to the original install.
        if self.exe.resolve() != self.exe or (self.lab/'app').resolve() != self.lab/'app':
            raise ValueError('app/ must be a physical copy, not a link')
        digest=hashlib.sha256((self.lab/'app/GameAssembly.dll').read_bytes()).hexdigest()
        if digest != TESTED_ASSEMBLY_SHA256:
            raise RuntimeError('Untested VRoid binary: refusing native calls')
        self.file_lock=(self.lab/'.mcp-owner.lock').open('a+b')
        self.file_lock.seek(0);self.file_lock.write(b'0');self.file_lock.flush();self.file_lock.seek(0)
        try:msvcrt.locking(self.file_lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            self.file_lock.close();self.file_lock=None
            raise RuntimeError('Another MCP process already owns this lab')
        self.run_dir.mkdir(parents=True)
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
            parts=['const PROBE='+json.dumps(config)+';',
                   (PROJECT/'agent/isolate.js').read_text(encoding='utf-8'),
                   self.bridge_js.read_text(encoding='utf-8'),
                   (PROJECT/'agent/bootstrap.js').read_text(encoding='utf-8'),
                   (PROJECT/'agent/parameters.js').read_text(encoding='utf-8'),
                   (PROJECT/'agent/operations.js').read_text(encoding='utf-8')]
            self.script=self.session.create_script('\n'.join(parts))
            self.script.on('message',lambda message,data:self._event({'event':'agent','message':message}))
            self.script.load();self.device.resume(self.pid)
            self._event({'event':'spawned-copy','pid':self.pid,'exe':str(self.exe)})
        except BaseException:
            self.close();raise

    async def _call(self, operation: str, args: dict | None = None) -> Any:
        if self.dead or self.script is None:
            raise RuntimeError('COPY_DISCONNECTED: restart the MCP server')
        if self.uncertain and operation != 'status':
            raise RuntimeError('PREVIOUS_CALL_UNCERTAIN: restart; do not retry a mutation')
        try:
            return await asyncio.wait_for(asyncio.to_thread(self.script.exports_sync.call,operation,args or {}),30)
        except asyncio.TimeoutError:
            self.uncertain=True
            raise RuntimeError('Native call timed out; result is uncertain and further calls are blocked')

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

    async def status(self) -> dict:
        async with self.lock:
            if self.dead:
                return {'model_ready':False,'connected':False,'writes_blocked':True,
                        'reason':'COPY_DISCONNECTED','recovery':'restart_session requires discard_unsaved=true'}
            try:
                status=await self._call('status')
            except frida.InvalidOperationError as error:
                if 'script has been destroyed' not in str(error):
                    raise
                self.dead=True
                return {'model_ready':False,'connected':False,'writes_blocked':True,
                        'reason':'COPY_DISCONNECTED','recovery':'restart_session requires discard_unsaved=true'}
            status.update(connected=True,writes_blocked=self.uncertain)
            return status

    async def list_face_params(self) -> dict:
        return await self.list_params('face')

    async def list_params(self, area: str) -> dict:
        if area not in ('face','body','clothing'):raise ValueError('Unsupported parameter area')
        async with self.lock:return await self._call('list_'+area+'_params')

    async def set_face_params(self, expected_model: str, changes: list[dict]) -> dict:
        return await self.set_params('face',expected_model,changes)

    async def set_params(self, area: str, expected_model: str, changes: list[dict]) -> dict:
        if area not in ('face','body','clothing'):raise ValueError('Unsupported parameter area')
        async with self.lock:
            result=await self._call('set_'+area+'_params',{'expected_model':expected_model,'changes':changes})
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
        async with self.lock:
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

    async def reopen_for_test(self, path: pathlib.Path) -> dict:
        resolved=path.resolve()
        if not resolved.is_relative_to(self.lab) or not resolved.is_file():raise ValueError('Only lab models may be opened')
        async with self.lock:
            await self._task(await self._call('open_model',{'path':str(resolved)}))
            return await self._settle()

    def close(self) -> None:
        # Kill only the process returned by this instance's spawn. No name-based attach/kill.
        try:
            if self.pid is not None and self.device is not None and not self.dead:
                try:self.device.kill(self.pid)
                except frida.ProcessNotFoundError:pass
        finally:
            self.dead=True
            if self.file_lock:
                import msvcrt
                self.file_lock.seek(0);msvcrt.locking(self.file_lock.fileno(),msvcrt.LK_UNLCK,1)
                self.file_lock.close();self.file_lock=None
