# VRoid Character MCP

**v0.3.2 · Windows · 34 MCP tools · stdio**

**English** | [繁體中文](README.zh-TW.md)

Control VRoid Studio character parameters, apply hair and clothing presets, and inspect the result through native screenshots using MCP. Operations run through Frida and VRoid's native methods, without mouse input, keyboard automation, or OCR.

This is an **unofficial, experimental local tool**. The server launches only a designated physical copy of VRoid with a separate profile. It does not attach to your existing VRoid process. Copy isolation and in-process write guards are not an operating-system sandbox.

## Features

| Area | Supported controls |
|---|---|
| Face and body | Eyes, eyebrows, nose, mouth, face shape, head/body proportions, shoulders, neck, chest, waist and limbs |
| Height | Centimeter target, whole-body scale adjustment and measurement error |
| Hair | Owned hairstyle/part presets; group/strand parameters, guide transforms, width, thickness, twist, cross-sections and shape curves; procedural group creation and group/strand removal |
| Hair bones | Grouping, bone count, stiffness, gravity, collision radius and generation settings |
| Clothing and accessories | Owned presets, garment shape controls, accessory creation/duplication/removal and available parameters |
| Colors | Native eye, hair, eyebrow, eyelash, skin and related color controls |
| Expressions and photo preview | Expression definitions and preview, poses, hands, lighting, wind, camera and available photo parameters |
| Visual review | Native 256–2048 pixel screenshots, multiple views, before/after images and parameter comparisons |
| History and saving | Native Undo/Redo and save-as to a new .vroid file |

Texture painting, custom material authoring, hand-drawn hair strands, VRM export and arbitrary code execution are outside the current scope. Available parameters vary by model, part and mode; this is not complete coverage of every internal API.

## Compatibility

Validated with Windows x64, VRoid Studio 2.14.0 / Unity 6000.0.62f1, Python 3.10, Frida 17.16.0, MCP Python SDK 1.30.0 and frida-il2cpp-bridge 0.14.0. Git, Node.js and npm are required for checkout and dependency installation.

Startup checks GameAssembly.dll against this SHA-256 and rejects other binaries, even if their displayed version is identical:

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
- Only one server can own a lab at a time. Create separate labs for simultaneous Codex and Claude Code sessions.
- If configurable, allow a longer first-call timeout, such as 120 seconds.
- Reload the MCP connection after updating the code. Save first: shutting down the server closes its own VRoid copy.

## Editing workflow

1. Call **list_face_params** to obtain model_token. Pass it as expected_model when editing.
2. List parameters or presets before applying changes. Use returned IDs, types, limits and options; follow next_offset pagination.
3. Capture a baseline with **capture_review**.
4. Edit through **set_face_params, set_body_params, set_parameters** or preset tools.
5. Inspect **screenshot/capture_review** images and use Undo when needed. Relist parameters after changing hair, clothing or structure.
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

Local validation for 0.3.2 included 26 unit tests and real MCP tests covering multi-view images, resolutions, before/after comparison, Undo, invalid requests and compatibility with the original screenshot interface. Evidence and character fixtures are kept locally rather than committed.

## Source layout

| Path | Purpose |
|---|---|
| launch.py | stdio entry point |
| prepare_lab.py | Verified installation copy |
| vroid_mcp/server.py | MCP tool definitions |
| vroid_mcp/runtime.py | Process lifecycle, native calls and artifacts |
| agent/bootstrap.js | Unity main-thread dispatch |
| agent/isolate.js | Private profile and in-process write guards |
| agent/operations.js | Model, history, saving and capture |
| agent/parameters.js | Typed parameter interfaces |
| tests/ | Unit and live integration tests |
