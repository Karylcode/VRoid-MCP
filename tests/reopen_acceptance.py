"""Fresh-process persistence and --model initialization check."""
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vroid_mcp.runtime import Runtime


async def run(lab, saved, output):
    runtime=Runtime(lab)
    try:
        runtime.start()
        status=await runtime.initialize(model_file=saved)
        catalog=await runtime.list_face_params()
        values={p['id']:p['value'] for p in catalog['parameters']}
        assert abs(values['face/FaceSet/000']-.65)<1e-6
        assert abs(values['face/FaceSet/001']-.35)<1e-6
        data=await runtime.screenshot('front',catalog['model_token'])
        output.mkdir(parents=True,exist_ok=True)
        (output/'front-reopened.png').write_bytes(data)
        evidence={'passed':True,'source':str(saved),'status':status,'values':{k:values[k] for k in ('face/FaceSet/000','face/FaceSet/001')}}
        (output/'reopen-result.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps(evidence,ensure_ascii=True),flush=True)
    finally:runtime.close()


if __name__=='__main__':asyncio.run(run(*(Path(s) for s in sys.argv[1:4])))
