"""Focused checks for structural operations, photo mode switching and clean capture."""
import asyncio,base64,json,sys
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def run(lab,model,output):
    output.mkdir(parents=True,exist_ok=True);steps=[]
    def record(name,**data):
        steps.append({'name':name,**data});print(json.dumps(steps[-1]),flush=True)
        (output/'result.json').write_text(json.dumps(steps,indent=2),encoding='utf8')
    project=Path(__file__).resolve().parents[1]
    with (output/'stderr.log').open('w') as log:
        async with stdio_client(StdioServerParameters(command=sys.executable,args=[str(project/'launch.py'),'--lab',str(lab),'--model',str(model)]),errlog=log) as (r,w):
            async with ClientSession(r,w,read_timeout_seconds=timedelta(seconds=90)) as s:
                await s.initialize()
                async def call(name,**args):
                    result=await s.call_tool(name,args);assert not result.isError,(name,result)
                    if name=='screenshot':return base64.b64decode(next(c for c in result.content if c.type=='image').data)
                    return result.structuredContent or json.loads(result.content[0].text)
                token=(await call('get_status'))['model_token']
                groups=await call('list_hair_bone_groups',category='HairFront')
                await call('generate_hair_bones',expected_model=token,category='HairFront')
                generated=await call('list_hair_bone_groups',category='HairFront');assert generated['groups']
                for i in range(32):
                    if {g['id'] for g in (await call('list_hair_bone_groups',category='HairFront'))['groups']}=={g['id'] for g in groups['groups']}:break
                    await call('undo',expected_model=token)
                else:raise AssertionError('Bone generation Undo did not restore original groups')
                record('bone_generation',generated=len(generated['groups']),undo_steps=i)
                presets=await call('list_hair_presets',category='HairFront')
                clear=next(p for p in presets['presets'] if p.get('clear'))
                await call('apply_hair_preset',expected_model=token,preset_id=clear['id'])
                assert not (await call('list_hair_nodes',category='HairFront'))['nodes']
                await call('undo',expected_model=token)
                assert (await call('list_hair_nodes',category='HairFront'))['nodes'];record('clear_and_restore_hair')
                (output/'clean-edit.png').write_bytes(await call('screenshot',expected_model=token,view='full_front'))
                await call('set_preview_mode',expected_model=token,mode='photo')
                ps=await call('list_parameters',domain='photo')
                async def change(changes):
                    changed=await call('set_parameters',expected_model=token,domain='photo',changes=changes);assert changed['ok'],changed
                await change([{'id':'photo/animation','value':0},{'id':'photo/animation_playing','value':False}])
                vals={p['id']:p['value'] for p in (await call('list_parameters',domain='photo'))['parameters']}
                assert vals['photo/animation']==0 and vals['photo/animation_playing'] is False;record('animation_preview')
                await change([{'id':'photo/pose','value':1},{'id':'photo/IsAutoBlink','value':False}])
                ps=await call('list_parameters',domain='photo');vals={p['id']:p['value'] for p in ps['parameters']}
                assert vals['photo/mode']==2,vals['photo/mode']
                q=next(p for p in ps['parameters'] if p['id'].startswith('photo/pose_controls/') and p['type']=='quaternion')
                await change([{'id':q['id'],'value':[0,0,.043619387,.999048222]}])
                await call('set_photo_camera',expected_model=token,position=[0,1,4],target=[0,.9,0])
                await change([{'id':'photo/camera/field_of_view','value':35}])
                (output/'clean-photo.png').write_bytes(await call('screenshot',expected_model=token,view='photo'))
                await call('set_preview_mode',expected_model=token,mode='edit');record('pose_and_clean_capture',controls=ps['total'])
                record('passed')

if __name__=='__main__':asyncio.run(run(*(Path(p).resolve() for p in sys.argv[1:4])))
