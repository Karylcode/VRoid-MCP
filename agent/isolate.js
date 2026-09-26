// Process-local safeguards for the disposable copy. Not a system sandbox.
const norm = p => p.replace(/^\\\\\?\\/, '').replace(/\//g, '\\').toLowerCase();
const lab = norm(PROBE.root);
if (norm(Process.mainModule.path) !== norm(PROBE.exe) || PROBE.excludedPids.includes(Process.id)) {
    throw new Error('Refusing to instrument anything except the designated disposable copy');
}
const pins = [];
const guarded = new Set();
const within = p => norm(p) === lab || norm(p).startsWith(lab + '\\');
function replaceArg(ctx, args, index, value) {
    ctx.path = Memory.allocUtf16String(value);
    args[index] = ctx.path;
}
function logOnce(kind, path) {
    const key = kind + ':' + path;
    if (!guarded.has(key)) { guarded.add(key); send({kind, path}); }
}
const blocked = PROBE.root + '\\blocked-outside-workspace\\denied';
function hookPathWrite(module, name, index) {
    const addr = module.findExportByName(name);
    if (!addr) return;
    pins.push(Interceptor.attach(addr, {onEnter(args) {
        let p = args[index].isNull() ? '' : args[index].readUtf16String();
        const mapped=remapFolder(p);
        if(mapped!==p){replaceArg(this,args,index,mapped);p=mapped;}
        if (p && !within(p) && !p.startsWith('\\\\.\\')) {
            logOnce('redirected-outside-write', p);
            replaceArg(this, args, index, blocked);
        }
    }}));
}
const kernel = Process.getModuleByName('kernel32.dll');
// A self-relaunch would lose this process's safeguards. This copy needs no children.
for(const name of ['CreateProcessW','CreateProcessA']){
    const address=kernel.findExportByName(name);
    if(!address)continue;
    const callback=new NativeCallback(function(){
        this.lastError=5;logOnce('blocked-child-process',name);return 0;
    },'bool',['pointer','pointer','pointer','pointer','bool','uint32','pointer','pointer','pointer','pointer']);
    pins.push(callback);Interceptor.replace(address,callback);
}
pins.push(Interceptor.attach(kernel.getExportByName('CreateFileW'), {onEnter(args) {
    let p = args[0].isNull() ? '' : args[0].readUtf16String();
    const mapped=remapFolder(p);
    if(mapped!==p){replaceArg(this,args,0,mapped);p=mapped;}
    if (!p || within(p) || p.startsWith('\\\\.\\')) return;
    const access = args[1].toUInt32(), disposition = args[4].toUInt32();
    const writes = (access & 0x400d0116) !== 0 || disposition !== 3;
    if (writes || /\.vroid(?:$|[.\\])/i.test(p)) {
        logOnce(writes ? 'redirected-outside-write' : 'blocked-external-model', p);
        replaceArg(this, args, 0, blocked);
    }
}}));
for (const name of ['DeleteFileW', 'CreateDirectoryW', 'RemoveDirectoryW']) hookPathWrite(kernel, name, 0);
for (const name of ['MoveFileW', 'MoveFileExW', 'ReplaceFileW']) {
    hookPathWrite(kernel, name, 0); hookPathWrite(kernel, name, 1);
}
const shell = Module.load('shell32.dll');
const ole = Module.load('ole32.dll');
const alloc = new NativeFunction(ole.getExportByName('CoTaskMemAlloc'), 'pointer', ['size_t']);
const free = new NativeFunction(ole.getExportByName('CoTaskMemFree'), 'void', ['pointer']);
function remapFolder(p) {
    if (within(p)) return p;
    p=p.replace(/^\\\\\?\\/, '').replace(/\//g, '\\');
    const original = norm(PROBE.originalProfile);
    if (norm(p) === original || norm(p).startsWith(original + '\\')) {
        return PROBE.root + '\\profile' + p.slice(PROBE.originalProfile.length);
    }
    return p;
}
// Unity also caches some absolute paths before managed initialization.
// Redirect subsequent file-system reads as well as writes to the private profile.
for (const [name, indexes] of [
    ['CreateFileW',[0]],['CreateDirectoryW',[0]],['DeleteFileW',[0]],['RemoveDirectoryW',[0]],
    ['GetFileAttributesW',[0]],['GetFileAttributesExW',[0]],['FindFirstFileW',[0]],['FindFirstFileExW',[0]],
    ['MoveFileW',[0,1]],['MoveFileExW',[0,1]],['ReplaceFileW',[0,1]]
]) {
    const address=kernel.findExportByName(name);
    if(!address) continue;
    pins.push(Interceptor.attach(address,{onEnter(args){
        this.strings=[];
        for(const i of indexes){
            if(args[i].isNull()) continue;
            const before=args[i].readUtf16String(),after=remapFolder(before);
            if(before!==after){
                const p=Memory.allocUtf16String(after);this.strings.push(p);args[i]=p;
            }
        }
    }}));
}
pins.push(Interceptor.attach(shell.getExportByName('SHGetKnownFolderPath'), {
    onEnter(args) { this.out = args[3]; },
    onLeave(ret) {
        if (ret.toInt32() !== 0 || this.out.isNull()) return;
        const old = this.out.readPointer();
        if (old.isNull()) return;
        const before = old.readUtf16String(), after = remapFolder(before);
        if (after === before) return;
        const memory = alloc((after.length + 1) * 2);
        memory.writeUtf16String(after); this.out.writePointer(memory); free(old);
        logOnce('isolated-known-folder', after);
    }
}));
pins.push(Interceptor.attach(shell.getExportByName('SHGetFolderPathW'), {
    onEnter(args) { this.out = args[4]; },
    onLeave(ret) {
        if (ret.toInt32() !== 0 || this.out.isNull()) return;
        const before = this.out.readUtf16String(), after = remapFolder(before);
        if (after !== before && after.length < 260) {
            this.out.writeUtf16String(after); logOnce('isolated-folder', after);
        }
    }
}));
// Give this process its own PlayerPrefs key. Existing VRoid keys are never written.
const advapi = Module.load('advapi32.dll');
for (const name of ['RegCreateKeyExW', 'RegOpenKeyExW']) {
    pins.push(Interceptor.attach(advapi.getExportByName(name), {onEnter(args) {
        if (args[1].isNull()) return;
        const p = args[1].readUtf16String();
        if (/^software\\pixiv\\vroid studio(?:\\|$)/i.test(p)) {
            const isolated = p.replace(/^software\\pixiv\\vroid studio/i, PROBE.registryKey);
            logOnce('isolated-registry', isolated); replaceArg(this, args, 1, isolated);
        }
    }}));
}
send({kind:'isolation-ready', pid:Process.id, executable:Process.mainModule.path});
