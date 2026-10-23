# VRoid Character MCP

**v0.4.0 · Windows · 42 MCP tools · stdio**

**English** | [繁體中文](README.zh-TW.md)

Control VRoid Studio character parameters, apply hair and clothing presets, and inspect the result through native screenshots using MCP. Operations run through Frida and VRoid's native methods, without mouse input, keyboard automation, or OCR.

This is an **unofficial, experimental local tool**. By default the server launches only a designated physical copy of VRoid with a separate profile. It attaches to a VRoid you opened yourself only when you call **attach_open_vroid**; edits then change your real model. Copy isolation and in-process write guards are not an operating-system sandbox.

## Features

| Area | Supported controls |
|---|---|
| Face and body | Eyes, eyebrows, nose, mouth, face shape, head/body proportions, shoulders, neck, chest, waist and limbs |
| Height | Centimeter target, whole-body scale adjustment and measurement error |
| Hair | Owned hairstyle/part presets; group/strand parameters, guide transforms, width, thickness, twist, cross-sections and shape curves; procedural group creation and group/strand removal |
| Hair bones | Grouping, bone count, stiffness, gravity, collision radius and generation settings |
| Clothing and accessories | Owned presets and closet custom items, garment shape controls, accessory creation/duplication/removal and available parameters |
| Parts | List the parts a model is built from, replace exactly one part by ID, save worn parts as custom items |
| Colors | Native eye, hair, eyebrow, eyelash, skin and related color controls |
| Expressions and photo preview | Expression definitions and preview, poses, hands, lighting, wind, camera and available photo parameters |
| Visual review | Native 256–2048 pixel screenshots, multiple views, before/after images and parameter comparisons |
| History, saving and export | Native Undo/Redo, save-as to a new .vroid file, VRM 0.x / 1.0 export through VRoid's own exporter |
| Your own VRoid | Attach to a VRoid Studio you opened, open start-screen model cards, detach without closing it |

Texture painting, custom material authoring, hand-drawn hair strands and arbitrary code execution are outside the current scope. Available parameters vary by model, part and mode; this is not complete coverage of every internal API.

## Compatibility

Validated with Windows x64, VRoid Studio 2.14.0 / Unity 6000.0.62f1, Python 3.10, Frida 17.16.0, MCP Python SDK 1.30.0 and frida-il2cpp-bridge 0.14.0. Git, Node.js and npm are required for checkout and dependency installation.

Startup checks GameAssembly.dll against this SHA-256 and rejects other binaries, even if their displayed version is identical. attach_open_vroid applies the same check to the VRoid you opened:

~~~text
793eb5fcff3093f344ee930fbfa0c0796ed7780ac91c45bdb7ce6bd34d62fd3c
~~~

The repository does not include VRoid binaries, characters, screenshots, test output or private client configuration. Supply your own compatible VRoid installation.

## Installation

PowerShell example; replace paths with your own:

~~~powershell
git clone https://github.com/Karylcode/VRoid-MCP.git C:\VRoid-MCP
Set-Location C:\VRoid-MCP
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
& .\.venv\Scripts\python.exe .\prepare_lab.py --source 'D:\SteamLibrary\steamapps\common\VRoid Studio' --lab 'C:\VRoid-MCP-lab'
~~~

prepare_lab.py copies and verifies the installation without modifying its source. The lab directory must **not already exist**. Neither directory may contain the other, and junctions/symlinks are rejected. Allow enough disk space for a full installation copy.

## MCP connection

Configure command, args and env in a stdio-capable MCP client. This generic JSON example may need to be adapted to your client's configuration format:

