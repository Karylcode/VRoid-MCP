// All functions in this module run synchronously on a registered Unity main thread.
globalThis.vroid = (() => {
    const session = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
    let generation = 0, engineAddress = '', tasks = new Map(), nextTask = 0;
    const allowed = new Set(['BlendShapeTransformParameterViewModel',
        'CombinedBlendShapeTransformParameterViewModel', 'BoneTransformParameterViewModel',
        'CombinedBoneTransformParameterViewModel']);
    const core = n => cls('UnityEngine.CoreModule', 'UnityEngine.' + n);
    const text = value => value && !value.handle.isNull() ? value.content : null;
    function main() {
        const p = state.refs['VRoid.Studio.MainViewModel'];
        if (!p) throw Error('NOT_READY: MainViewModel has not been constructed');
        return new Il2Cpp.Object(ptr(p));
    }
    function model(expected) {
        const m = main();
        const file = m.field('_mainModel').value.field('currentFile').value;
        if (file.handle.isNull()) throw Error(ATTACHED ? 'NO_MODEL: VRoid shows its start screen; open_start_model or open one there'
            : 'NO_MODEL: initialize a disposable model first');
        const engine = file.field('engine').value;
        if (engine.handle.isNull() || engine.method('get_Disposed').invoke()) throw Error('MODEL_DISPOSED');
        const p = state.refs['VRoid.Studio.EditRootScreen.ViewModel'];
        if (!p) throw Error('MODEL_LOADING: EditRootScreen is not ready');
        const root = new Il2Cpp.Object(ptr(p));
        if (!root.field('_engineModel').value.handle.equals(engine.handle)) throw Error('MODEL_LOADING');
        if (engineAddress !== engine.handle.toString()) {
            engineAddress = engine.handle.toString(); generation++;
        }
        const token = session + ':' + generation;
        // Reads pass no token at all; an empty token is refused, never treated as "any model".
        if (expected != null && expected !== token) throw Error(expected ? 'STALE_MODEL: list parameters again' : 'EXPECTED_MODEL_REQUIRED');
        return {main:m, file, engine, root, token, face:root.method('get_FaceEditor').invoke(),
            context:engine.method('get_Context').invoke()};
    }
    function array(immutable) {
        const a = immutable.field('array').value;
        return a.handle.isNull() ? [] : [...a];
    }
    function value(p) {
        return p.method(p.tryMethod('get_CombinedValue') ? 'get_CombinedValue' : 'get_ModelValue').invoke();
    }
    function canonical(p) {
        return [p.class.name, text(p.field('_transferableGroupType').value), ...p.class.fields
            .filter(f=>!f.isStatic && /path|boneElementKey/i.test(f.name))
            .map(f=>{const v=p.field(f.name).value;return v.handle.isNull() ? '' :
                v instanceof Il2Cpp.String ? v.content : v.method('ToString').invoke().content;})].join('|');
    }
    function selector(m,area) {
        const names={face:'Face',body:'Body',hair:'Hair',clothing:'Clothing'};
        if(!Object.hasOwn(names,area))throw Error('UNKNOWN_AREA');
        return m.root.method('get_'+names[area]+'Editor').invoke().method('get_PresetsSelector').invoke();
    }
    function categories(m,area) {
        const out=[],seen=new Set();
        function walk(c){
            if(seen.has(c.handle.toString()))return;seen.add(c.handle.toString());out.push(c);
            for(const child of array(c.method('get_Children').invoke()))walk(child);
        }
        walk(selector(m,area).method('get_Categories').invoke());return out;
    }
    function entries(m,area='face') {
        if(area==='clothing'){
            const editor=m.root.method('get_ClothingEditor').invoke(),out=[];
            for(const instance of editor.method('get_Instances').invoke()){
                const info=instance.field('transferableGroupInfo').value;
                const group=text(info.method('get_Id').invoke()),type=text(info.method('get_Type').invoke());
                [...instance.method('get_BlendShapeParameters').invoke()].forEach((p,i)=>{
                    if(!allowed.has(p.class.name))throw Error('UNSUPPORTED_CLOTHING_PARAMETER: '+p.class.name);
                    if(!p.field('_context').value.handle.equals(m.context.handle))throw Error('CONTEXT_MISMATCH');
                    out.push({p,canonical:canonical(p),id:'clothing/'+group+'/'+String(i).padStart(3,'0'),
                        category:type.split('.').pop(),category_key:type});
                });
            }
            return out;
        }
        if(!['face','body'].includes(area))throw Error('NO_PARAMETER_API_FOR_AREA');
        const out = [], seenCategories = new Set();
        const root = selector(m,area).method('get_Categories').invoke();
        function walk(category) {
            const address = category.handle.toString();
            if (seenCategories.has(address)) return; seenCategories.add(address);
            const getter = category.tryMethod('get_ParameterCategoryViewModel');
            const pc = getter ? getter.invoke() : category.tryMethod('get_Parameters')?category:null;
            if (pc && !pc.handle.isNull()) {
                const key = text(category.method('get_TranslationKey').invoke());
                const name = text(category.method('get_Name').invoke());
                array(pc.method('get_Parameters').invoke()).forEach((p,i)=>{
                    if (!allowed.has(p.class.name)) throw Error('UNSUPPORTED_FACE_PARAMETER: '+p.class.name);
                    if (!p.field('_context').value.handle.equals(m.context.handle)) throw Error('CONTEXT_MISMATCH');
                    out.push({p, canonical:canonical(p), id:area+'/'+key.split('.').pop()+'/'+String(i).padStart(3,'0'),
                        category:name, category_key:key});
                });
            }
            for (const child of array(category.method('get_Children').invoke())) walk(child);
        }
        walk(root);
        if (!out.length) throw Error('NO_PARAMETERS: '+area);
        return out;
    }
    function details(e) {
        const p=e.p;
        return {id:e.id,label:text(p.method('get_Label').invoke()),category:e.category,
            category_key:e.category_key,type:p.class.name,value:value(p),
            min:p.method('get_MinValue').invoke(),max:p.method('get_MaxValue').invoke(),
            editable:p.method('get_IsEditable').invoke()};
    }
    function list(args={},area='face') {
        const m=model(args.expected_model), aliases=new Map();
        const params=entries(m,area).map(e=>{
            const d=details(e);d.alias_of=aliases.get(e.canonical)||null;
            if(!d.alias_of)aliases.set(e.canonical,e.id);return d;
        });
        return {model_token:m.token,schema:'vroid-2.14.0-'+area+'-v1',area,count:params.length,
            unique_parameters:aliases.size,parameters:params};
    }
    function status() {
        const base={pid:Process.id,unity:Il2Cpp.unityVersion,main_thread:state.mainThread,
            callback_thread:Process.getCurrentThreadId(),frame:state.frame||0,
            background:core('Application').method('get_runInBackground').invoke(),
            focused:core('Application').method('get_isFocused').invoke(),model_ready:false};
        try {const m=model();const photo=m.root.field('obsoleteLegacyPhotoBoothViewModel').value;
            const photoActive=photo.method('get_IsActive').invoke();
            let photoUpdating=false;
            if(photoActive){const vm=photo.method('get_V1PhotoBooth').invoke();
                if(vm.handle.isNull())photoUpdating=true;
                else {const preview=vm.method('get_PreviewModelTransform').invoke();
                    photoUpdating=preview.tryMethod('get_IsUpdatingModel')?preview.method('get_IsUpdatingModel').invoke():false;}}
            return {...base,model_ready:true,model_token:m.token,photo_active:photoActive,photo_updating:photoUpdating,
            presets_loading:['face','body','hair','clothing'].some(area=>selector(m,area).method('get_IsLoading').invoke()),
            command_busy:!m.context.method('get_IsCommandExecutable').invoke(),
            updating:m.main.field('_editModelTransform').value.method('get_IsUpdatingModel').invoke()};}
        catch(e) {return {...base,reason:String(e)};}
    }
    function set(args,area='face') {
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');
        const m=model(args.expected_model), map=new Map(entries(m,area).map(e=>[e.id,e]));
        if(!Array.isArray(args.changes)||!args.changes.length||args.changes.length>64)throw Error('BATCH_SIZE: 1..64');
        const seen=new Set();
        const changes=args.changes.map(change=>{
            const e=map.get(change.id);if(!e)throw Error('UNKNOWN_PARAMETER: '+change.id);
            if(seen.has(e.canonical))throw Error('DUPLICATE_PARAMETER_OR_ALIAS: '+change.id);seen.add(e.canonical);
            const d=details(e),v=change.value;
            if(typeof v!=='number'||!Number.isFinite(v))throw Error('INVALID_NUMBER: '+change.id);
            if(v<d.min||v>d.max){
                // Files from older VRoid versions can hold values the sliders cannot reach (e.g. -0.1 on a 0..1 slider).
                const span=d.max-d.min;
                if(!args.allow_out_of_ui_range||v<d.min-span||v>d.max+span)throw Error('OUT_OF_RANGE: '+change.id+' ['+d.min+','+d.max+']');
            }
            if(!d.editable)throw Error('PARAMETER_NOT_EDITABLE: '+change.id);
            return {e,before:d.value,value:v};
        });
        const applied=[];
        for(const c of changes){
            try {
                if(Math.abs(c.before-c.value)>1e-7){
                    const v=Memory.alloc(4);v.writeFloat(c.value);
                    invokeManaged(c.e.p,c.e.p.tryMethod('set_CombinedValue')?'set_CombinedValue':'set_ModelValue',[v]);
                }
                applied.push({id:c.e.id,before:c.before,after:value(c.e.p)});
            }catch(e){return {model_token:m.token,ok:false,partial:true,applied,error:String(e),frame:state.frame||0};}
        }
        return {model_token:m.token,ok:true,applied,frame:state.frame||0,history_policy:'native VRoid history; a batch may require multiple undo steps'};
    }
    function enumerate(collection){
        const out=[],e=collection.method('GetEnumerator').invoke();
        try{while(e.method('MoveNext').invoke())out.push(e.method('get_Current').invoke());}
        finally{if(e.tryMethod('Dispose'))e.method('Dispose').invoke();}
        return out;
    }
    function presetEntries(m,area){
        if(!['face','body','hair','clothing'].includes(area))throw Error('UNSUPPORTED_PRESET_AREA');
        const result=[],clears=[];
        for(const category of categories(m,area)){
            const pc=category.tryMethod('get_PresetCategoryViewModel')?category.method('get_PresetCategoryViewModel').invoke():
                category.tryMethod('get_PresetOptions')?category:null;
            if(!pc||pc.handle.isNull())continue;
            const key=text(category.method('get_TranslationKey').invoke()).split('.').pop();
            const name=text(category.method('get_Name').invoke());
            const options=[...enumerate(pc.method('get_PresetOptions').invoke())];
            if(pc.tryMethod('get_CustomItemOptions')){
                // Closet items live in a separate collection that VRoid builds when the category is first shown.
                let custom=pc.method('get_CustomItemOptions').invoke();
                if(custom.handle.isNull()){invokeManaged(selector(m,area),'set_SelectedCategory',[category.handle]);custom=pc.method('get_CustomItemOptions').invoke();}
                if(!custom.handle.isNull())options.push(...enumerate(custom));
            }
            for(const p of options){
                if(p.class.name==='ClearOptionViewModel'){
                    clears.push({p,id:area+'/'+key+'/none',category:key,category_name:name,label:name+' / None',
                        resource_name:null,clear:true,owned:true,selected:null});continue;
                }
                if(p.class.name==='CustomItemOptionViewModel'){
                    // Items in this VRoid's closet (custom_items); selected the same way as built-in presets.
                    const fm=p.field('_model').value,id=text(fm.method('get_TransferableGroupId').invoke());
                    result.push({p,id:area+'/'+key+'/'+id,category:key,category_name:name,label:name+' / custom item',
                        resource_name:text(fm.method('get_TransferableGroupResourceName').invoke()),custom:true,
                        file:text(fm.method('get_FilePath').invoke()),owned:true,selected:p.method('get_IsSelected').invoke()});
                    continue;
                }
                if(p.class.name!=='PresetOptionViewModel')continue;
                const pm=p.field('_model').value,id=text(p.method('get_TransferableGroupId').invoke());
                const resource=text(pm.field('resourceName').value);
                result.push({p,id:area+'/'+key+'/'+id,category:key,category_name:name,
                    label:name+' / '+resource.split('/').slice(0,-1).pop(),resource_name:resource,
                    owned:p.method('get_IsOwned').invoke(),selected:p.method('get_IsSelected').invoke()});
            }
        }
        return result.concat(clears);
    }
    function listPresets(args,area){
        const m=model(args.expected_model),all=presetEntries(m,area),counts=new Map();
        for(const p of all){const c=counts.get(p.category)||{id:p.category,name:p.category_name,count:0};c.count++;counts.set(p.category,c);}
        if(args.category&&!counts.has(args.category))throw Error('UNKNOWN_PRESET_CATEGORY');
        const matching=all.filter(p=>(!args.category||p.category===args.category)&&(!args.owned_only||p.owned));
        const offset=args.offset??0,limit=args.limit??100;
        if(!Number.isInteger(offset)||offset<0||!Number.isInteger(limit)||limit<1||limit>200)throw Error('INVALID_PAGINATION');
        return {model_token:m.token,area,categories:[...counts.values()],total:matching.length,offset,
            next_offset:offset+limit<matching.length?offset+limit:null,
            presets:matching.slice(offset,offset+limit).map(({p,...data})=>data)};
    }
    function activeGroupSnapshot(m){
        const active=m.context.method('get_ActiveModel').invoke().method('GetActiveTransferableGroups').invoke();
        const it=active.method('get_Values').invoke().method('GetEnumerator').invoke(),groups=[];
        try{while(it.method('MoveNext').invoke()){const v=it.method('get_Current').invoke();
            groups.push({id:text(v.method('get_Id').invoke()),revision:text(v.method('get_Revision').invoke()),type:text(v.method('get_Type').invoke())});}}
        finally{it.method('Dispose').invoke();}
        return groups.sort((a,b)=>a.id.localeCompare(b.id));
    }
    function applyPreset(args,area){
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');
        const m=model(args.expected_model),entry=presetEntries(m,area).find(p=>p.id===args.preset_id);
        if(!entry)throw Error('UNKNOWN_PRESET');
        if(!entry.owned)throw Error('PRESET_NOT_OWNED');
        if(entry.selected)return {model_token:m.token,preset_id:entry.id,changed:false,frame:state.frame};
        const before_groups=activeGroupSnapshot(m),enabled=Memory.alloc(1);enabled.writeU8(1);
        if(entry.clear)invokeManaged(entry.p,'ClearTransferableGroup');
        else invokeManaged(entry.p,'set_IsSelected',[enabled]);
        return {model_token:m.token,preset_id:entry.id,category:entry.category,clear:!!entry.clear,changed:true,before_groups,frame:state.frame};
    }
    function rememberTask(task) {
        const id=String(++nextTask);tasks.set(id,{task,handle:retain(task)});return {task_id:id};
    }
    function taskStatus({task_id}) {
        const holder=tasks.get(task_id);if(!holder)throw Error('UNKNOWN_TASK');
        const task=holder.task,done=task.method('get_IsCompleted').invoke();
        if(!done)return {completed:false};
        const faulted=task.method('get_IsFaulted').invoke(),canceled=task.method('get_IsCanceled').invoke();
        const result={completed:true,faulted,canceled};
        if(faulted)result.error=text(task.method('get_Exception').invoke().method('ToString').invoke());
        holder.handle.free();tasks.delete(task_id);return result;
    }
    function invokeManaged(object, method, parameters=[]) {
        // Let IL2CPP catch normal Windows C++ exceptions; Frida's default "steal"
        // interrupts even exceptions that VRoid handles internally.
        const invoke=new NativeFunction(Il2Cpp.module.getExportByName('il2cpp_runtime_invoke'),
            'pointer',['pointer','pointer','pointer','pointer'],{exceptions:'propagate'});
        const exception=Memory.alloc(Process.pointerSize);exception.writePointer(NULL);
        const argv=parameters.length?Memory.alloc(parameters.length*Process.pointerSize):NULL;
        parameters.forEach((p,i)=>argv.add(i*Process.pointerSize).writePointer(p));
        const result=invoke(object.method(method,parameters.length).handle,object.handle,argv,exception);
        if(!exception.readPointer().isNull()){
            const error=new Il2Cpp.Object(exception.readPointer());
            throw Error('MANAGED_OPERATION_ERROR: '+method+': '+error.method('ToString').invoke().content);
        }
        return new Il2Cpp.Object(result);
    }
    function history(args, method) {
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');
        return {...rememberTask(invokeManaged(model(args.expected_model).engine,method)),frame:state.frame||0};
    }
    function newModel(args) {
        const variant=args.variant||'F00';if(!['F00','M00'].includes(variant))throw Error('UNSUPPORTED_VARIANT');
        const current=main().field('_mainModel').value.field('currentFile').value;
        if(!current.handle.isNull())throw Error('MODEL_ALREADY_OPEN');
        main().method('InitializeCurrentFileAndMoveToEditRoot',2).invoke(Il2Cpp.string(variant==='F00'?'Preset_F':'Preset_M'),Il2Cpp.string(variant));
        return {requested:true,variant};
    }
    function save(args) {
        const m=model(args.expected_model);
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');
        const handler=m.main.method('get_ActionHandler').invoke(),path=Il2Cpp.string(args.path),access=Memory.alloc(1);
        access.writeU8(0);
        const success=invokeManaged(handler,'SaveSync',[path.handle,access]).unbox().field('m_value').value;
        if(!success)throw Error('SAVE_FAILED');
        // The published name is assigned by the host after its no-overwrite rename.
        // Keep this editing session untitled, so UI autosave cannot target an old file.
        m.file.field('path').value=Il2Cpp.string('');
        handler.method('UpdateWindowTitle').invoke();
        return {saved:true,model_token:m.token};
    }
    function open(args) {
        const path=Il2Cpp.string(args.path),dontSetPath=Memory.alloc(1),fromXRoid=Memory.alloc(1);
        dontSetPath.writeU8(1);fromXRoid.writeU8(0);
        return rememberTask(invokeManaged(main(),'ImportFileAndMoveToEditRoot',[path.handle,dontSetPath,fromXRoid]));
    }
    function startScreen() {
        const c=cls('VRoid.Studio','VRoid.Studio.StartScreen.ViewModel');
        const live=Il2Cpp.gc.choose(c).filter(o=>o.class.handle.equals(c.handle)&&!o.field('_disposed').value);
        if(live.length!==1)throw Error('START_SCREEN_NOT_FOUND: '+live.length);
        return live[0];
    }
    function startItems() {
        const screen=startScreen(),out=[];
        for(const [group,getter] of [['recent','get_ModelItemDataSources'],['sample','get_SampleModelItemDataSources'],['old','get_OldModelItemDataSources']]){
            const items=screen.method(getter).invoke();
            for(let i=0,n=items.method('get_Count').invoke();i<n;i++){
                const item=items.method('get_Item').invoke(i);
                if(item.handle.isNull()||item.class.type.name!=='VRoid.Studio.StartScreen.View.ModelSelectItemViewModel')continue;
                out.push({item,group,name:text(item.method('get_Name').invoke()),
                    path:text(item.method('get_Path').invoke())||null,downloaded:item.field('isDownloaded').value});
            }
        }
        return out;
    }
    function openStartModel(args) {
        // Same as clicking the card on the start screen; never replaces a model that is already open.
        if(!main().field('_mainModel').value.field('currentFile').value.handle.isNull())
            throw Error('MODEL_ALREADY_OPEN: save or close it in VRoid first');
        const matches=startItems().filter(e=>e.name===args.name&&(!args.group||e.group===args.group));
        if(matches.length!==1)throw Error((matches.length?'AMBIGUOUS_START_MODEL: pass group':'UNKNOWN_START_MODEL')+': '+args.name);
        invokeManaged(matches[0].item,'OnClickItemDelegate');
        return {requested:true,name:args.name,group:matches[0].group};
    }
    function listParts(args) {
        // Every active transferable group: what the model is built from, by native id and resource.
        const m=model(args.expected_model),parts=[];
        const it=m.context.method('get_ActiveModel').invoke().method('GetActiveTransferableGroups').invoke()
            .method('get_Values').invoke().method('GetEnumerator').invoke();
        try{while(it.method('MoveNext').invoke()){
            const g=it.method('get_Current').invoke(),type=text(g.method('get_Type').invoke()),res=text(g.method('get_ResourceName').invoke());
            parts.push({id:text(g.method('get_Id').invoke()),type:type.split('.').pop(),group_type:type,resource_name:res,
                original_resource_name:text(g.method('get_OriginalResourceName').invoke()),custom:!!res&&res.startsWith('user/'),
                updated:g.method('get_UpdatedSinceLastRevision').invoke()});
        }}finally{it.method('Dispose').invoke();}
        return {model_token:m.token,parts:parts.sort((a,b)=>a.type.localeCompare(b.type)||a.id.localeCompare(b.id))};
    }
    let partCallbacks=null;
    function managedCallbacks() {
        // Frida-made delegates crash when VRoid invokes them from its async loader, so build real managed
        // delegates over harmless corlib/Unity methods: success is a no-op, errors go to Player.log.
        if(partCallbacks)return partCallbacks;
        const typeOf=c=>c.type.object,typeClass=Il2Cpp.corlib.class('System.Type');
        const create=(delegateClass,methodInfo)=>Il2Cpp.corlib.class('System.Delegate').method('CreateDelegate')
            .overload('System.Type','System.Reflection.MethodInfo').invoke(typeOf(delegateClass),methodInfo);
        const thread=typeOf(Il2Cpp.corlib.class('System.Threading.Thread'));
        const noop=thread.method('GetMethod').overload('System.String','System.Type[]')
            .invoke(Il2Cpp.string('MemoryBarrier'),Il2Cpp.array(typeClass,0));
        const exception=Il2Cpp.corlib.class('System.Exception');
        const logException=typeOf(core('Debug')).method('GetMethod').overload('System.String','System.Type[]')
            .invoke(Il2Cpp.string('LogException'),Il2Cpp.array(typeClass,[typeOf(exception)]));
        const ok=create(Il2Cpp.corlib.class('System.Action'),noop);
        const fail=create(Il2Cpp.corlib.class('System.Action`1').inflate(exception),logException);
        partCallbacks={ok,fail,handles:[retain(ok),retain(fail)]};
        return partCallbacks;
    }
    function replacePart(args) {
        // Native Context.LoadAndReplaceTransferableGroup: swaps exactly one built-in part by id.
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');
        if(typeof args.part_id!=='string'||!args.part_id.endsWith('.transferablegroup'))throw Error('PART_ID_REQUIRED: a *.transferablegroup id');
        const m=model(args.expected_model);
        // An id missing from the asset catalog (e.g. from a file made with an older VRoid, or a custom
        // item id) makes the native loader throw outside any handler and VRoid crashes: refuse it here.
        const registry=Il2Cpp.gc.choose(cls('VRoid.Studio','VRoid.Studio.ModelPresetsSelector.CustomItemRegistry'))[0];
        if(!registry)throw Error('ASSET_CATALOG_NOT_FOUND');
        if(!registry.field('_assetCatalog').value.method('ContainsId').invoke(Il2Cpp.string(args.part_id)))
            throw Error('UNKNOWN_PART_ID: not in this VRoid\'s asset catalog; for closet custom items use list_presets and apply_preset');
        const {ok,fail}=managedCallbacks();
        const preserveMaterial=Memory.alloc(1);preserveMaterial.writeU8(0);
        invokeManaged(m.context,'LoadAndReplaceTransferableGroup',[Il2Cpp.string(args.part_id).handle,ok.handle,fail.handle,preserveMaterial]);
        return {requested:true,part_id:args.part_id,frame:state.frame};
    }
    // VRM export through VRoid's own photo-booth exporter, given a path instead of the save dialog.
    let vrmJob=null;
    const findClass=name=>{for(const a of Il2Cpp.domain.assemblies){const c=a.image.tryClass(name);if(c)return c;}throw Error('CLASS_NOT_FOUND: '+name);};
    const flag=v=>{const b=Memory.alloc(1);b.writeU8(v?1:0);return b;};
    const booth=m=>m.root.field('obsoleteLegacyPhotoBoothViewModel').value;
    const screenNav=m=>m.main.method('get_GlobalBus').invoke().method('get_ScreenNavigation').invoke();
    const EXPORT_SCREEN='VRoid.Studio.VRMExportScreen.ViewModel';
    function vrmExportState(args) {
        const m=model(args.expected_model),b=booth(m),screen=screenNav(m).method('get_ActiveScreen').invoke().class.type.name;
        const settings=b.method('get_IsActive').invoke()?b.method('get_ExportSettings').invoke():null;
        return {model_token:m.token,export_screen:screen===EXPORT_SCREEN,busy:!!vrmJob,frame:state.frame,
            ready:!!settings&&!settings.handle.isNull()&&!b.field('_isBlockingUpdateExportPreview').value};
    }
    function enterVrmExport(args) {
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');
        const m=model(args.expected_model);invokeManaged(m.root,'EnterToVRMExport');
        return {model_token:m.token,frame:state.frame};
    }
    function leaveVrmExport(args) {
        const m=model(args.expected_model),nav=screenNav(m),screen=nav.method('get_ActiveScreen').invoke();
        if(screen.class.type.name===EXPORT_SCREEN)invokeManaged(nav,'Pop',[screen.handle,flag(false)]);
        return {model_token:m.token,frame:state.frame};
    }
    function stringList(value) {
        const list=Il2Cpp.corlib.class('System.Collections.Generic.List`1').inflate(Il2Cpp.corlib.class('System.String')).new();
        for(const s of String(value||'').split(/\s*,\s*/).filter(Boolean))list.method('Add').invoke(Il2Cpp.string(s));
        return list;
    }
    function vrmMeta(m,version,dialogMeta) {
        // The settings' meta objects stay empty until the dialog fills them; build from the model's stored export meta.
        const app=m.context.method('get_ActiveModel').invoke().method('get_AppState').invoke();
        const src=app.method(version===0?'get_Vrm0Export':'get_Vrm1Export').invoke(),get=n=>src.field('<'+n+'>k__BackingField').value;
        const str=n=>Il2Cpp.string(text(get(n))||'');
        if(version===0){
            const meta=findClass('VRM.glTF_VRM_Meta').new();
            for(const [k,n] of [['title','Title'],['version','Version'],['author','Author'],['contactInformation','ContactInformation'],
                ['reference','Reference'],['otherPermissionUrl','OtherPermissionUrl'],['otherLicenseUrl','OtherLicenseUrl']])meta.field(k).value=str(n);
            for(const [k,n] of [['allowedUserName','AllowedUserName'],['violentUssageName','ViolentUssageName'],['sexualUssageName','SexualUssageName'],
                ['commercialUssageName','CommercialUssageName'],['licenseName','LicenseName']])meta.field(k).value=Il2Cpp.string(get(n).toString());
            meta.field('texture').value=dialogMeta.handle.isNull()?-1:dialogMeta.field('texture').value;
            if(!text(meta.field('title').value))throw Error('VRM_META_TITLE_REQUIRED: set the model\'s VRM title in VRoid first');
            return meta;
        }
        const meta=findClass('UniVRM10.VRM10ObjectMeta').new();
        for(const n of ['Name','Version','CopyrightInformation','ContactInformation','ThirdPartyLicenses','OtherLicenseUrl'])meta.field(n).value=str(n);
        meta.field('Authors').value=stringList(text(get('Authors')));meta.field('References').value=stringList(text(get('References')));
        for(const n of ['AvatarPermission','ViolentUsage','SexualUsage','CommercialUsage','PoliticalOrReligiousUsage','AntisocialOrHateUsage',
            'CreditNotation','Redistribution','Modification'])meta.field(n).value=get(n);
        if(!dialogMeta.handle.isNull()&&!dialogMeta.field('Thumbnail').value.handle.isNull())meta.field('Thumbnail').value=dialogMeta.field('Thumbnail').value;
        if(!text(meta.field('Name').value))throw Error('VRM_META_NAME_REQUIRED: set the model\'s VRM name in VRoid first');
        return meta;
    }
    function managedSignal() {
        // Action bound to ManualResetEventSlim.Set: a real managed delegate whose firing can be polled.
        const c=Il2Cpp.corlib.class('System.Threading.ManualResetEventSlim'),event=c.new();
        const set=c.type.object.method('GetMethod').overload('System.String','System.Type[]').invoke(Il2Cpp.string('Set'),Il2Cpp.array(Il2Cpp.corlib.class('System.Type'),0));
        const action=Il2Cpp.corlib.class('System.Delegate').method('CreateDelegate').overload('System.Type','System.Object','System.Reflection.MethodInfo')
            .invoke(Il2Cpp.corlib.class('System.Action').type.object,event,set);
        return {event,action,handles:[retain(event),retain(action)]};
    }
    function progressLog() {
        const dbl=Il2Cpp.corlib.class('System.Double'),listClass=Il2Cpp.corlib.class('System.Collections.Generic.List`1').inflate(dbl),list=listClass.new();
        const add=listClass.type.object.method('GetMethod').overload('System.String').invoke(Il2Cpp.string('Add'));
        const action=Il2Cpp.corlib.class('System.Delegate').method('CreateDelegate').overload('System.Type','System.Object','System.Reflection.MethodInfo')
            .invoke(Il2Cpp.corlib.class('System.Action`1').inflate(dbl).type.object,list,add);
        return {list,action,handles:[retain(list),retain(action)]};
    }
    function startVrmExport(args) {
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');
        if(vrmJob)throw Error('VRM_EXPORT_BUSY');
        if(![0,1].includes(args.version)||typeof args.path!=='string'||!/\.vrm$/i.test(args.path))throw Error('VRM_EXPORT_ARGS: version 0|1 and a .vrm path');
        const m=model(args.expected_model),b=booth(m),settings=b.method('get_ExportSettings').invoke();
        if(settings.handle.isNull())throw Error('VRM_EXPORT_NOT_READY: enter the export screen first');
        const meta=vrmMeta(m,args.version,settings.method(args.version===0?'get_VRM0MetaData':'get_VRM10MetaData').invoke());
        const ok=managedSignal(),fail=managedSignal(),progress=progressLog();
        const hair=args.hair_combination??settings.field('isEnableHairCombination').value;
        const reduction=findClass('VRoidStudio.PhotoBooth.MaterialReductionMode').field('None').value;
        const routine=b.method(args.version===0?'ExportVRM0':'ExportVRM1').invoke(Il2Cpp.string(args.path),meta,!!hair,false,reduction,false,ok.action,fail.action,progress.action);
        // The view model's coroutines need a MonoBehaviour host; a temporary GameObject keeps VRoid's UI untouched.
        const go=core('GameObject').alloc();go.method('.ctor',1).invoke(Il2Cpp.string('VRoid MCP VRM export'));
        go.method('AddComponent',1).invoke(findClass('UnityEngine.UI.LayoutElement').type.object).method('StartCoroutine').overload('System.Collections.IEnumerator').invoke(routine);
        vrmJob={ok,fail,progress,go,handles:[retain(go),retain(meta),retain(routine)]};
        return {started:true,version:args.version,path:args.path,hair_combination:!!hair};
    }
    function vrmExportStatus() {
        if(!vrmJob)return {running:false};
        const done=vrmJob.ok.event.method('get_IsSet').invoke(),failed=vrmJob.fail.event.method('get_IsSet').invoke();
        const n=vrmJob.progress.list.method('get_Count').invoke(),progress=n?vrmJob.progress.list.method('get_Item').invoke(n-1):0;
        if(!done&&!failed)return {running:true,progress};
        core('Object').method('Destroy',1).invoke(vrmJob.go);
        [...vrmJob.ok.handles,...vrmJob.fail.handles,...vrmJob.progress.handles,...vrmJob.handles].forEach(h=>h.free());vrmJob=null;
        return {running:false,done,failed,progress};
    }
    function saveCustomItems(args) {
        // VRoid's own "save as custom item" for every worn part it marks savable; files go to the profile's custom_items.
        if(!args.expected_model)throw Error('EXPECTED_MODEL_REQUIRED');
        const m=model(args.expected_model);
        const c=cls('VRoid.Studio','VRoid.Studio.ModelPresetsSelector.TemporaryCustomItemViewModel'),seen=new Set(),saved=[];
        for(const vm of Il2Cpp.gc.choose(c).filter(o=>o.class.handle.equals(c.handle))){
            const e=vm.field('_engine').value,category=vm.field('_customItemCategoryModel').value;
            if(e.handle.isNull()||!e.handle.equals(m.engine.handle)||category.handle.isNull())continue;
            const type=text(category.field('<TransferableGroupType>k__BackingField').value);
            if(!type||seen.has(type)||!vm.field('_wearingCustomItemSavableTransferableGroup').value)continue;
            if(args.types&&!args.types.includes(type.split('.').pop()))continue;
            seen.add(type);invokeManaged(vm,'SaveAsCustomItem',[(()=>{const b=Memory.alloc(1);b.writeU8(0);return b;})()]);
            saved.push(type.split('.').pop());
        }
        return {model_token:m.token,saved:saved.sort(),frame:state.frame};
    }
    function vector(x,y,z) {
        const o=core('Vector3').alloc(),v=o.unbox();v.method('.ctor',3).invoke(x,y,z);return v;
    }
    function screenshot(args) {
        const m=model(args.expected_model),view=args.view||'front';
        const size=args.size===undefined?512:args.size;
        if(!Number.isInteger(size)||size<256||size>2048)throw Error('CAPTURE_SIZE_RANGE: 256..2048');
        if(view==='photo')return photoScreenshot(m,size);
        if(!['front','side','back','three_quarter','full_front','full_side','full_back','full_three_quarter'].includes(view))throw Error('UNSUPPORTED_VIEW');
        const rtClass=core('RenderTexture'),unityObject=core('Object');
        const previous=rtClass.method('get_active').invoke();let go=null,rt=null,texture=null;
        try {
            const body=m.main.method('get_GlobalBus').invoke().method('get_Common3D').invoke()
                .method('get_AvatarCamera').invoke().field('_body').value;
            const source=body.field('_templateCamera').value.method('get_PrimaryCamera').invoke();
            go=core('GameObject').alloc();go.method('.ctor',1).invoke(Il2Cpp.string('VRoid MCP temporary capture'));
            const cam=go.method('AddComponent',1).invoke(core('Camera').type.object);
            cam.method('CopyFrom').invoke(source);cam.method('set_enabled').invoke(false);
            rt=rtClass.alloc();rt.method('.ctor',3).invoke(size,size,24);rt.method('Create').invoke();
            cam.method('set_targetTexture').invoke(rt);cam.method('set_orthographic').invoke(false);
            cam.method('set_fieldOfView').invoke(30);
            const face=m.face.method('GetFaceSMR').invoke(),bounds=face.method('get_bounds').invoke();
            const center=bounds.method('get_center').invoke(),extents=bounds.method('get_extents').invoke();
            let x=center.field('x').value,y=center.field('y').value,z=center.field('z').value;
            let radius=Math.max(extents.field('y').value,extents.field('x').value)*1.8;
            if(view.startsWith('full_')){
                // Character stands on y=0. Frame the feet through the top of the head,
                // with room for the T-pose arms and hair; adapts to height sliders.
                const top=y+extents.field('y').value;
                y=top/2;radius=top*.68;
            }
            const distance=radius/Math.tan(Math.PI/12);
            const transform=cam.method('get_transform').invoke();
            const diagonal=distance/Math.sqrt(2);
            transform.method('set_position').invoke(view.endsWith('three_quarter')?vector(x+diagonal,y,z+diagonal):view.endsWith('front')?vector(x,y,z+distance):view.endsWith('back')?vector(x,y,z-distance):vector(x+distance,y,z));
            transform.method('LookAt').overload('UnityEngine.Vector3','UnityEngine.Vector3').invoke(vector(x,y,z),vector(0,1,0));
            cam.method('Render').invoke();rtClass.method('set_active').invoke(rt);
            texture=core('Texture2D').alloc();texture.method('.ctor',2).invoke(size,size);
            const rect=core('Rect').alloc().unbox();rect.method('.ctor',4).invoke(0,0,size,size);
            texture.method('ReadPixels',4).invoke(rect,0,0,false);texture.method('Apply',2).invoke(false,false);
            const bytes=cls('UnityEngine.ImageConversionModule','UnityEngine.ImageConversion').method('EncodeToPNG',1).invoke(texture);
            const encoded=Il2Cpp.corlib.class('System.Convert').method('ToBase64String').overload('System.Byte[]').invoke(bytes);
            return {model_token:m.token,view,width:size,height:size,mime_type:'image/png',base64:encoded.content};
        } finally {
            rtClass.method('set_active').invoke(previous);
            if(go)unityObject.method('DestroyImmediate',1).invoke(go);
            if(texture)unityObject.method('DestroyImmediate',1).invoke(texture);
            if(rt){rt.method('Release').invoke();unityObject.method('DestroyImmediate',1).invoke(rt);}
        }
    }
    function photoScreenshot(m,size){
        const photo=m.root.field('obsoleteLegacyPhotoBoothViewModel').value;
        if(!photo.method('get_IsActive').invoke())throw Error('PHOTO_MODE_REQUIRED');
        const cam=photo.method('get_PhotoBoothCamera').invoke(),rtClass=core('RenderTexture');
        const oldTarget=cam.method('get_targetTexture').invoke(),oldActive=rtClass.method('get_active').invoke();let rt=null,texture=null;
        try{
            rt=rtClass.alloc();rt.method('.ctor',3).invoke(size,size,24);rt.method('Create').invoke();
            invokeManaged(cam,'set_targetTexture',[rt.handle]);invokeManaged(cam,'Render');rtClass.method('set_active').invoke(rt);
            texture=core('Texture2D').alloc();texture.method('.ctor',2).invoke(size,size);
            const rect=core('Rect').alloc().unbox();rect.method('.ctor',4).invoke(0,0,size,size);
            texture.method('ReadPixels',4).invoke(rect,0,0,false);texture.method('Apply',2).invoke(false,false);
            const bytes=cls('UnityEngine.ImageConversionModule','UnityEngine.ImageConversion').method('EncodeToPNG',1).invoke(texture);
            const encoded=Il2Cpp.corlib.class('System.Convert').method('ToBase64String').overload('System.Byte[]').invoke(bytes);
            return {model_token:m.token,view:'photo',width:size,height:size,mime_type:'image/png',base64:encoded.content};
        }finally{
            invokeManaged(cam,'set_targetTexture',[oldTarget.handle]);rtClass.method('set_active').invoke(oldActive);
            if(texture)core('Object').method('DestroyImmediate',1).invoke(texture);
            if(rt){rt.method('Release').invoke();core('Object').method('DestroyImmediate',1).invoke(rt);}
        }
    }
    const extended=createParameterApi({model,cls,core,text,array,invokeManaged,entries,details,value,selector,categories});
    const operations={...extended.operations,status,list_face_params:list,set_face_params:set,task_status:taskStatus,
        prepare_capture(args){const m=model(args.expected_model),hair=m.root.method('get_HairEditor').invoke(),bone=hair.method('get_BoneEditor').invoke(),design=hair.method('get_DesignEditor').invoke();
            if(!bone.handle.isNull()){invokeManaged(bone,'ClearSelection');invokeManaged(bone,'OnLeaveFeature');}
            if(!design.handle.isNull())invokeManaged(design,'ClearSelectHairOutLine');
            const p=m.root.field('obsoleteLegacyPhotoBoothViewModel').value;
            if(p.method('get_IsActive').invoke()){const disabled=Memory.alloc(1);disabled.writeU8(0);invokeManaged(p.method('get_PosesViewModel').invoke(),'set_IsVisibleController',[disabled]);}
            return {model_token:m.token,frame:state.frame};},
        list_presets:a=>listPresets(a,a.area),apply_preset:a=>applyPreset(a,a.area),
        list_body_params:a=>list(a,'body'),set_body_params:a=>set(a,'body'),
        list_clothing_params:a=>list(a,'clothing'),set_clothing_params:a=>set(a,'clothing'),
        list_hair_presets:a=>listPresets(a,'hair'),apply_hair_preset:a=>applyPreset(a,'hair'),
        list_clothing_presets:a=>listPresets(a,'clothing'),apply_clothing_preset:a=>applyPreset(a,'clothing'),
        preset_state:a=>{const m=model(a.expected_model);
            const p=presetEntries(m,a.area).find(p=>p.id===a.preset_id);
            if(!p)throw Error('UNKNOWN_PRESET');
            return {selected:p.selected,model_token:m.token,active_groups:activeGroupSnapshot(m)};},
        undo:a=>history(a,'UndoAsync'),redo:a=>history(a,'RedoAsync'),new_model:newModel,
        save_as:save,open_model:open,screenshot,
        list_start_models:()=>({models:startItems().map(({item,...data})=>data)}),open_start_model:openStartModel,
        list_parts:listParts,replace_part:replacePart,save_custom_items:saveCustomItems,
        vrm_export_state:vrmExportState,enter_vrm_export:enterVrmExport,leave_vrm_export:leaveVrmExport,
        start_vrm_export:startVrmExport,vrm_export_status:vrmExportStatus,
        gc_check(){Il2Cpp.gc.collect(2);return list();}};
    return {dispatch(name,args={}){
        if(!Object.hasOwn(operations,name))throw Error('UNKNOWN_OPERATION');
        // The user's own VRoid keeps its own file: no replacing the model or re-pointing its save path.
        if(ATTACHED&&['new_model','open_model','save_as'].includes(name))throw Error('NOT_ALLOWED_WHEN_ATTACHED: '+name);
        const editOperation=/^(set_(face|body|clothing)_params|apply_.*preset|edit_hair_structure|edit_accessories|generate_hair_bones|save_as|undo|redo|preview_expression|replace_part|save_custom_items)$/.test(name)||name==='set_parameters'&&args.domain!=='photo';
        if(editOperation&&model().root.field('obsoleteLegacyPhotoBoothViewModel').value.method('get_IsActive').invoke())throw Error('RETURN_TO_EDIT_MODE_FIRST');
        return operations[name](args);
    }};
})();
