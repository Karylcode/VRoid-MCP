"""Real stdio lifecycle regression: fast discovery, native preset completion, recovery."""
import asyncio,base64,json,sys,time
from datetime import timedelta
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server,lab,output=map(Path,sys.argv[1:4]);output.mkdir(parents=True,exist_ok=True)
    evidence={'passed':False,'steps':[]}
    def record(name,**kw):
        evidence['steps'].append({'name':name,**kw})
        (output/'result.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(evidence['steps'][-1]),flush=True)
    with (output/'stderr.log').open('w',encoding='utf8') as log:
        async with stdio_client(StdioServerParameters(command=sys.executable,args=[str(server/'launch.py'),'--lab',str(lab)]),errlog=log) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=120)) as session:
                start=time.monotonic();await session.initialize();listing=await session.list_tools();elapsed=time.monotonic()-start
                record('discovery',seconds=elapsed,count=len(listing.tools))
                assert elapsed<3,'Tool discovery must not wait for Unity startup'
                async def call(name,args=None,error=False):
                    result=await session.call_tool(name,args or {})
                    assert bool(result.isError)==error,(name,result)
                    if error:return result
                    if name=='screenshot':return result
                    return result.structuredContent or json.loads(result.content[0].text)
                state=await call('get_status');token=state['model_token'];assert state['model_ready']
                presets=await call('list_hair_presets',{'category':'HairSet','limit':200})
                p=next(p for p in presets['presets'] if p['label'].endswith('/ 010'))
                result=await call('apply_hair_preset',{'expected_model':token,'preset_id':p['id']})
                assert result['settled'] and result['changed'] and not result['selected']
                assert result['confirmation']=='model_changed_without_preset_checkmark'
                assert any(g['type'].endswith('.HairTied') for g in result['active_groups'])
                assert not (await call('get_status'))['writes_blocked']
                capture=await call('screenshot',{'expected_model':token,'view':'front'})
                image=next(c for c in capture.content if c.type=='image')
                (output/'hair010.png').write_bytes(base64.b64decode(image.data))
                await call('list_face_params')
                record('hair010_does_not_poison_session',selected=False)
                await call('restart_session',{},error=True)
                assert (await call('get_status'))['model_token']==token
                record('restart_requires_explicit_discard')
                restarted=await call('restart_session',{'discard_unsaved':True})
                assert restarted['model_ready'] and restarted['model_token']!=token
                assert restarted['pid']!=state['pid']
                record('restart_over_mcp',old_pid=state['pid'],new_pid=restarted['pid'])
                # Simulate loss of this disposable test process only.
                import frida
                frida.get_local_device().kill(restarted['pid'])
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    dead=await call('get_status')
                    if not dead['connected']:break
                    await asyncio.sleep(.1)
                assert not dead['connected'] and dead['writes_blocked']
                recovered=await call('restart_session',{'discard_unsaved':True})
                assert recovered['connected'] and recovered['model_ready']
                record('disconnected_copy_recovered_over_mcp')
                evidence['passed']=True;record('passed')

asyncio.run(main())
