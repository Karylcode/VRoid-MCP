import asyncio
import pytest
from vroid_mcp.runtime import Runtime, require_model_token

LIVE='session:1'
WRITES={
    'set_face_params':lambda r,t:r.set_face_params(t,[{'id':'face/x/000','value':0}]),
    'set_body_params':lambda r,t:r.set_params('body',t,[{'id':'body/x/000','value':0}]),
    'set_clothing_params':lambda r,t:r.set_params('clothing',t,[{'id':'clothing/x/000','value':0}]),
    'apply_preset':lambda r,t:r.apply_preset('hair',t,'hair/HairSet/x'),
    'set_parameters':lambda r,t:r.parameter_call('set_parameters',{'expected_model':t,'domain':'colors','changes':[]},True),
    'set_height':lambda r,t:r.set_height(t,160),
    'undo':lambda r,t:r.history('undo',t),
    'redo':lambda r,t:r.history('redo',t),
    'save_as':lambda r,t:r.save_as('character.vroid',t),
    'replace_part':lambda r,t:r.replace_part(t,'x.transferablegroup'),
    'save_custom_items':lambda r,t:r.save_custom_items(t),
    'export_vrm':lambda r,t:r.export_vrm(t,'character.vrm'),
}


def fake_runtime(lab,status):
    """A Runtime whose native bridge answers only status and fails the test on any other call."""
    runtime=Runtime(lab);calls=[]
    async def call(operation,args=None):
        calls.append(operation)
        if operation!='status':raise AssertionError('native call before the model check: '+operation)
        return status
    runtime._call=call
    return runtime,calls


@pytest.mark.parametrize('token',['',None,0])
def test_missing_token_is_rejected(token):
    with pytest.raises(ValueError,match='EXPECTED_MODEL_REQUIRED'):require_model_token(token)


@pytest.mark.parametrize('tool',WRITES)
@pytest.mark.parametrize('token',['','session:0'])
def test_write_refuses_empty_or_stale_token_before_native_calls(tmp_path,tool,token):
    runtime,calls=fake_runtime(tmp_path,{'model_ready':True,'model_token':LIVE})
    with pytest.raises(ValueError,match='EXPECTED_MODEL_REQUIRED' if not token else 'STALE_MODEL'):
        asyncio.run(WRITES[tool](runtime,token))
    assert set(calls)<={'status'}
    assert not (tmp_path/'saves').exists() and not (tmp_path/'exports').exists()


def test_write_refused_while_no_model_is_open(tmp_path):
    runtime,calls=fake_runtime(tmp_path,{'model_ready':False,'reason':'Error: NO_MODEL: VRoid shows its start screen'})
    with pytest.raises(ValueError,match='NO_MODEL'):asyncio.run(runtime.replace_part(LIVE,'x.transferablegroup'))
    assert calls==['status']


def test_current_token_passes_the_check(tmp_path):
    runtime,calls=fake_runtime(tmp_path,{'model_ready':True,'model_token':LIVE})
    asyncio.run(runtime._check_model(LIVE))
    assert calls==['status']
