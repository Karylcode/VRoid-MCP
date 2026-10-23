const state={ready:false,error:null,mainThread:0,frame:0,lastExec:0,modelUpdates:0,refs:{},handles:{},hooks:[],pump:[],queue:[],draining:false};
function cls(assembly,name){return Il2Cpp.domain.assembly(assembly).image.class(name);}
let gcNew,gcGet,gcFree;
function retain(object){
    // Unity 6 uses pointer-sized Il2CppGCHandle. Bridge 0.14.0 declares uint32.
    const handle=gcNew(object.handle,0);
    if(!gcGet(handle).equals(object.handle))throw Error('GC_HANDLE_ABI_MISMATCH');
    let freed=false;
    return {free(){if(!freed){gcFree(handle);freed=true;}}};
}
function keep(name,object){
    state.handles[name]?.free();state.handles[name]=retain(object);
    state.refs[name]=object.handle.toString();
}
function enqueue(block,wake=false){
    if(!state.ready)return Promise.reject(Error(state.error||'BRIDGE_NOT_READY'));
    if(state.queue.length>=32)return Promise.reject(Error('QUEUE_FULL'));
    return new Promise((resolve,reject)=>{
        const job={block,wake,resolve,reject,deadline:Date.now()+12000};
        job.timer=setTimeout(()=>{const i=state.queue.indexOf(job);if(i>=0){state.queue.splice(i,1);reject(Error('MAIN_THREAD_TIMEOUT: not executed'));}},12000);
        state.queue.push(job);
        // WM_NULL wakes a paused player's message loop so pumpTick can run the job. The main
        // thread may already sit in GetMessage from before the hook existed; that call returns
        // without onLeave, so keep posting until a hooked call takes the job.
        const wakeUp=()=>{
            if(!state.queue.includes(job))return;
            state.postThreadMessage(state.mainThread,0,NULL,NULL);setTimeout(wakeUp,100);
        };
        if(wake&&state.postThreadMessage)wakeUp();
    });
}
function drain(){
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
function tick(){
    if(Process.getCurrentThreadId()!==state.mainThread||state.draining)return;
    state.frame++;state.lastExec=Date.now();
    drain();
}
function pumpTick(){
    // An attached VRoid pauses its player loop while unfocused. Only adopt/release
    // jobs may run from its message pump, and only when Exec has stopped ticking.
    if(Process.getCurrentThreadId()!==state.mainThread||state.draining)return;
    if(Date.now()-state.lastExec<250||!state.queue[0]?.wake)return;
    drain();
}
function unityWindowThread(){
    // Il2Cpp.mainThread is the first entry of IL2CPP's attached-thread list, which can be
    // another thread once earlier Frida sessions attached and detached. Unity's main
    // thread owns the player window and pumps its messages.
    const user32=Process.getModuleByName('user32.dll');
    const findWindowEx=new NativeFunction(user32.getExportByName('FindWindowExW'),'pointer',['pointer','pointer','pointer','pointer']);
    const windowThread=new NativeFunction(user32.getExportByName('GetWindowThreadProcessId'),'uint32',['pointer','pointer']);
    const unityClass=Memory.allocUtf16String('UnityWndClass'),owner=Memory.alloc(4);
    for(let window=findWindowEx(NULL,NULL,unityClass,NULL);!window.isNull();window=findWindowEx(NULL,window,unityClass,NULL)){
        const thread=windowThread(window,owner);
        if(owner.readU32()===Process.id)return thread;
    }
    throw Error('UNITY_WINDOW_NOT_FOUND');
}
function forceBackground(){
    state.bgHook=Interceptor.attach(state.bgAddress,{onEnter(args){args[0]=ptr(1);}});
}
function adoptRunning(){
    // Constructors already ran in a running VRoid; find the live view models instead.
    const found={};
    for(const name of ['VRoid.Studio.MainViewModel','VRoid.Studio.EditRootScreen.ViewModel']){
        const c=cls('VRoid.Studio',name);
        found[name]=Il2Cpp.gc.choose(c).filter(o=>o.class.handle.equals(c.handle));
    }
    const mains=found['VRoid.Studio.MainViewModel'];
    if(mains.length!==1)throw Error('MAIN_VIEW_MODEL_NOT_FOUND: '+mains.length);
    keep('VRoid.Studio.MainViewModel',mains[0]);
    const file=mains[0].field('_mainModel').value.field('currentFile').value;
    const engine=file.handle.isNull()?null:file.field('engine').value;
    const root=engine&&found['VRoid.Studio.EditRootScreen.ViewModel']
        .find(r=>r.field('_engineModel').value.handle.equals(engine.handle));
    if(root)keep('VRoid.Studio.EditRootScreen.ViewModel',root);
    if(!state.background){
        const scope=cls('VRoid.UI','VRoid.UI.Util.RunInBackgroundUtil').method('EnableRunInBackgroundScoped').invoke();
        state.background=scope;state.backgroundHandle=retain(scope);forceBackground();
    }
    for(const hook of state.pump)hook.detach();
    state.pump=[];
    return {main_view_model:true,edit_root:!!root,
        background:cls('UnityEngine.CoreModule','UnityEngine.Application').method('get_runInBackground').invoke()};
}
function releaseAttached(){
    // Give the user's VRoid back its own background setting and drop our GC handles.
    state.bgHook?.detach();state.bgHook=null;
    if(state.background){
        const scope=state.background;state.background=null;
        try{(scope.tryMethod('Dispose')??scope.method('System.IDisposable.Dispose')).invoke();}
        finally{state.backgroundHandle.free();}
    }
    for(const handle of Object.values(state.handles))handle.free();
    state.handles={};state.refs={};
    return {released:true};
}
Il2Cpp.perform(()=>{
    if(Il2Cpp.unityVersion!=='6000.0.62f1')throw Error('UNTESTED_UNITY_VERSION: '+Il2Cpp.unityVersion);
    // A spawned copy runs this block on its main thread; an attached VRoid runs it on Frida's thread.
    state.mainThread=ATTACHED?unityWindowThread():Process.getCurrentThreadId();
    gcNew=new NativeFunction(Il2Cpp.module.getExportByName('il2cpp_gchandle_new'),'pointer',['pointer','bool']);
    gcGet=new NativeFunction(Il2Cpp.module.getExportByName('il2cpp_gchandle_get_target'),'pointer',['pointer']);
    gcFree=new NativeFunction(Il2Cpp.module.getExportByName('il2cpp_gchandle_free'),'void',['pointer']);
    state.bgAddress=Il2Cpp.exports.resolveInternalCall(Memory.allocUtf8String('UnityEngine.Application::set_runInBackground'));
    if(state.bgAddress.isNull())throw Error('BACKGROUND_BINDING_MISSING');
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
                    keep(name,object);
                }
            }));
        }
    }
    if(ATTACHED){
        const user32=Process.getModuleByName('user32.dll');
        state.postThreadMessage=new NativeFunction(user32.getExportByName('PostThreadMessageW'),'bool',['uint32','uint32','pointer','pointer']);
        for(const name of ['PeekMessageW','PeekMessageA','GetMessageW','GetMessageA']){
            const address=user32.findExportByName(name);
            if(address)state.pump.push(Interceptor.attach(address,{onLeave:pumpTick}));
        }
    }else{
        const bg=cls('VRoid.UI','VRoid.UI.Util.RunInBackgroundUtil');
        state.hooks.push(Interceptor.attach(bg.method('Initialize').virtualAddress,{onLeave(){
            if(Process.getCurrentThreadId()!==state.mainThread)return;
            // Initialize must first reset its flag/count consistently; hold the scope afterwards.
            forceBackground();
            try{const scope=bg.method('EnableRunInBackgroundScoped').invoke();state.background=scope;state.backgroundHandle=retain(scope);}
            catch(e){send({event:'background-scope-error',error:String(e)});}
        }}));
    }
    state.hooks.push(Interceptor.attach(cls('VRoid.Studio','VRoid.Studio.Engine.Model')
        .method('OnModelUpdateComplete').virtualAddress,{onLeave(){state.modelUpdates++;}}));
    state.ready=true;
    send({event:'ready',pid:Process.id,unity:Il2Cpp.unityVersion,main_thread:state.mainThread,attached:ATTACHED});
},ATTACHED?'free':'main').catch(e=>{state.error=String(e);send({event:'init-error',error:String(e)});});
rpc.exports={
    health(){return {ready:state.ready,error:state.error,pid:Process.id,frame:state.frame};},
    call(name,args){return enqueue(()=>vroid.dispatch(name,args||{}));},
    adopt(){return enqueue(adoptRunning,true);},
    release(){return enqueue(releaseAttached,true);}
};
