"""Real MCP protocol test. Spawns the server, which owns only the configured copy."""
import asyncio
import base64
from datetime import timedelta
import json
from pathlib import Path
import sys
import time

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT = Path(__file__).resolve().parents[1]


async def run(lab: Path, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    checks=[]
    def record(name, **data):
        item={'name':name,**data};checks.append(item)
        print(json.dumps(item,ensure_ascii=True),flush=True)
        (output/'stdio-result.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
    params=StdioServerParameters(command=sys.executable,args=[str(PROJECT/'launch.py'),'--lab',str(lab.resolve())])
    with (output/'server-stderr.log').open('w',encoding='utf8') as errlog:
        async with stdio_client(params,errlog=errlog) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=60)) as session:
                await session.initialize()
                listing=await session.list_tools()
                assert {t.name for t in listing.tools}>={'get_status','list_face_params','set_face_params','undo','redo','screenshot','save_as',
                    'list_body_params','set_body_params','list_clothing_params','set_clothing_params',
                    'list_hair_presets','apply_hair_preset','list_clothing_presets','apply_clothing_preset'}
                record('tools_list',tools=[t.name for t in listing.tools])
                async def call(name,args=None, expect_error=False):
                    result=await session.call_tool(name,args or {})
                    assert bool(result.isError)==expect_error,(name,result)
                    if expect_error:return result
                    if name=='screenshot':return result
                    return result.structuredContent or json.loads(result.content[0].text)
                status=await call('get_status');record('status',**status)
                catalog=await call('list_face_params');token=catalog['model_token']
                selected=[]
                for kind in sorted({p['type'] for p in catalog['parameters']}):
                    p=next(p for p in catalog['parameters'] if p['type']==kind and p['alias_of'] is None)
                    target=p['min']+(p['max']-p['min'])*.7
                    selected.append({'id':p['id'],'value':target})
                record('catalog',count=catalog['count'],unique=catalog['unique_parameters'])
                await call('set_face_params',{'expected_model':'wrong-token','changes':selected},True)
                alias=next(p for p in catalog['parameters'] if p['alias_of']==selected[0]['id'])
                await call('set_face_params',{'expected_model':token,'changes':[selected[0],{'id':alias['id'],'value':selected[0]['value']}]},True)
                record('stale_token_and_duplicate_alias_rejected')
                edited=await call('set_face_params',{'expected_model':token,'changes':selected})
                assert edited['ok'] and all(abs(p['after']-c['value'])<1e-5 for p,c in zip(edited['applied'],selected))
                record('all_present_parameter_types_set',result=edited)
                undone=await call('undo',{'expected_model':token,'steps':len(selected)})
                initial={p['id']:p['value'] for p in catalog['parameters']}
                assert all(abs(p['value']-initial[p['id']])<1e-5 for p in undone['parameters'])
                redone=await call('redo',{'expected_model':token,'steps':len(selected)})
                values={p['id']:p['value'] for p in redone['parameters']}
                assert all(abs(values[p['id']]-p['value'])<1e-5 for p in selected)
                record('undo_redo_over_stdio')
                for view in ('front','side'):
                    result=await call('screenshot',{'expected_model':token,'view':view})
                    images=[item for item in result.content if item.type=='image']
                    assert len(images)==1 and images[0].mimeType=='image/png'
                    data=base64.b64decode(images[0].data,validate=True)
                    assert data.startswith(b'\x89PNG\r\n\x1a\n')
                    (output/(view+'.png')).write_bytes(data)
                    record('mcp_image',view=view,bytes=len(data))
                saved=await call('save_as',{'expected_model':token,'filename':'stdio-'+time.strftime('%Y%m%d-%H%M%S')+'.vroid'})
                assert Path(saved['path']).is_file();record('save_as_over_stdio',**saved)
                await call('save_as',{'expected_model':token,'filename':Path(saved['path']).name},True)
                statuses=[await call('get_status') for _ in range(10)]
                assert all(s['background'] and s['main_thread']==s['callback_thread'] for s in statuses)
                record('background_observation',unfocused_samples=sum(not s['focused'] for s in statuses),samples=len(statuses))
                record('passed',passed=True)


if __name__=='__main__':asyncio.run(run(Path(sys.argv[1]),Path(sys.argv[2])))
