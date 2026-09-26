"""Actual MCP body/hair/clothing controls, undo, rendering, and save/reload."""
import asyncio,base64,json,sys,time
from datetime import timedelta
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from vroid_mcp.runtime import Runtime

async def run(lab,output):
    output.mkdir(parents=True,exist_ok=True)
    evidence={'steps':[],'passed':False}
    def record(name,**data):
        entry={'name':name,**data};evidence['steps'].append(entry)
        (output/'result.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(entry,ensure_ascii=True),flush=True)
    params=StdioServerParameters(command=sys.executable,args=[str(PROJECT/'launch.py'),'--lab',str(lab)])
    with (output/'server.log').open('w',encoding='utf8') as errlog:
        async with stdio_client(params,errlog=errlog) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=60)) as s:
                await s.initialize();tools=await s.list_tools();assert len(tools.tools)>=15
                record('tools',names=[t.name for t in tools.tools])
                async def call(name,args=None,error=False):
                    r=await s.call_tool(name,args or {});assert bool(r.isError)==error,(name,r)
                    if error:return r
                    if name=='screenshot':
                        block=next(c for c in r.content if c.type=='image');return base64.b64decode(block.data)
                    return r.structuredContent or json.loads(r.content[0].text)
                b=await call('list_body_params');token=b['model_token'];assert b['count']==23
                changes=[{'id':b['parameters'][0]['id'],'value':.3}]
                await call('set_body_params',{'expected_model':token,'changes':[changes[0],{'id':b['parameters'][1]['id'],'value':1e9}]},True)
                assert [p['value'] for p in (await call('list_body_params'))['parameters']]==[p['value'] for p in b['parameters']]
                p=next(p for p in b['parameters'] if p['type']=='CombinedBlendShapeTransformParameterViewModel')
                changes.append({'id':p['id'],'value':p['max']*.2})
                edited=await call('set_body_params',{'expected_model':token,'changes':changes});assert edited['ok']
                record('body_parameters',count=b['count'],applied=edited['applied'])
                await call('undo',{'expected_model':token,'steps':2})
                vals={p['id']:p['value'] for p in (await call('list_body_params'))['parameters']}
                initial={p['id']:p['value'] for p in b['parameters']}
                assert all(abs(vals[c['id']]-initial[c['id']])<1e-5 for c in changes)
                await call('redo',{'expected_model':token,'steps':2});record('body_undo_redo')
                (output/'before-presets.png').write_bytes(await call('screenshot',{'expected_model':token,'view':'full_front'}))
                chosen={}
                for area,category in [('hair','HairSet'),('clothing','ClothingSet')]:
                    all_presets=await call('list_'+area+'_presets')
                    page2=await call('list_'+area+'_presets',{'offset':100})
                    assert not ({p['id'] for p in all_presets['presets']}&{p['id'] for p in page2['presets']})
                    (output/(area+'-catalog.json')).write_text(json.dumps(all_presets,ensure_ascii=False,indent=2),encoding='utf8')
                    cat=await call('list_'+area+'_presets',{'category':category})
                    preset=next(p for p in cat['presets'] if not p['selected'] and p['owned']);chosen[area]=preset['id']
                    await call('apply_'+area+'_preset',{'expected_model':token,'preset_id':'invalid'},True)
                    result=await call('apply_'+area+'_preset',{'expected_model':token,'preset_id':preset['id']})
                    assert result['selected'];record('apply_'+area,total=all_presets['total'],preset=preset['id'],result=result)
                    await call('undo',{'expected_model':token})
                    after_undo=await call('list_'+area+'_presets',{'category':category})
                    assert not next(p['selected'] for p in after_undo['presets'] if p['id']==preset['id'])
                    await call('redo',{'expected_model':token})
                    after_redo=await call('list_'+area+'_presets',{'category':category})
                    assert next(p['selected'] for p in after_redo['presets'] if p['id']==preset['id'])
                    record(area+'_undo_redo')
                cloth=await call('list_clothing_params');assert cloth['count']>0
                p=next(p for p in cloth['parameters'] if p['editable'])
                clothing_change={'id':p['id'],'value':p['max']*.3 if abs(p['value']-p['max']*.3)>1e-4 else p['min']}
                change=await call('set_clothing_params',{'expected_model':token,'changes':[clothing_change]});assert change['ok']
                assert abs(change['applied'][0]['after']-clothing_change['value'])<1e-4
                record('clothing_sliders',count=cloth['count'],applied=change['applied'])
                await call('undo',{'expected_model':token})
                undone={x['id']:x['value'] for x in (await call('list_clothing_params'))['parameters']}
                assert abs(undone[p['id']]-p['value'])<1e-4
                await call('redo',{'expected_model':token});record('clothing_slider_undo_redo')
                for view in ('front','back','full_front','full_side','full_back'):
                    png=await call('screenshot',{'expected_model':token,'view':view});assert png.startswith(b'\x89PNG')
                    (output/(view+'.png')).write_bytes(png)
                record('native_views',count=5)
                vals={p['id']:p['value'] for p in (await call('list_body_params'))['parameters']}
                assert all(abs(vals[c['id']]-c['value'])<1e-5 for c in changes)
                record('outfit_and_hair_preserve_body')
                save=await call('save_as',{'expected_model':token,'filename':'extended-'+time.strftime('%Y%m%d-%H%M%S')+'.vroid'})
                record('save',**save)
    runtime=Runtime(lab)
    try:
        runtime.start();await runtime.initialize(model_file=Path(save['path']))
        restored=await runtime.list_params('body');values={p['id']:p['value'] for p in restored['parameters']}
        assert all(abs(values[c['id']]-c['value'])<1e-5 for c in changes)
        for area,category in [('hair','HairSet'),('clothing','ClothingSet')]:
            state=await runtime._call('preset_state',{'area':area,'preset_id':chosen[area],'expected_model':restored['model_token']})
            assert state['selected'],(area,state)
        # A saved instance retains its ID; replacing the garment generates a different ID.
        clothes=await runtime.list_params('clothing');target=next(x for x in clothes['parameters'] if x['id']==clothing_change['id'])
        assert abs(target['value']-clothing_change['value'])<1e-4
        (output/'reopened.png').write_bytes(await runtime.screenshot('full_front',restored['model_token']))
        record('fresh_process_persistence',body=True,hair=True,clothing=True)
        await runtime._call('gc_check');record('gc_survives')
    finally:runtime.close()
    evidence['passed']=True;record('passed')

if __name__=='__main__':asyncio.run(run(Path(sys.argv[1]),Path(sys.argv[2])))
