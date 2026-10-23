**English** | [繁體中文](own-vroid.zh-TW.md) · [Documentation index](README.md)

# Working with your own VRoid

By default every tool works on the MCP copy. **attach_open_vroid** switches every tool to a VRoid Studio you opened yourself. **Edits then change your real model.**

## Attaching

- **attach_open_vroid(pid?)** switches every tool to a VRoid Studio you opened yourself, such as the Steam version. pid is needed only when several VRoid windows are open; the error then lists the candidates.
- If the MCP copy is already running, pass discard_copy_unsaved=true and it is closed (save_as first when useful).
- attach_open_vroid checks your VRoid's GameAssembly.dll against the same SHA-256 as the copy. Other builds are refused.
- The server still needs --lab. Only one server can own a lab at a time, including while it is attached.
- If VRoid runs as administrator (for example because Steam does), the MCP client must also run as administrator; otherwise attaching fails with PermissionError.

## While attached

- Edits go through VRoid's native history, so Ctrl+Z works in VRoid.
- save_as and opening or creating models are refused; save in VRoid yourself. The only exception is open_start_model on the start screen (see below).
- **save_custom_items** writes into your real closet (the custom_items folder of your VRoid profile), not into the lab.
- export_vrm works and writes the file to the lab's exports folder.
- The isolation hooks are not loaded. Your VRoid keeps its own files, registry settings and child processes; only the hooks needed to read and write parameters are installed.
- Unity pauses its main loop while VRoid is unfocused. Attaching wakes the message loop and keeps VRoid processing in the background. If the main thread still does not respond, click the VRoid window once and call the tool again.

## Start screen

If VRoid is on its start screen, **list_start_models** lists recent models, built-in AvatarSample models and old models. **open_start_model(name)** opens one like clicking its card; pass group (recent, sample or old) if the name is ambiguous. It waits up to 90 seconds and works only while no model is open, so unsaved work is never replaced. If loading takes longer, for example while a sample downloads or a dialog is shown, it returns opened=false; check get_status.

The MCP copy always has a model open, so open_start_model is mainly for your own VRoid.

## Detaching

- **detach_open_vroid** gives VRoid back its own background setting, releases handles and unloads the hooks. VRoid keeps running with its unsaved work intact. The next tool call starts the MCP copy again.
- restart_session only detaches while attached: your VRoid is not closed. A fresh MCP copy then starts.
- Shutting down the server detaches the same way. It never closes a VRoid you opened yourself.
- If the connection to your VRoid is lost, tools report ATTACHED_VROID_DISCONNECTED. Call attach_open_vroid again, or detach_open_vroid.
