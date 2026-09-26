"""Runs the actual native bridge on a newly spawned copy, never an existing VRoid process."""
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from vroid_mcp.runtime import Runtime


async def run(lab:Path, destination:Path):
    destination.mkdir(parents=True,exist_ok=True)
    runtime=Runtime(lab)
    results={'started':time.strftime('%Y-%m-%dT%H:%M:%S'),'steps':[]}
    def record(name,**data):
        item={'name':name,**data};results['steps'].append(item);print(json.dumps(item,ensure_ascii=True),flush=True)
        (destination/'live-result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        runtime.start();record('spawn',pid=runtime.pid,run_dir=str(runtime.run_dir))
        status=await runtime.initialize();assert status['background'] and status['main_thread']==status['callback_thread']
        record('initialized',**status)
        catalog=await runtime.list_face_params();token=catalog['model_token']
        assert catalog['count']==214 and catalog['unique_parameters']==92
        (destination/'face-parameters.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
        record('catalog',count=catalog['count'],unique=catalog['unique_parameters'])
        before={p['id']:p['value'] for p in catalog['parameters']}
        baseline=await runtime.screenshot('front',token);(destination/'front-before.png').write_bytes(baseline)
        changes=[{'id':'face/FaceSet/000','value':.65},{'id':'face/FaceSet/001','value':.35}]
        try:await runtime.set_face_params(token,[changes[0],{'id':'face/FaceSet/001','value':1e8}])
        except Exception as e:record('invalid_batch_rejected',error=str(e))
        else:raise AssertionError('invalid batch accepted')
        unchanged=await runtime.list_face_params();assert all(abs(p['value']-before[p['id']])<1e-6 for p in unchanged['parameters'])
        result=await runtime.set_face_params(token,changes);assert result['ok'];record('batch_set',result=result)
        image=await runtime.screenshot('front',token);(destination/'front-after.png').write_bytes(image)
        assert image!=baseline
        (destination/'side-after.png').write_bytes(await runtime.screenshot('side',token))
        record('native_images',before_bytes=len(baseline),after_bytes=len(image))
        undo_steps=0
        for _ in changes:
            restored=await runtime.history('undo',token);undo_steps+=1
            vals={p['id']:p['value'] for p in restored['parameters']}
            record('undo_step',step=undo_steps,values={c['id']:vals[c['id']] for c in changes})
            if all(abs(vals[c['id']]-before[c['id']])<1e-6 for c in changes):break
        assert all(abs(vals[c['id']]-before[c['id']])<1e-6 for c in changes)
        redone=await runtime.history('redo',token,undo_steps);vals={p['id']:p['value'] for p in redone['parameters']}
        assert all(abs(vals[c['id']]-c['value'])<1e-6 for c in changes)
        record('undo_redo',native_steps=undo_steps)
        filename='acceptance-'+time.strftime('%Y%m%d-%H%M%S')+'.vroid'
        saved=await runtime.save_as(filename,token);record('save_as',**saved)
        try:await runtime.save_as(filename,token)
        except FileExistsError:pass
        else:raise AssertionError('existing file overwritten')
        assert hashlib.sha256(Path(saved['path']).read_bytes()).hexdigest()==saved['sha256']
        record('overwrite_rejected')
        reopened=await runtime.reopen_for_test(Path(saved['path']));assert reopened['model_token']!=token
        restored=await runtime.list_face_params();vals={p['id']:p['value'] for p in restored['parameters']}
        assert all(abs(vals[c['id']]-c['value'])<1e-6 for c in changes)
        try:await runtime.set_face_params(token,changes)
        except Exception:pass
        else:raise AssertionError('stale model accepted')
        record('reopen_persists_and_old_token_rejected',new_model_token=restored['model_token'])
        gc_catalog=await runtime._call('gc_check')
        assert gc_catalog['count']==catalog['count']
        record('registered_main_thread_gc_and_retained_handles',parameters=gc_catalog['count'])
        background_samples=0
        for _ in range(20):
            state=await runtime.status();assert state['background'] and state['main_thread']==state['callback_thread']
            background_samples+=not state['focused']
            await runtime.list_face_params()
        record('repeated_background_calls',round_trips=40,unfocused_samples=background_samples)
        log=(runtime.run_dir/'Player.log').read_text(encoding='utf-8',errors='replace')
        assert 'Crash!!!' not in log and 'Collecting from unknown thread' not in log and not runtime.dead
        record('no_gc_crash_in_acceptance_run')
        results['passed']=True
    except BaseException as e:
        results['passed']=False;record('failure',error=repr(e));raise
    finally:
        runtime.close();results['finished']=time.strftime('%Y-%m-%dT%H:%M:%S')
        (destination/'live-result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':asyncio.run(run(Path(sys.argv[1]),Path(sys.argv[2])))
