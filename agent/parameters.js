// Typed adapters for native editor parameters. No caller-supplied methods or code.
globalThis.createParameterApi = H => {
    const {model,cls,core,text,array,invokeManaged,entries,details,value,selector,categories}=H;
    const roots=new Map();
    const last=s=>s.split('.').pop();
    function seq(o){
        if(!o||o.handle.isNull())return [];
        if(o instanceof Il2Cpp.Array)return [...o];
        if(o.tryField('array'))return array(o);
        if(o.tryMethod('get_Count')&&o.tryMethod('get_Item'))return Array.from({length:o.method('get_Count').invoke()},(_,i)=>o.method('get_Item').invoke(i));
        const it=o.method('GetEnumerator').invoke(),a=[];
        try{while(it.method('MoveNext').invoke())a.push(it.method('get_Current').invoke());}
        finally{if(it.tryMethod('Dispose'))it.method('Dispose').invoke();}return a;
    }
    function cache(m,key,create){
        const id=m.token+'/'+key;
        if(!roots.has(id)){const o=create();roots.set(id,{o,hold:retain(o)});}return roots.get(id).o;
    }
    function label(o,fallback){for(const n of ['TranslatedDisplayName','Label','Name'])if(o.tryMethod('get_'+n))return text(o.method('get_'+n).invoke())||fallback;return fallback;}
    function read(o,prop,type){
        const v=o.method('get_'+prop).invoke();
        if(type==='string')return text(v);
        if(type==='curve')return seq(v.method('get_RawControlPoints').invoke()).map(p=>[p.field('x').value,p.field('y').value]);
        if(type==='screen_color')return ['_r','_g','_b'].map(k=>v.field(k).value/255);
        const keys={color:['r','g','b','a'],vector2:['x','y'],vector3:['x','y','z'],quaternion:['x','y','z','w']}[type];
        return keys?keys.map(k=>v.field(k).value):v;
    }
    function argument(type,v){
        if(type==='string')return Il2Cpp.string(v).handle;
        if(type==='screen_color')return cls('VRoid.UI','VRoid.UI.ScreenColor').method('FromRgb').invoke(...v.map(x=>x*255)).handle;
        if(type==='curve'){
            const points=Il2Cpp.array(core('Vector2'),v.length);
            v.forEach((xy,i)=>{const p=Memory.alloc(8);p.writeFloat(xy[0]);p.add(4).writeFloat(xy[1]);points.set(i,new Il2Cpp.ValueType(p,core('Vector2').type));});
            const c=cls('VRoidCore','VRoidCore.Common.Types.Curve2').alloc();
            invokeManaged(c,'.ctor',[points.handle,argument('int',64),argument('float',.001)]);return c.handle;
        }
        const a=Memory.alloc(Array.isArray(v)?v.length*4:4);
        if(Array.isArray(v))v.forEach((x,i)=>a.add(i*4).writeFloat(x));
        else if(type==='bool')a.writeU8(v?1:0);
        else if(type==='int'||type==='enum')a.writeS32(v);
        else a.writeFloat(v);return a;
    }
    function param(o,prop,id,type='float',extra={}){
        return {o,prop,data:{id,label:label(o,prop),type,value:read(o,prop,type),editable:true,...extra}};
    }
    function morph(e){const d=details(e);return {o:e.p,alias:e.canonical,prop:e.p.tryMethod('get_CombinedValue')?'CombinedValue':'ModelValue',data:{...d,type:'float',native_type:d.type}};}
    function colorEntries(vm,prefix,out){
        if(!vm||vm.handle.isNull())return;
        for(const c of seq(vm.method('get_ColorSelections').invoke())){
            for(const s of seq(c.method('get_SubColorSelections').invoke())){
                const sm=s.field('_model').value,key=last(text(sm.method('get_TranslationKey').invoke()));
                out.push(param(s,'Color',prefix+'/'+key,'color',{category:label(c,''),editable:sm.method('GetIsAvailable').invoke(model().engine),min:0,max:1,format:'RGBA floats 0..1; sRGB'}));
            }
        }
    }
    function colors(m){
        const out=[],collection=selector(m,'face').field('_categoryColorSelectionCollection').value;
        for(const c of seq(collection.field('_categoryColorSelections').value.method('get_Values').invoke())){
            const key=last(text(c.method('get_TransferableGroupType').invoke()));
            const vm=cache(m,'color/'+key,()=>{
                const o=cls('VRoid.Studio','VRoid.Studio.ColorSelection.ViewModel.CategoryColorSelection').alloc();
                invokeManaged(o,'.ctor',[m.root.method('get_Resources').invoke().handle,m.engine.handle,c.handle,m.root.method('get_ColorPalette').invoke().handle]);return o;
            });colorEntries(vm,'colors/'+key,out);
        }
        const h=m.root.method('get_HairEditor').invoke();
        selectHairCategory(m,'HairSet');
        out.push(param(h,'HairSetColor','colors/Hair/All','color',{min:0,max:1,scope:'all hair',format:'RGBA floats 0..1; sRGB'}));
        return out;
    }
    function expressionCategories(m){return seq(m.face.method('get_ExpressionParameterCategories').invoke());}
    function expressions(m,scope){
        const out=[];
        for(const c of expressionCategories(m)){
            const id=last(text(c.method('get_SynthesizedCompatKey').invoke()));if(scope&&id!==scope)continue;
            seq(c.method('get_ParameterParts').invoke()).forEach((part,i)=>seq(part.method('get_Parameters').invoke()).forEach((p,j)=>{
                out.push(param(p,'Value','expressions/'+id+'/'+i+'/'+j,'float',{category:label(c,id),part:label(part,''),min:p.method('get_MinValue').invoke(),max:p.method('get_MaxValue').invoke()}));
            }));
        }return out;
    }
    function general(m){
        const g=m.root.method('get_GeneralEditor').invoke(),out=[];
        const spec={EyeExcursionEditor:{'':['HorizontalInner','HorizontalOuter','VerticalUpper','VerticalLower']},
            OutlineParameterEditor:{HairParameterSet:['OutlineWidth'],FaceParameterSet:['OutlineWidth'],BodyParameterSet:['OutlineWidth'],AccessoryParameterSet:['OutlineWidth']},
            RimLightEditor:{HairParameterSet:['Strength','Compression'],FaceParameterSet:['Strength','Compression'],BodyParameterSet:['Strength','Compression']},
            ShadingParameterEditor:{FaceParameterSet:['NormalSmoothing','ShadingShift','ShadingToony'],HairParameterSet:['ShadingShift','ShadingToony'],BodyParameterSet:['ShadingShift','ShadingToony']},
            SpringBonePropertyEditor:{'':['ErrorReduction'],ClothingParameterSet:['Amplitude'],AccessoryParameterSet:['Amplitude'],BodyParameterSet:['Amplitude']}};
        for(const [editor,sets]of Object.entries(spec)){
            const e=g.method('get_'+editor).invoke();
            for(const [set,names]of Object.entries(sets))for(const name of names){
                const o=set?e.method('get_'+set).invoke():e;
                const bounds=name==='ShadingShift'?[-1,1]:['ShadingToony','NormalSmoothing','OutlineWidth'].includes(name)?[0,1]:[0,100];
                out.push(param(o,name,'general/'+editor+'/'+(set?set+'/':'')+name,name==='ErrorReduction'?'bool':'float',
                    {label:name,category:label(e,editor),min:bounds[0],max:bounds[1],range_source:'MCP validated operating range'}));
            }
        }return out;
    }
    function accessoryEditor(m){
        const e=m.root.method('get_AccessoryEditor').invoke();
        // Instance collections are populated only while this native feature is active.
        if(!e.method('get_IsFeatureActive').invoke())invokeManaged(e,'OnEnterFeature');
        return e;
    }
    function accessoryInstances(m){
        const e=accessoryEditor(m),out=[],seen=new Set();
        for(const c of seq(e.method('get_ShapeParameterCategories').invoke())){
            invokeManaged(e,'set_SelectedShapeParameterCategory',[c.handle]);
            for(const o of seq(e.method('get_Instances').invoke()))if(!seen.has(accessoryId(o))){seen.add(accessoryId(o));out.push(o);}
        }return out;
    }
    function accessoryId(o){return text(o.field('transferableInfo').value.method('get_Id').invoke());}
    function accessories(m,scope){
        if(!scope)throw Error('ACCESSORY_SCOPE_REQUIRED: list_accessories first');
        const out=[];
        for(const o of accessoryInstances(m)){
            const id=accessoryId(o);if(scope&&scope!==id)continue;const prefix='accessories/'+id;
            const e=accessoryEditor(m),type=text(o.field('transferableInfo').value.method('get_GroupType').invoke());
            const c=seq(e.method('get_ShapeParameterCategories').invoke()).find(c=>text(c.method('get_TransferableGroupType').invoke())===type);
            if(c)invokeManaged(e,'set_SelectedShapeParameterCategory',[c.handle]);
            invokeManaged(e,'set_SelectedInstance',[o.handle]);
            for(const p of ['IsVisible','IsEditable']){
                const entry=param(o,p,prefix+'/'+p,'bool',{label:p,category:label(o,id)});
                entry.write=v=>invokeManaged(o,p==='IsVisible'?'SetVisibility':'SetEditability',[argument('bool',v)]);out.push(entry);
            }
            const getTransform=()=>{
                const q=cls('VRoidCore','VRoidCore.Editing.Query.GetPartOriginQuery').alloc();invokeManaged(q,'.ctor',[Il2Cpp.string(id).handle]);
                const origin=invokeManaged(q,'Execute',[m.context.method('get_ActiveModel').invoke().handle]);
                return invokeManaged(origin,'get_Transform').unbox();
            };
            for(const [field,type,keys]of [['Scale','vector3',['x','y','z']],['Position','vector3',['x','y','z']],['Rotation','quaternion',['x','y','z','w']]]){
                const get=()=>{const t=getTransform().field(field).value;return keys.map(k=>t.field(k).value);};
                out.push({data:{id:prefix+'/PartOriginLocal'+field,label:'Local '+field,type,value:get(),editable:true,units:field==='Position'?'meters':undefined},read:get,write:v=>{
                    const t=getTransform(),component=t.field(field).value;keys.forEach((k,i)=>component.field(k).value=v[i]);
                    const command=cls('VRoidCore','VRoidCore.Editing.History.Command.SetPartOriginTransformCommand').alloc();
                    invokeManaged(command,'.ctor',[Il2Cpp.string(id).handle,t.handle]);invokeManaged(m.context,'ExecuteSyncCommand',[command.handle]);
                }});
            }
            const bones=seq(o.method('get_Bones').invoke());
            if(bones.length)out.push(param(o,'SelectedBoneIndex',prefix+'/bone','enum',{options:bones.map((b,i)=>({value:i,label:label(b,String(i))})),min:0,max:bones.length-1}));
            seq(o.method('get_Parameters').invoke()).forEach((p,i)=>out.push(morph({p,id:prefix+'/shape/'+i,category:label(o,id)})));
            // ShapeParameterCategory contains obsolete hard-coded group IDs; current
            // accessories expose their actual shape controls through instance.Parameters.
            colorEntries(o.method('get_CategoryColorSelection').invoke(),prefix+'/colors',out);
        }return out;
    }
    function validate(e,v){
        const d=e.data;if(!d.editable)throw Error('PARAMETER_NOT_EDITABLE: '+d.id);
        if(d.type==='curve'){
            if(!Array.isArray(v)||v.length<2||v.length>64||v.some(p=>!Array.isArray(p)||p.length!==2||p.some(x=>typeof x!=='number'||!Number.isFinite(x)||Math.abs(x)>10)))throw Error('CURVE_CONTROL_POINTS: 2..64 finite [x,y] pairs within -10..10');
            return;
        }
        if(d.type==='bool'){if(typeof v!=='boolean')throw Error('BOOLEAN_REQUIRED: '+d.id);return;}
        if(d.type==='string'){if(typeof v!=='string'||v.length>128)throw Error('INVALID_STRING');return;}
        if(['color','screen_color','vector2','vector3','quaternion'].includes(d.type)){
            const n=d.type==='vector2'?2:['vector3','screen_color'].includes(d.type)?3:4;if(!Array.isArray(v)||v.length!==n||v.some(x=>typeof x!=='number'||!Number.isFinite(x)))throw Error('INVALID_VECTOR: '+d.id);
            if(['color','screen_color'].includes(d.type)&&v.some(x=>x<0||x>1))throw Error('COLOR_RANGE');
            if(d.type==='quaternion'&&Math.abs(v.reduce((a,x)=>a+x*x,0)-1)>.01)throw Error('NORMALIZED_QUATERNION_REQUIRED');
            if((d.id.endsWith('LocalScale')||d.id.endsWith('/Scale'))&&v.some(x=>x<=0||x>100))throw Error('SCALE_RANGE: (0,100]');
            if(v.some(x=>Math.abs(x)>10000))throw Error('VECTOR_RANGE');return;
        }
        if(typeof v!=='number'||!Number.isFinite(v)||(['int','enum'].includes(d.type)&&!Number.isInteger(v)))throw Error('INVALID_NUMBER: '+d.id);
        if((d.min!==undefined&&v<d.min)||(d.max!==undefined&&v>d.max))throw Error('OUT_OF_RANGE: '+d.id);
    }
    function all(m,args){
        switch(args.domain){case 'face':case 'body':return entries(m,args.domain).map(morph);
            case 'clothing':return clothing(m);
            case 'colors':return colors(m);case 'expressions':return expressions(m,args.scope);case 'general':return general(m);
            case 'hair_bones':return hairBones(m,args);
            case 'photo':return photoParameters(m);
            case 'accessories':return accessories(m,args.scope);case 'hair':return hairParameters(m,args);
            default:throw Error('UNKNOWN_DOMAIN');}
    }
    function listParameters(args){const m=model(args.expected_model),es=all(m,args),offset=args.offset??0,limit=args.limit??200;
        if(!Number.isInteger(offset)||offset<0||!Number.isInteger(limit)||limit<1||limit>500)throw Error('INVALID_PAGINATION');
        return {model_token:m.token,domain:args.domain,scope:args.scope||null,total:es.length,next_offset:offset+limit<es.length?offset+limit:null,parameters:es.slice(offset,offset+limit).map(e=>e.data)};
    }
    function setParameters(args){
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');const m=model(args.expected_model),es=all(m,args),map=new Map(es.map(e=>[e.data.id,e]));
        if(!Array.isArray(args.changes)||args.changes.length<1||args.changes.length>64)throw Error('BATCH_SIZE: 1..64');
        const seen=new Set(),cs=args.changes.map(c=>{const e=map.get(c.id);if(!e)throw Error('UNKNOWN_PARAMETER: '+c.id);const key=e.alias||c.id;if(seen.has(key))throw Error('DUPLICATE_PARAMETER');seen.add(key);validate(e,c.value);return {e,v:c.value};});
        const applied=[];
        for(const {e,v}of cs){try{if(e.write)e.write(v);else invokeManaged(e.o,'set_'+e.prop,[argument(e.data.type,v)]);applied.push({id:e.data.id,before:e.data.value,after:e.read?e.read():read(e.o,e.prop,e.data.type)});}catch(error){return {ok:false,model_token:m.token,applied,error:String(error),frame:state.frame};}}
        return {ok:true,model_token:m.token,applied,frame:state.frame};
    }
    function selectHairCategory(m,category){
        const c=categories(m,'hair').find(c=>last(text(c.method('get_TranslationKey').invoke()))===category);
        if(!c)throw Error('UNKNOWN_HAIR_CATEGORY');
        invokeManaged(selector(m,'hair'),'set_SelectedCategory',[c.handle]);return c;
    }
    function hairEditor(m,category){
        if(!['HairFront','HairBack','AllHair','HairTied','HairSideburns','HairAhoge','HairHanege'].includes(category))throw Error('HAIR_PART_CATEGORY_REQUIRED');
        const selected=selectHairCategory(m,category);
        const h=m.root.method('get_HairEditor').invoke(),hm=h.method('get_Model').invoke();
        const types=[...selected.field('_categoryModel').value.field('transferableTypes').value];
        if(types.length!==1)throw Error('HAIR_CATEGORY_TYPE_AMBIGUOUS');
        invokeManaged(hm,'SetTransferableType',[types[0].handle]);
        let d=h.method('get_DesignEditor').invoke();
        if(d.handle.isNull()){
            d=cache(m,'hair-design',()=>{
                const o=cls('VRoid.Studio','VRoid.Studio.HairEditor.DesignEditor.ViewModel').alloc();
                invokeManaged(o,'.ctor',[m.root.method('get_Resources').invoke().handle,m.main.method('get_CurrentFile').invoke().handle,
                    m.main.method('get_GlobalBus').invoke().handle,hm.handle,m.engine.handle,
                    m.main.method('get_CurrentFile').invoke().method('get_Engine').invoke().handle,h.handle,m.main.method('get_ActionHandler').invoke().handle]);return o;
            });invokeManaged(h,'set_DesignEditor',[d.handle]);
        }
        invokeManaged(d,'UpdateLists');return d;
    }
    function nodeId(n){
        const p=n.method(n.tryMethod('get_HairStrandPath')?'get_HairStrandPath':'get_HairGroupPath').invoke();
        const names=['TransferableId','HairGroupId','HairStrandId'];
        return names.filter(k=>p.tryMethod('get_'+k)).map(k=>text(p.method('get_'+k).invoke())).join('/');
    }
    function hairNodes(d){
        const out=[];function walk(n,parent){const id=nodeId(n);out.push({n,id,parent});for(const c of seq(n.method('get_Children').invoke()))walk(c,id);}
        for(const g of seq(d.method('get_HairGroups').invoke()))walk(g,null);return out;
    }
    function hairParameters(m,args){
        const d=hairEditor(m,args.category),node=hairNodes(d).find(n=>n.id===args.scope);
        if(!node)throw Error('UNKNOWN_HAIR_NODE: list_hair_nodes first');
        const n=node.n,out=[],prefix='hair/'+node.id;
        out.push(param(n,'TranslatedDisplayName',prefix+'/name','string',{label:'Name'}));
        for(const p of ['IsVisible','IsEditable'])out.push(param(n,p,prefix+'/'+p,'bool',{label:p}));
        if(n.method('get_IsGroupColorShown').invoke())out.push(param(n,'GroupColor',prefix+'/color','color',{label:'Group color',min:0,max:1}));
        if(n.tryMethod('get_HairGroupPath')){
            const path=n.method('get_HairGroupPath').invoke();
            const getTransform=()=>{const q=cls('VRoidCore','VRoidCore.Editing.Query.GetGuideOriginTransformQuery').alloc();invokeManaged(q,'.ctor',[path.handle]);return invokeManaged(q,'Execute',[m.context.method('get_ActiveModel').invoke().handle]).unbox();};
            for(const [field,type,keys]of [['Position','vector3',['x','y','z']],['Rotation','quaternion',['x','y','z','w']],['Scale','vector3',['x','y','z']]]){
                const get=()=>{const t=getTransform().field(field).value;return keys.map(k=>t.field(k).value);};
                out.push({data:{id:prefix+'/guide/'+field,label:'Guide '+field,type,value:get(),editable:true,units:field==='Position'?'meters':undefined},read:get,write:v=>{
                    const t=getTransform(),component=t.field(field).value;keys.forEach((k,i)=>component.field(k).value=v[i]);
                    const command=cls('VRoidCore','VRoidCore.Editing.History.Command.SetGuideOriginTransformCommand').alloc();
                    invokeManaged(command,'.ctor',[path.handle,t.handle]);invokeManaged(m.context,'ExecuteSyncCommand',[command.handle]);
                }});
            }
        }
        const prop=cache(m,'hair-property/'+node.id,()=>d.method('get_Mode').invoke().method('CreateProperty').invoke(n));
        seq(prop.method('get_Groups').invoke()).forEach((g,gi)=>seq(g.method('get_ParameterItems').invoke()).forEach((p,pi)=>{
            const id=prefix+'/'+gi+'/'+pi,extra={category:text(g.method('get_TranslatedHeader').invoke())};
            if(p.tryMethod('get_MinValue')&&p.tryMethod('set_Value')){
                out.push(param(p,'Value',id,p.method('get_Value').returnType.name==='System.Int32'?'int':'float',
                    {...extra,min:p.method('get_MinValue').invoke(),max:p.method('get_MaxValue').invoke(),range_source:'native UI'}));
            }else if(p.tryMethod('get_Index')&&p.tryMethod('get_Items')){
                const options=seq(p.method('get_Items').invoke()).map((v,i)=>({value:i,label:label(v,String(i))}));
                out.push(param(p,'Index',id,'enum',{...extra,options,min:0,max:options.length-1}));
            }else if(p.tryMethod('get_Curve')){
                const options=seq(p.method('get_CurveTemplates').invoke()).map((v,i)=>({value:i,label:label(v,String(i))}));
                out.push(param(p,'SelectedCurveTemplateIndex',id+'/template','enum',{...extra,options,min:0,max:options.length-1}));
                out.push(param(p,'Curve',id+'/curve','curve',extra));
            }
            if(p.tryMethod('set_IsOverriding'))out.push(param(p,'IsOverriding',id+'/override','bool',{...extra,label:label(p,'')+' override'}));
        }));return out;
    }
    function accessoryTemplates(m){
        const e=accessoryEditor(m),out=[];
        for(const c of seq(e.method('get_ShapeParameterCategories').invoke())){
            invokeManaged(e,'set_SelectedShapeParameterCategory',[c.handle]);
            const category=text(c.method('get_TransferableGroupType').invoke());
            for(const t of seq(e.method('get_Templates').invoke())){
                const id=text(t.field('transferableGroupTemplate').value.field('id').value);
                out.push({c,t,data:{id,category,label:label(t,id)}});
            }
        }return out;
    }
    function boneEditor(m){
        const h=m.root.method('get_HairEditor').invoke();let b=h.method('get_BoneEditor').invoke();
        if(b.handle.isNull()){
            b=cache(m,'hair-bone-editor',()=>{
                const o=cls('VRoid.Studio','VRoid.Studio.HairEditor.BoneEditor.ViewModel').alloc();
                invokeManaged(o,'.ctor',[m.root.method('get_Resources').invoke().handle,m.main.method('get_CurrentFile').invoke().handle,
                    m.main.method('get_GlobalBus').invoke().handle,h.method('get_Model').invoke().handle,h.handle,
                    h.method('get_MultiCustomItemSavingModelNonBaseHair').invoke().handle]);return o;
            });invokeManaged(h,'set_BoneEditor',[b.handle]);
        }invokeManaged(b,'UpdateLists');return b;
    }
    function clothing(m){
        const out=entries(m,'clothing').map(morph),e=m.root.method('get_ClothingEditor').invoke();
        for(const o of seq(e.method('get_Instances').invoke())){
            const id=text(o.field('transferableGroupInfo').value.method('get_Id').invoke()),bones=seq(o.method('get_Bones').invoke());
            if(bones.length)out.push(param(o,'SelectedBoneIndex','clothing/'+id+'/bone','enum',{min:0,max:bones.length-1,options:bones.map((b,i)=>({value:i,label:label(b,String(i))}))}));
            if(o.method('get_PartOriginPositionGizmoEnabled').invoke())out.push(param(o,'PartOriginGlobalPosition','clothing/'+id+'/position','vector3',{units:'meters'}));
        }return out;
    }
    function boneNodes(b){return seq(b.method('get_GroupedBoneGroups').invoke()).map(n=>{const p=n.field('boneGroupPath').value;return {n,p,id:text(p.method('get_TransferableId').invoke())+'/'+text(p.method('get_BoneGroupId').invoke())};});}
    function hairBones(m,args){
        hairEditor(m,args.category||'HairFront');
        const b=boneEditor(m),out=[],gen=b.method('get_BoneGroupGeneration').invoke();
        out.push(param(gen,'Count','hair_bones/generation/count','int',{min:1,max:100,persistent:false,label:'Generated bone group count'}));
        out.push(param(gen,'Edge','hair_bones/generation/edge','float',{min:0,max:1,persistent:false,label:'Generation grouping threshold'}));
        for(const {n,p,id}of boneNodes(b)){
            if(args.scope&&args.scope!==id)continue;
            const prop=cache(m,'bone-property/'+id,()=>{
                const o=cls('VRoid.Studio','VRoid.Studio.HairEditor.BoneEditor.Property.ViewModel.BoneGroupPropertyViewModel').alloc();
                invokeManaged(o,'.ctor',[m.root.method('get_Resources').invoke().handle,m.engine.handle,m.main.method('get_CurrentFile').invoke().method('get_Engine').invoke().handle,b.handle,p.handle]);return o;
            });
            for(const name of ['BoneCount','SpringRootRate','Stiffness','Gravity','ColliderRadius'])out.push(param(prop,name,'hair_bones/'+id+'/'+name,name==='BoneCount'?'int':'float',
                {min:name==='BoneCount'?1:0,max:name==='BoneCount'?20:1,label:name,category:label(n,id),range_source:'MCP operating range'}));
            out.push(param(n,'TranslatedDisplayName','hair_bones/'+id+'/name','string',{label:'Name'}));
        }return out;
    }
    function photo(m){
        const p=m.root.field('obsoleteLegacyPhotoBoothViewModel').value;
        if(!p.method('get_IsActive').invoke())throw Error('PHOTO_MODE_REQUIRED: set_preview_mode(photo) first');return p;
    }
    function photoParameters(m){
        const p=photo(m),out=[];
        const typeMap={'System.Single':'float','System.Int32':'int','System.Boolean':'bool','UnityEngine.Vector2':'vector2','VRoid.UI.ScreenColor':'screen_color'};
        function add(o,name,id,extra={}){const type=typeMap[o.method('get_'+name).returnType.name];if(!type)throw Error('UNSUPPORTED_PHOTO_PARAMETER');out.push(param(o,name,id,type,{label:name,persistent:false,...extra}));}
        for(const name of ['ColorAlpha','ImageAlpha','CurrentColor','IsAutoBlink','IsLookAtCameraOn','LeftEyeGazeOffset','RightEyeGazeOffset','IsGazeOffsetSyncOn','LightIntencity','LightDegreeAltitude','LightDegreeAzimuth'])add(p,name,'photo/'+name);
        add(p,'LightColor','photo/LightColor');
        const wind=p.method('get_WindViewModel').invoke();for(const name of ['DirectionX','DirectionY','DirectionZ'])add(wind,name,'photo/wind/'+name,{min:-100,max:100});
        const post=p.method('get_PostEffectSettings').invoke();
        for(const group of ['bloomParam','colorGradingParam','comicBookParam','antiAliasingParam','motionBlurParam']){
            const o=post.method('get_'+group).invoke();
            for(const g of o.class.methods.filter(g=>g.name.startsWith('get_')&&typeMap[g.returnType.name]&&o.tryMethod('set_'+g.name.slice(4))))add(o,g.name.slice(4),'photo/effects/'+group+'/'+g.name.slice(4));
        }
        const poses=p.method('get_PosesViewModel').invoke(),options=seq(poses.method('get_PoseAnimationList').invoke()).map((o,i)=>({value:i,label:label(o,String(i))}));
        add(poses,'SelectedIndex','photo/pose',{min:0,max:options.length-1,options});out[out.length-1].data.type='enum';
        const modeType=cls('VRoidStudio','VRoidStudio.GUI.AvatarEditor.PhotoBooth.PoseMode');
        const modes=['FemaleAnimation','MaleAnimation','ManualPose'].map(name=>{const v=modeType.field(name).value;return {label:name,value:typeof v==='number'?v:v.field('value__').value};});
        const manual=modes.find(m=>m.label==='ManualPose').value;
        out[out.length-1].write=v=>{invokeManaged(p,'set_PoseModeIndex',[argument('int',manual)]);invokeManaged(poses,'set_SelectedIndex',[argument('int',v)]);};
        out.push(param(p,'PoseModeIndex','photo/mode','enum',{options:modes,min:Math.min(...modes.map(m=>m.value)),max:Math.max(...modes.map(m=>m.value)),persistent:false}));
        const animations=p.method('get_AnimationsViewModel').invoke();
        const items=[...seq(animations.method('get_FemaleAnimationList').invoke()),...seq(animations.method('get_MaleAnimationList').invoke())];
        const currentAnimation=()=>{const selected=animations.method('get_SelectedAnimation').invoke();return selected.handle.isNull()?-1:items.findIndex(i=>i.handle.equals(selected.handle));};
        out.push({data:{id:'photo/animation',label:'Animation',type:'enum',value:currentAnimation(),editable:true,persistent:false,min:0,max:items.length-1,options:items.map((a,i)=>({value:i,label:label(a,String(i))}))},read:currentAnimation,write:v=>{
            const female=animations.method('IsFemaleAnimation').invoke(items[v]),mode=modes.find(m=>m.label===(female?'FemaleAnimation':'MaleAnimation')).value;
            invokeManaged(p,'set_PoseModeIndex',[argument('int',mode)]);invokeManaged(animations,'set_SelectedAnimation',[items[v].handle]);
        }});
        out.push({data:{id:'photo/animation_playing',label:'Animation playing',type:'bool',value:animations.method('get_IsAnimationPlaying').invoke(),editable:true,persistent:false},
            read:()=>animations.method('get_IsAnimationPlaying').invoke(),write:v=>{if(animations.method('get_IsAnimationPlaying').invoke()!==v)invokeManaged(animations,'TogglePlayAnimation');}});
        const controller=poses.field('_posesModel').value.field('_poseController').value;
        if(!controller.handle.isNull())seq(controller.field('poseSerializers').value).forEach((serializer,i)=>{
            const definition=serializer.method('Serialize').invoke();
            for(const method of definition.class.methods.filter(g=>g.name.startsWith('get_')&&/Current/i.test(g.name)&&definition.tryMethod('set_'+g.name.slice(4)))){
                const name=method.name.slice(4),type={'UnityEngine.Quaternion':'quaternion','UnityEngine.Vector3':'vector3','System.Single':'float'}[method.returnType.name];if(!type)continue;
                const get=()=>read(serializer.method('Serialize').invoke(),name,type);
                out.push({data:{id:'photo/pose_controls/'+i+'/'+name,label:label(serializer,String(i))+' '+name,type,value:get(),editable:true,persistent:false},read:get,write:v=>{
                    const fresh=serializer.method('Serialize').invoke();invokeManaged(fresh,'set_'+name,[argument(type,v)]);invokeManaged(serializer,'Deserialize',[fresh.handle]);
                }});
            }
        });
        const hands=p.method('get_HandPosesViewModel').invoke();
        for(const side of ['Left','Right']){
            const options=seq(hands.method('get_'+side+'HandAnimationSource').invoke()).map((o,i)=>({value:i,label:label(o,String(i))}));
            add(hands,side+'HandAnimationIndex','photo/hands/'+side+'/pose',{min:0,max:options.length-1,options});out[out.length-1].data.type='enum';
            add(hands,side+'HandAnimationWeight','photo/hands/'+side+'/weight',{min:0,max:1});
        }
        const camera=p.method('get_PhotoBoothCamera').invoke();
        out.push(param(camera,'fieldOfView','photo/camera/field_of_view','float',{min:1,max:179,persistent:false,units:'degrees'}));
        out.push(param(camera,'orthographic','photo/camera/orthographic','bool',{persistent:false}));
        out.push(param(camera,'orthographicSize','photo/camera/orthographic_size','float',{min:.01,max:100,persistent:false}));
        for(const name of ['ColorAlpha','ImageAlpha']){const e=out.find(e=>e.data.id==='photo/'+name);e.data.min=0;e.data.max=1;}
        return out;
    }
    return {operations:{list_parameters:listParameters,set_parameters:setParameters,
        set_preview_mode(args){if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');const m=model(args.expected_model),p=m.root.field('obsoleteLegacyPhotoBoothViewModel').value;
            const active=p.method('get_IsActive').invoke();
            if(args.mode==='photo'){if(!active)invokeManaged(m.root,'EnterToPhotoBooth');}
            else if(args.mode==='edit'){if(active){const nav=m.main.method('get_GlobalBus').invoke().method('get_ScreenNavigation').invoke(),screen=nav.method('get_ActiveScreen').invoke();if(screen.class.type.name!=='VRoid.Studio.PhotoBoothScreen.ViewModel')throw Error('UNEXPECTED_SCREEN');invokeManaged(nav,'Pop',[screen.handle,argument('bool',false)]);}}
            else throw Error('INVALID_PREVIEW_MODE');return {model_token:m.token,mode:args.mode,frame:state.frame};},
        set_photo_camera(args){if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');const m=model(args.expected_model);photo(m);
            validate({data:{id:'camera_position',type:'vector3',editable:true}},args.position);validate({data:{id:'camera_target',type:'vector3',editable:true}},args.target);
            const camera=m.main.method('get_GlobalBus').invoke().method('get_PhotoBoothAvatarCameraPosition').invoke();
            invokeManaged(camera,'SetCustomView',[argument('vector3',args.position),argument('vector3',args.target)]);return {model_token:m.token,frame:state.frame};},
        list_hair_nodes(args){const m=model(args.expected_model),d=hairEditor(m,args.category);return {model_token:m.token,category:args.category,nodes:hairNodes(d).map(({n,id,parent})=>({id,parent,label:label(n,id),kind:n.class.name}))};},
        list_hair_bone_groups(args){const m=model(args.expected_model);hairEditor(m,args.category||'HairFront');return {model_token:m.token,groups:boneNodes(boneEditor(m)).map(({n,id})=>({id,label:label(n,id)}))};},
        generate_hair_bones(args){if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');const m=model(args.expected_model);hairEditor(m,args.category||'HairFront');invokeManaged(boneEditor(m),'GenHairBoneGroup');return {model_token:m.token,frame:state.frame};},
        edit_hair_structure(args){if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');const m=model(args.expected_model),d=hairEditor(m,args.category);
            if(args.action==='add_procedural')invokeManaged(d,'AddProceduralGuide');
            else if(args.action==='remove'){const n=hairNodes(d).find(n=>n.id===args.node_id);if(!n)throw Error('UNKNOWN_HAIR_NODE');invokeManaged(d,'set_SelectedItem',[n.n.handle]);invokeManaged(d,'DeleteSelectedItem');}
            else throw Error('UNKNOWN_HAIR_ACTION');return {model_token:m.token,frame:state.frame};},
        list_accessory_templates(args){const m=model(args.expected_model);return {model_token:m.token,templates:accessoryTemplates(m).map(e=>e.data)};},
        list_accessories(args){const m=model(args.expected_model);return {model_token:m.token,instances:accessoryInstances(m).map(o=>({id:accessoryId(o),label:label(o,''),visible:o.method('get_IsVisible').invoke()}))};},
        edit_accessories(args){if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');const m=model(args.expected_model),e=accessoryEditor(m);
            if(args.action==='add'){const t=accessoryTemplates(m).find(t=>t.data.id===args.template_id);if(!t)throw Error('UNKNOWN_TEMPLATE');invokeManaged(e,'set_SelectedShapeParameterCategory',[t.c.handle]);invokeManaged(e,'set_SelectedTemplate',[t.t.handle]);}
            else {const o=accessoryInstances(m).find(o=>accessoryId(o)===args.instance_id);if(!o)throw Error('UNKNOWN_ACCESSORY');invokeManaged(e,'set_SelectedInstance',[o.handle]);
                if(args.action==='remove')invokeManaged(e,'RemoveSelectedInstance');else if(args.action==='duplicate')invokeManaged(e,'DuplicateSelectedInstance');else throw Error('UNKNOWN_ACCESSORY_ACTION');}
            return {model_token:m.token,frame:state.frame};},
        list_expressions(args){const m=model(args.expected_model);return {model_token:m.token,expressions:expressionCategories(m).map(c=>({id:last(text(c.method('get_SynthesizedCompatKey').invoke())),label:label(c,'')}))};},
        preview_expression(args){if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');const m=model(args.expected_model);if(args.expression===null){invokeManaged(m.face,'ResetExpression');}else{const c=expressionCategories(m).find(c=>last(text(c.method('get_SynthesizedCompatKey').invoke()))===args.expression);if(!c)throw Error('UNKNOWN_EXPRESSION');invokeManaged(m.face,'set_SelectedExpressionParameterCategory',[c.handle]);invokeManaged(m.face,'UpdateExpression');}return {model_token:m.token,frame:state.frame};},
        get_height(args){const m=model(args.expected_model),o=m.root.method('get_BodyEditor').invoke().method('get_BodyHeight').invoke();return {model_token:m.token,centimeters:o.method('get_BodyHeightValue').invoke(),live_centimeters:o.method('GetBodyHeight').invoke()*100,label:text(o.method('get_BodyHeightLabel').invoke())};}
    }};
};
