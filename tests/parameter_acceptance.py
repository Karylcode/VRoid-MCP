"""End-to-end typed parameter acceptance through the actual stdio MCP protocol."""
import asyncio,base64,json,sys,time
from datetime import timedelta
from pathlib import Path
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT=Path(__file__).resolve().parents[1]

async def run(lab,output):
    output.mkdir(parents=True,exist_ok=True)
    evidence={'passed':False,'steps':[]};saved=None;persist=[]
    def record(name,**data):
        evidence['steps'].append({'name':name,**data})
        (output/'result.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
        print(json.dumps({'name':name,**data},ensure_ascii=True),flush=True)
    def close(a,b):
        if isinstance(a,list):return len(a)==len(b) and all(close(x,y) for x,y in zip(a,b))
        if isinstance(a,bool):return a==b
        return abs(a-b)<2e-4
    for phase in ('edit','reopen'):
        args=[str(PROJECT/'launch.py'),'--lab',str(lab)]
        if saved:args+=['--model',saved]
        with (output/(phase+'-stderr.log')).open('w',encoding='utf8') as log:
            async with stdio_client(StdioServerParameters(command=sys.executable,args=args),errlog=log) as (read,write):
                async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=90)) as s:
                    await s.initialize()
                    async def call(name,args=None,error=False):
                        r=await s.call_tool(name,args or {})
                        assert bool(r.isError)==error,(name,r)
                        if error:return r
                        if name=='screenshot':return base64.b64decode(next(c for c in r.content if c.type=='image').data)
                        return r.structuredContent or json.loads(r.content[0].text)
                    token=(await call('get_status'))['model_token']
                    async def plist(domain,**kwargs):return await call('list_parameters',{'domain':domain,**kwargs})
                    async def update(domain,changes,**kwargs):
                        r=await call('set_parameters',{'expected_model':token,'domain':domain,'changes':changes,**kwargs})
                        assert r['ok'],r
                        vals={p['id']:p['value'] for p in (await plist(domain,**kwargs))['parameters']}
                        for c in changes:assert close(vals[c['id']],c['value']),(domain,c,vals.get(c['id']))
                        return r
                    if phase=='reopen':
                        for domain,kwargs,changes in persist:
                            ps=await plist(domain,**kwargs);vals={p['id']:p['value'] for p in ps['parameters']}
                            for c in changes:assert c['id'] in vals and close(vals[c['id']],c['value']),(domain,c,vals.get(c['id']))
                        height=await call('get_height');assert abs(height['centimeters']-160)<=.08,height
                        (output/'reopened.png').write_bytes(await call('screenshot',{'expected_model':token,'view':'full_front'}))
                        record('fresh_process_persistence',domains=[p[0] for p in persist],height=height)
                        continue
                    tools=await s.list_tools();record('tools',count=len(tools.tools),names=[t.name for t in tools.tools])
                    for area in ('face','body','hair','clothing'):
                        p=await call('list_presets',{'area':area});assert p['total']>0
                        record('presets_'+area,total=p['total'])
                    hp=await call('list_hair_presets',{'category':'HairSet'})
                    chosen=next(p for p in hp['presets'] if not p['selected'])
                    await call('apply_hair_preset',{'expected_model':token,'preset_id':chosen['id']})
                    colors=await plist('colors');assert colors['total']>=25
                    changes=[{'id':'colors/Iris/BothEyes','value':[.15,.5,.9,1.]},{'id':'colors/Hair/All','value':[.92,.72,.27,1.]}]
                    await update('colors',changes);persist.append(('colors',{},changes));record('colors',total=colors['total'])
                    await call('undo',{'expected_model':token,'steps':2});await call('redo',{'expected_model':token,'steps':2})
                    before=await plist('general')
                    await call('set_parameters',{'expected_model':token,'domain':'general','changes':[{'id':before['parameters'][0]['id'],'value':12.},{'id':before['parameters'][1]['id'],'value':1e9}]},True)
                    assert before==await plist('general')
                    gc=[{'id':before['parameters'][0]['id'],'value':11.},{'id':next(p['id'] for p in before['parameters'] if p['type']=='bool'),'value':False}]
                    await update('general',gc);persist.append(('general',{},gc));record('general',total=before['total'])
                    ex=await call('list_expressions');scope=ex['expressions'][1]['id']
                    ep=await plist('expressions',scope=scope);ec=[{'id':ep['parameters'][0]['id'],'value':23.}]
                    await update('expressions',ec,scope=scope);persist.append(('expressions',{'scope':scope},ec))
                    await call('preview_expression',{'expected_model':token,'expression':scope})
                    (output/'expression.png').write_bytes(await call('screenshot',{'expected_model':token}))
                    await call('preview_expression',{'expected_model':token});record('expressions',count=len(ex['expressions']))
                    nodes=await call('list_hair_nodes',{'category':'HairFront'});assert nodes['nodes']
                    scope=nodes['nodes'][0]['id'];kwargs={'scope':scope,'category':'HairFront'};ps=await plist('hair',**kwargs)
                    hc=[]
                    for typ in ('float','int','enum','curve','vector3'):
                        p=next(p for p in ps['parameters'] if p['type']==typ)
                        if typ=='float':v=p['min']+(p['max']-p['min'])*.4
                        elif typ=='int':v=min(p['max'],p['value']+1)
                        elif typ=='enum':v=(p['value']+1)%len(p['options'])
                        elif typ=='curve':v=[a[:] for a in p['value']];v[1][1]+=.01
                        else:v=p['value'][:];v[0]+=.001
                        hc.append({'id':p['id'],'value':v})
                    await update('hair',hc,**kwargs);persist.append(('hair',kwargs,hc));record('hair',nodes=len(nodes['nodes']),controls=ps['total'])
                    await call('edit_hair_structure',{'expected_model':token,'category':'HairFront','action':'add_procedural'})
                    expanded=await call('list_hair_nodes',{'category':'HairFront'});assert len(expanded['nodes'])>len(nodes['nodes'])
                    added=next(n for n in expanded['nodes'] if n['parent'] is None and n['id'] not in {n['id'] for n in nodes['nodes']})
                    procedural=await plist('hair',category='HairFront',scope=added['id']);assert procedural['total']>ps['total']
                    await call('undo',{'expected_model':token});assert len((await call('list_hair_nodes',{'category':'HairFront'}))['nodes'])==len(nodes['nodes'])
                    record('procedural_hair',parameters=procedural['total'])
                    bp=await plist('hair_bones',category='HairFront');p=next(p for p in bp['parameters'] if p['id'].endswith('/Stiffness'))
                    bc=[{'id':p['id'],'value':.55}];await update('hair_bones',bc,category='HairFront');persist.append(('hair_bones',{'category':'HairFront'},bc));record('hair_bones',controls=bp['total'])
                    templates=await call('list_accessory_templates');assert len(templates['templates'])>=12
                    await call('edit_accessories',{'expected_model':token,'action':'add','template_id':templates['templates'][0]['id']})
                    instances=await call('list_accessories');assert len(instances['instances'])==1,instances
                    scope=instances['instances'][0]['id'];ap=await plist('accessories',scope=scope);ac=[]
                    for typ in ('float','color','vector3'):
                        p=next(p for p in ap['parameters'] if p['type']==typ)
                        v=(p['min']+(p['max']-p['min'])*.25) if typ=='float' else ([.2,.3,.4,1.] if typ=='color' else [1.03,1.03,1.03])
                        ac.append({'id':p['id'],'value':v})
                    await update('accessories',ac,scope=scope);persist.append(('accessories',{'scope':scope},ac));record('accessory',templates=len(templates['templates']),controls=ap['total'])
                    await call('edit_accessories',{'expected_model':token,'action':'duplicate','instance_id':scope})
                    two=(await call('list_accessories'))['instances'];assert len(two)==2,two
                    duplicate=next(p['id'] for p in two if p['id']!=scope)
                    await call('edit_accessories',{'expected_model':token,'action':'remove','instance_id':duplicate})
                    assert len((await call('list_accessories'))['instances'])==1;record('accessory_duplicate_remove')
                    height=await call('set_height',{'expected_model':token,'centimeters':160.});assert abs(height['measured_cm']-160)<=.05
                    record('height',result=height)
                    await call('set_preview_mode',{'expected_model':token,'mode':'photo'})
                    photo=await plist('photo');assert photo['total']>30
                    pc=[{'id':'photo/IsAutoBlink','value':False},{'id':'photo/LightColor','value':[1.,.95,.85]},
                        {'id':'photo/pose','value':1.},{'id':'photo/effects/bloomParam/Enable','value':True}]
                    await update('photo',pc)
                    detailed=(await plist('photo'))['parameters'];pose_control=next((p for p in detailed if p['id'].startswith('photo/pose_controls/') and p['type']=='quaternion'),None)
                    assert pose_control,'Detailed pose quaternion missing'
                    await update('photo',[{'id':pose_control['id'],'value':[0.,0.,.043619387,.999048222]}])
                    record('pose_control',id=pose_control['id'])
                    await call('set_photo_camera',{'expected_model':token,'position':[0.,1.1,3.],'target':[0.,1.,0.]})
                    (output/'photo.png').write_bytes(await call('screenshot',{'expected_model':token,'view':'photo'}))
                    await call('set_preview_mode',{'expected_model':token,'mode':'edit'});record('photo',parameters=photo['total'])
                    await call('set_parameters',{'expected_model':'stale','domain':'colors','changes':changes},True)
                    status=await call('get_status');assert status['background'];record('background',focused=status['focused'])
                    for view in ('front','full_front','full_side'):(output/(view+'.png')).write_bytes(await call('screenshot',{'expected_model':token,'view':view}))
                    save=await call('save_as',{'expected_model':token,'filename':'parameters-'+time.strftime('%Y%m%d-%H%M%S')+'.vroid'});saved=save['path'];record('saved',path=saved)
    evidence['passed']=True;record('passed')

if __name__=='__main__':asyncio.run(run(Path(sys.argv[1]).resolve(),Path(sys.argv[2]).resolve()))
