"""Actual MCP review protocol, native rendering, before/after evidence and guards."""
import asyncio
import base64
import json
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server,lab,output,model=map(lambda p:Path(p).resolve(),sys.argv[1:5])
    output.mkdir(parents=True,exist_ok=True)
    evidence={'passed':False,'steps':[]}
    def record(name,**values):
        evidence['steps'].append({'name':name,**values})
        (output/'result.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(evidence['steps'][-1],ensure_ascii=False),flush=True)
    with (output/'stderr.log').open('w',encoding='utf8') as log:
        async with stdio_client(StdioServerParameters(command=sys.executable,args=[str(server/'launch.py'),'--lab',str(lab),'--model',str(model)]),errlog=log) as (read,write):
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=120)) as session:
                await session.initialize()
                catalog=await session.list_tools()
                assert 'capture_review' in {t.name for t in catalog.tools}
                record('tool_registered',count=len(catalog.tools))
                async def raw(name,args=None,error=False):
                    result=await session.call_tool(name,args or {})
                    assert bool(result.isError)==error,(name,result)
                    return result
                async def call(name,args=None):
                    r=await raw(name,args)
                    return r.structuredContent or json.loads(r.content[0].text)
                def review(result,count,size):
                    data=json.loads(result.content[0].text)
                    images=[c for c in result.content if c.type=='image']
                    assert len(images)==count
                    for image in images:
                        png=base64.b64decode(image.data)
                        assert png[:8]==b'\x89PNG\r\n\x1a\n'
                        assert int.from_bytes(png[16:20],'big')==size
                        assert int.from_bytes(png[20:24],'big')==size
                    assert data['visual_review_required'] is True
                    assert Path(data['manifest_path']).is_file()
                    return data
                state=await call('get_status');token=state['model_token']
                before=await call('list_face_params')
                baseline=review(await raw('capture_review',{'expected_model':token,'label':'Before verification edit'}),4,1024)
                assert (await call('list_face_params'))==before
                assert abs(baseline['height']['centimeters']-160)<.05
                record('four_native_views_and_persistent_evidence',capture_id=baseline['capture_id'],height=baseline['height'])
                eye=next(p for p in before['parameters'] if p['id']=='face/FaceSet/001')
                edit=await call('set_face_params',{'expected_model':token,'changes':[{'id':eye['id'],'value':eye['value']+.1}]})
                assert edit['ok']
                compared=review(await raw('capture_review',{'expected_model':token,'label':'After verification edit','baseline_id':baseline['capture_id']}),8,1024)
                assert any(p['id']==eye['id'] and p['before']!=p['after'] for p in compared['parameter_changes'])
                assert compared['baseline_same_model_token'] is True
                record('before_after_images_and_numeric_difference',changes=len(compared['parameter_changes']))
                await call('undo',{'expected_model':token})
                assert (await call('list_face_params'))==before
                for invalid in [
                    {'views':[]},{'views':['front','front']},{'views':['invalid']},
                    {'views':['photo']},{'size':2049},{'baseline_id':'../escape'},
                    {'baseline_id':baseline['capture_id'],'size':512},{'expected_model':'stale'}]:
                    await raw('capture_review',{'expected_model':token,**invalid},error=True)
                record('invalid_views_size_baseline_and_stale_token_rejected')
                shot=await raw('screenshot',{'expected_model':token,'view':'three_quarter','size':2048})
                png=base64.b64decode(next(c for c in shot.content if c.type=='image').data)
                assert int.from_bytes(png[16:20],'big')==2048
                (output/'three_quarter_2048.png').write_bytes(png)
                for view in ['front','side','back','three_quarter','full_front','full_side','full_back','full_three_quarter']:
                    r=await raw('screenshot',{'expected_model':token,'view':view,'size':256})
                    assert any(c.type=='image' for c in r.content)
                legacy=await raw('screenshot',{'expected_model':token})
                png=base64.b64decode(next(c for c in legacy.content if c.type=='image').data)
                assert int.from_bytes(png[16:20],'big')==512
                record('eight_views_256_1024_2048_and_legacy_512')
                await call('set_preview_mode',{'expected_model':token,'mode':'photo'})
                await raw('capture_review',{'expected_model':token},error=True)
                photo=await raw('screenshot',{'expected_model':token,'view':'photo','size':1024})
                png=base64.b64decode(next(c for c in photo.content if c.type=='image').data)
                assert int.from_bytes(png[16:20],'big')==1024
                await call('set_preview_mode',{'expected_model':token,'mode':'edit'})
                record('photo_size_supported_and_review_requires_edit')
                final=review(await raw('capture_review',{'expected_model':token,'label':'Refined character final','views':['front','three_quarter','side','full_front','full_side','full_back']}),6,1024)
                assert (await call('list_face_params'))==before
                assert not (await call('get_status'))['writes_blocked']
                record('final_review',manifest_path=final['manifest_path'],images=final['images'])
                evidence['passed']=True;record('passed')


asyncio.run(main())
