const state={ready:false,error:null,mainThread:0,frame:0,modelUpdates:0,refs:{},handles:{},hooks:[],queue:[],draining:false};
function cls(assembly,name){return Il2Cpp.domain.assembly(assembly).image.class(name);}
let gcNew,gcGet,gcFree;
function retain(object){
    // Unity 6 uses pointer-sized Il2CppGCHandle. Bridge 0.14.0 declares uint32.
    const handle=gcNew(object.handle,0);
    if(!gcGet(handle).equals(object.handle))throw Error('GC_HANDLE_ABI_MISMATCH');
    let freed=false;
    return {free(){if(!freed){gcFree(handle);freed=true;}}};
}
function enqueue(block){
    if(!state.ready)return Promise.reject(Error(state.error||'BRIDGE_NOT_READY'));
    if(state.queue.length>=32)return Promise.reject(Error('QUEUE_FULL'));
    return new Promise((resolve,reject)=>{
        const job={block,resolve,reject,deadline:Date.now()+12000};
        job.timer=setTimeout(()=>{const i=state.queue.indexOf(job);if(i>=0){state.queue.splice(i,1);reject(Error('MAIN_THREAD_TIMEOUT: not executed'));}},12000);
        state.queue.push(job);
    });
}
function tick(){
    if(Process.getCurrentThreadId()!==state.mainThread||state.draining)return;
    state.frame++;
    const job=state.queue.shift();if(!job)return;
    clearTimeout(job.timer);state.draining=true;
    try{
        if(Date.now()>job.deadline)throw Error('MAIN_THREAD_TIMEOUT: not executed');
        if(Il2Cpp.currentThread===null||Il2Cpp.currentThread.id!==state.mainThread)throw Error('UNREGISTERED_THREAD');
        const result=job.block();
        if(result instanceof Promise)throw Error('ASYNC_MANAGED_CALL_FORBIDDEN');
        job.resolve(result);
    }catch(e){job.reject(e);}finally{state.draining=false;}
}
Il2Cpp.perform(()=>{
    if(Il2Cpp.unityVersion!=='6000.0.62f1')throw Error('UNTESTED_UNITY_VERSION: '+Il2Cpp.unityVersion);
    state.mainThread=Process.getCurrentThreadId();
    gcNew=new NativeFunction(Il2Cpp.module.getExportByName('il2cpp_gchandle_new'),'pointer',['pointer','bool']);
    gcGet=new NativeFunction(Il2Cpp.module.getExportByName('il2cpp_gchandle_get_target'),'pointer',['pointer']);
    gcFree=new NativeFunction(Il2Cpp.module.getExportByName('il2cpp_gchandle_free'),'void',['pointer']);
    const bgAddress=Il2Cpp.exports.resolveInternalCall(Memory.allocUtf8String('UnityEngine.Application::set_runInBackground'));
    if(bgAddress.isNull())throw Error('BACKGROUND_BINDING_MISSING');
    // Hook the native binding because IL2CPP can inline the managed property wrapper.
    state.hooks.push(Interceptor.attach(cls('UnityEngine.CoreModule','UnityEngine.UnitySynchronizationContext')
        .method('Exec').virtualAddress,{onLeave:tick}));
    for(const name of ['VRoid.Studio.MainViewModel','VRoid.Studio.EditRootScreen.ViewModel']){
        const c=cls('VRoid.Studio',name);
        for(const method of c.methods.filter(m=>m.name==='.ctor'&&!m.virtualAddress.isNull())){
            state.hooks.push(Interceptor.attach(method.virtualAddress,{
                onEnter(args){this.object=args[0];},onLeave(){
                    if(Process.getCurrentThreadId()!==state.mainThread)return;
                    const object=new Il2Cpp.Object(this.object);
                    if(!object.class.handle.equals(c.handle))return;
                    state.handles[name]?.free();state.handles[name]=retain(object);
                    state.refs[name]=object.handle.toString();
                }
            }));
        }
    }
    const bg=cls('VRoid.UI','VRoid.UI.Util.RunInBackgroundUtil');
    state.hooks.push(Interceptor.attach(bg.method('Initialize').virtualAddress,{onLeave(){
        if(Process.getCurrentThreadId()!==state.mainThread)return;
        // Initialize must first reset its flag/count consistently; hold the scope afterwards.
        state.hooks.push(Interceptor.attach(bgAddress,{onEnter(args){args[0]=ptr(1);}}));
        try{const scope=bg.method('EnableRunInBackgroundScoped').invoke();state.background=scope;state.backgroundHandle=retain(scope);}
        catch(e){send({event:'background-scope-error',error:String(e)});}
    }}));
    state.hooks.push(Interceptor.attach(cls('VRoid.Studio','VRoid.Studio.Engine.Model')
        .method('OnModelUpdateComplete').virtualAddress,{onLeave(){state.modelUpdates++;}}));
    state.ready=true;
    send({event:'ready',pid:Process.id,unity:Il2Cpp.unityVersion,main_thread:state.mainThread});
},'main').catch(e=>{state.error=String(e);send({event:'init-error',error:String(e)});});
rpc.exports={
    health(){return {ready:state.ready,error:state.error,pid:Process.id,frame:state.frame};},
    call(name,args){return enqueue(()=>vroid.dispatch(name,args||{}));}
};
