// Frida skips every Interceptor listener during native calls made from JS unless the NativeFunction
// uses traps:'all'. VRoid's own file I/O inside an MCP call (save, new model, history temp) then
// bypassed isolate.js and wrote into the user's real profile. Default every NativeFunction to 'all',
// including the ones frida-il2cpp-bridge creates for managed method calls.
(() => {
    const Native = NativeFunction;
    globalThis.NativeFunction = function (address, returnType, argTypes, options) {
        const extra = typeof options === 'string' ? {abi: options} : (options || {});
        return new Native(address, returnType, argTypes, Object.assign({traps: 'all'}, extra));
    };
})();