~~~json
{
  "mcpServers": {
    "vroid": {
      "command": "C:\\VRoid-MCP\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\VRoid-MCP\\launch.py",
        "--lab",
        "C:\\VRoid-MCP-lab"
      ],
      "env": {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
~~~

- Tool discovery is immediate. The VRoid copy starts on the **first tool call**.
- A new server session creates an F00 character by default. Add --variant M00 for the male base.
- To open an existing character, add --model followed by an absolute path to a .vroid file **inside the lab**. Reconnecting does not automatically resume your last character.
- Only one server can own a lab at a time, including while it is attached to your own VRoid. Create separate labs for simultaneous Codex and Claude Code sessions.
- If configurable, allow a longer first-call timeout, such as 120 seconds.
- Reload the MCP connection after updating the code. Save first: shutting down the server closes its own VRoid copy. It never closes a VRoid you opened yourself.

## Editing workflow

1. Call **list_face_params** to obtain model_token. Pass it as expected_model when editing.
2. List parameters or presets before applying changes. Use returned IDs, types, limits and options; follow next_offset pagination.
3. Capture a baseline with **capture_review**.
4. Edit through **set_face_params, set_body_params, set_parameters** or preset tools.
5. Inspect **screenshot/capture_review** images and use Undo when needed. Relist parameters after changing hair, clothing, parts or structure.
6. Apply **set_height** after styling, then **save_as** with a new filename such as character.vroid.

Example arguments for set_parameters. Replace the token and confirm these controls exist and are editable:

~~~json
{
  "expected_model": "<model_token>",
  "domain": "colors",
  "changes": [
    {"id": "colors/Iris/BothEyes", "value": [0.18, 0.50, 0.73, 1]},
    {"id": "colors/Hair/All", "value": [0.90, 0.79, 0.53, 1]}
  ]
}
~~~

For hair, call list_hair_nodes(category="HairTied"), use a returned node ID as scope in list_parameters(domain="hair", category="HairTied", scope=...), then call set_parameters.

For photo preview, use set_preview_mode(mode="photo"), list_parameters(domain="photo"), adjust settings, then screenshot(view="photo"). Return to mode="edit" before editing, capture_review or saving. Photo settings are session-only and are not stored in the .vroid file.

set_face_params and set_body_params accept allow_out_of_ui_range=true, which permits values up to one slider span beyond the UI limits. Use it only to copy values another model really holds, such as samples made with older VRoid versions, not to invent new ones.

## Working with your own VRoid

- **attach_open_vroid(pid?)** switches every tool to a VRoid Studio you opened yourself, such as the Steam version. pid is needed only when several VRoid windows are open; the error then lists the candidates. If the MCP copy is already running, pass discard_copy_unsaved=true and it is closed (save_as first when useful).
- Edits go through VRoid's native history, so Ctrl+Z works in VRoid. save_as and opening or creating models are refused; save in VRoid yourself.
- The isolation hooks are not loaded. Your VRoid keeps its own files, registry settings and child processes; only the hooks needed to read and write parameters are installed.
- Unity pauses its main loop while VRoid is unfocused. Attaching wakes the message loop and keeps VRoid processing in the background. If the main thread still does not respond, click the VRoid window once and call the tool again.
- If VRoid is on its start screen, **list_start_models** lists recent models, built-in AvatarSample models and old models, and **open_start_model(name)** opens one like clicking its card. It waits up to 90 seconds and works only while no model is open, so unsaved work is never replaced.
- **detach_open_vroid** gives VRoid back its own background setting, releases handles and unloads the hooks. VRoid keeps running with its unsaved work intact. The next tool call starts the MCP copy again. restart_session only detaches while attached.
- If VRoid runs as administrator (for example because Steam does), the MCP client must also run as administrator; otherwise attaching fails with PermissionError.

## Parts and custom items

- **list_parts** lists every part (transferable group) the model is built from: id, type, resource_name, original_resource_name for custom parts, and custom/updated flags.
- **replace_part(part_id)** replaces exactly one part, for example a single face shape without the rest of its face set. It accepts built-in IDs and custom items registered in this VRoid's closet. IDs missing from the asset catalog, such as part IDs from files made with older VRoid versions, are refused because VRoid's native loader crashes on them.
- **save_custom_items(types?)** saves worn parts that VRoid marks savable (custom or modified) as custom items, like VRoid's own "save as custom item". Files go to the custom_items folder of the controlled VRoid: the lab profile for the copy, your real closet when attached.
- list_presets also lists closet custom items with custom=true; apply them with apply_preset.

To rebuild an older character on the current VRoid version, match its parts by resource_name, save its custom or modified parts with save_custom_items, apply them on the new model, use replace_part for single parts, then copy the values and compare.

## VRM export

**export_vrm(expected_model, filename, version=1)** exports through VRoid's own exporter. version 1 is VRM 1.0 and 0 is VRM 0.x.

- Files are written under lab/exports/. Existing files are never overwritten. The export screen is entered and left automatically.
- Name, authors and license come from the VRM export meta stored in the model. Export is refused if the model has no name.
- VRoid's default settings are used: hair meshes combined, no material or mesh reduction.
- Works on the MCP copy and on your own VRoid after attach_open_vroid.

## Screenshot review

screenshot accepts front, side, back and three_quarter for the head; prefix them with full_ for full-body views. Use photo for the active photo preview. size defaults to 512 and accepts 256–2048 pixels.

capture_review defaults to four 1024-pixel images: front, three_quarter, full_front and full_back. You can request one to six distinct model views:

~~~json
{
  "expected_model": "<model_token>",
  "label": "Before editing",
  "views": ["front", "three_quarter", "full_front", "full_back"],
  "size": 1024
}
~~~

The tool returns images, a capture_id, height readings and a visual checklist. PNGs and parameter snapshots are saved under `lab/reviews/<capture_id>/`.

After editing, pass the previous capture_id as baseline_id with the same views and size to obtain before/after images and face/body/clothing/color parameter differences. Reviews with different model tokens are explicitly identified.

This provides evidence for visual inspection, **not an automated beauty score or collision test**. Hair geometry changes require image inspection, and hair physics may vary between frames. Capturing images does not save the character.

## Behavior and limitations

- Batches are not transactions. Inputs are validated first, but a native execution error may leave partial edits. Inspect ok, applied and error. A batch may require several Undo steps.
- save_as accepts a single .vroid filename, writes only under lab/saves/ and refuses to overwrite an existing file.
- restart_session(discard_unsaved=true) recreates only the MCP-owned copy and discards unsaved changes. Its new token invalidates the previous model identity.
- Some hair presets expand into parts without retaining the whole-set checkbox. selected=false alone does not establish failure; inspect changed, confirmation and screenshots.
- Height depends on styling and proportions. get_height reports both cached UI centimeters and live_centimeters; they can differ slightly.
- F00 is the primary validation target. M00, comprehensive unfocused operation and long-running stability have not received equivalent validation.

## Changes in 0.4.0

- New tools: attach_open_vroid, detach_open_vroid, list_start_models, open_start_model, list_parts, replace_part, save_custom_items and export_vrm.
- Isolation fix: in 0.3.2 the copy could still write file_access_history.json, history_temp and vroid_file_temporary into your real `LocalLow\pixiv\VRoid Studio` profile. Unity resolves its data path through windows.storage.dll, some file calls go straight to kernelbase.dll, and Frida skips Interceptor listeners during native calls made from the agent. Folder lookups are now hooked in every exporting module, file and registry hooks sit on kernelbase.dll with CreateFile2, CopyFile*, MoveFileWithProgressW, SetFileAttributesW and CreateDirectoryExW added, and agent/traps.js makes every NativeFunction use traps:'all'.
- Accessory IsVisible now uses VRoid's native visibility history command. Before, it only changed the list icon and the mesh stayed visible.
- set_face_params and set_body_params accept allow_out_of_ui_range.
- capture_review no longer sends every PNG a second time as base64 structured content.

## Tests

Unit tests do not start VRoid:

~~~powershell
& .\.venv\Scripts\python.exe -m pip install pytest
& .\.venv\Scripts\python.exe -m pytest -q
~~~

Live MCP/VRoid tests are in tests/. Prepare a separate lab and run only one test against it at a time:

~~~powershell
& .\.venv\Scripts\python.exe .\tests\stdio_acceptance.py C:\VRoid-MCP-test-lab .\test-evidence\stdio
~~~

Local validation for 0.3.2 included 26 unit tests and real MCP tests covering multi-view images, resolutions, before/after comparison, Undo, invalid requests and compatibility with the original screenshot interface. The 0.4.0 features were checked by hand against VRoid Studio 2.14.0: saving from the copy left the real profile unchanged, repeated exports of the same .vroid were byte-identical, and an AvatarSample_M rebuilt through parts matched the original in all 38 parts and every listed value. They do not have acceptance scripts in tests/ yet. Evidence and character fixtures are kept locally rather than committed.

## Source layout

| Path | Purpose |
|---|---|
| launch.py | stdio entry point |
| prepare_lab.py | Verified installation copy |
| vroid_mcp/server.py | MCP tool definitions |
| vroid_mcp/runtime.py | Process lifecycle, attaching, native calls and artifacts |
| agent/traps.js | Makes native calls keep firing the isolation hooks |
| agent/bootstrap.js | Unity main-thread dispatch and adopting an already running VRoid |
| agent/isolate.js | Private profile and in-process write guards |
| agent/operations.js | Model, history, parts, saving, VRM export and capture |
| agent/parameters.js | Typed parameter interfaces |
| tests/ | Unit and live integration tests |
