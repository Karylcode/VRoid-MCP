**English** | [繁體中文](troubleshooting.zh-TW.md) · [Documentation index](README.md)

# Troubleshooting

## Common situations

- **The first call is slow or times out.** The first tool call starts VRoid. If your client allows it, set a longer first-call timeout, such as 120 seconds.
- **"Another MCP process already owns this lab".** Only one server can own a lab at a time, including while it is attached to your own VRoid. Close the other server or create a separate lab, for example one for Codex and one for Claude Code.
- **PermissionError when attaching.** VRoid runs as administrator (for example because Steam does). Run the MCP client as administrator too, or start Steam/VRoid without administrator rights.
- **"VRoid main thread did not respond".** Unity pauses its main loop while VRoid is unfocused. Click the VRoid window once and call the tool again.
- **New tools do not appear after updating.** Reload the MCP connection. Save first: shutting down the server closes its own VRoid copy.

## Error messages

| Message | What to do |
|---|---|
| Untested VRoid binary / UNTESTED_UNITY_VERSION | The VRoid build does not match the validated SHA-256 or Unity version. Use the build listed in [Installation](installation.md#compatibility). |
| VRoid copy or frida-il2cpp-bridge is missing | Run npm ci in the repository, and check that --lab points to a lab made by prepare_lab.py. |
| app/ must be a physical copy, not a link | Create a new lab with prepare_lab.py. |
| No VRoid Studio window opened outside the MCP was found | Open VRoid yourself before attach_open_vroid. |
| Several VRoid windows are open; pass pid | Call attach_open_vroid again with one of the listed pids. |
| The MCP copy is running: save_as first or pass discard_copy_unsaved=true | save_as if needed, then attach with discard_copy_unsaved=true. |
| NO_MODEL | Your VRoid shows its start screen. Use open_start_model, or open a model in VRoid. |
| EXPECTED_MODEL_REQUIRED | The call had no model_token. Call list_face_params and pass its model_token as expected_model. |
| STALE_MODEL / MODEL_CHANGED_DURING_OPERATION | The model changed. List parameters again and use the new model_token. |
| RETURN_TO_EDIT_MODE_FIRST | Call set_preview_mode(mode="edit"). |
| PHOTO_MODE_REQUIRED | Call set_preview_mode(mode="photo") first. |
| COPY_DISCONNECTED | The copy exited. Call restart_session(discard_unsaved=true) or restart the MCP server; the copy's unsaved changes are lost. |
| ATTACHED_VROID_DISCONNECTED | Call attach_open_vroid again, or detach_open_vroid. |
| Native call timed out / PREVIOUS_CALL_UNCERTAIN | Do not retry the change. See [Behavior and limitations](limitations.md#behavior). |
| Height did not converge within native range | The target is outside the model's reachable range. The original scale was restored. |
| UNKNOWN_PART_ID | The ID is not in this VRoid's asset catalog; replace_part takes built-in part IDs only. Use list_presets and apply_preset for built-in presets and closet custom items. |
| VRM_META_NAME_REQUIRED / VRM_META_TITLE_REQUIRED | Set the model's VRM name (1.0) or title (0.x) in VRoid first. |
| Refusing to overwrite an existing file | Choose a new filename. |
| REPLACE_PART_FAILED / VRM_EXPORT_FAILED | Read VRoid's Player.log (see below). |

## Logs

Each session writes bridge.jsonl (bridge events) to `<lab>\runs\<timestamp>-<id>\`. For the copy, VRoid's Player.log is written to the same folder. When attached, VRoid writes Player.log to its own usual location.
