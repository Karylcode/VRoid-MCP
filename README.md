**English** | [繁體中文](README.zh-TW.md)

# VRoid Character MCP

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/)
[![VRoid Studio 2.14.0](https://img.shields.io/badge/VRoid%20Studio-2.14.0-orange.svg)](https://vroid.com/studio)

A local MCP server with 42 MCP tools that lets an AI client edit VRoid Studio characters: face, body and clothing sliders, hair, accessories, colors, presets and parts. It checks the result with native screenshots and exports VRM files. Operations run through Frida and VRoid's own native methods; the server does not simulate mouse or keyboard input or use OCR. It is built with Python (MCP Python SDK) and a JavaScript Frida agent (frida-il2cpp-bridge), and works with stdio MCP clients such as Codex and Claude Code.

> [!IMPORTANT]
> - This is an **unofficial, experimental local tool**.
> - It is not affiliated with or endorsed by pixiv Inc., the developer of VRoid Studio.
> - By default the server launches only a designated physical copy of VRoid with a separate profile. Copy isolation and in-process write guards are not an operating-system sandbox.
> - **attach_open_vroid** connects to a VRoid you opened yourself. Edits then change your real model.

## What it does

- **Sliders**: face, body and clothing sliders, and height to a centimeter target
- **Hair**: hair presets, hair group and strand parameters, procedural hair groups and hair bones
- **Parameters**: accessories, colors, expressions and photo-preview settings
- **Parts**: list the parts of a model, replace one part, save worn parts as custom items
- **Review**: native screenshots and multi-view before/after review
- **Undo, save and export**: native Undo/Redo, save-as to a new .vroid file, VRM 0.x / 1.0 export
- **Your own VRoid**: attach to a VRoid Studio you opened yourself

## Requirements

- Windows x64
- SHA-256-checked VRoid Studio 2.14.0 (Unity 6000.0.62f1), not included in this repository; other builds are refused
- Python 3.10, Frida 17.16.0, MCP Python SDK 1.30.0
- Node.js and npm (for frida-il2cpp-bridge 0.14.0), and Git

Details: [Installation](docs/installation.md).

## Quick start

PowerShell example; replace paths with your own:

~~~powershell
git clone https://github.com/Karylcode/VRoid-MCP.git C:\VRoid-MCP
Set-Location C:\VRoid-MCP
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
& .\.venv\Scripts\python.exe .\prepare_lab.py --source 'D:\SteamLibrary\steamapps\common\VRoid Studio' --lab 'C:\VRoid-MCP-lab'
~~~

Add the server to a stdio MCP client. Adapt this generic JSON to your client's format:

~~~json
{
  "mcpServers": {
    "vroid": {
      "command": "C:\\VRoid-MCP\\.venv\\Scripts\\python.exe",
      "args": ["C:\\VRoid-MCP\\launch.py", "--lab", "C:\\VRoid-MCP-lab"],
      "env": {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
~~~

Then ask your AI client to:

1. Call **list_face_params** and pass its model_token as expected_model when editing.
2. Edit with **set_face_params**, **set_body_params**, **set_parameters** or the preset tools.
3. Check the result with **capture_review**, then **save_as** a new .vroid file.

Next: [Usage](docs/usage.md).

## Troubleshooting

- **The first call is slow or times out**: the first tool call starts VRoid. If your client allows it, set a longer first-call timeout, such as 120 seconds.
- **"Another MCP process already owns this lab"**: only one MCP server can own a lab at a time. Create separate labs for Codex and Claude Code.
- **PermissionError when attaching**: VRoid runs as administrator, so the MCP client must run as administrator too.
- **"VRoid main thread did not respond"**: a VRoid you attached to pauses its main loop while unfocused. Click the VRoid window once and call again.

More: [Troubleshooting](docs/troubleshooting.md).

## Documentation

- [Documentation index](docs/README.md): all pages, and where to start
- [Installation](docs/installation.md): compatibility, SHA-256 check, venv setup, preparing a lab, MCP connection, command-line options
- [Usage](docs/usage.md): full list of what you can edit, editing workflow, colors example, hair, accessories, photo preview, height
- [Working with your own VRoid](docs/own-vroid.md): attach_open_vroid, start-screen models, detaching, administrator rights
- [Parts, custom items and VRM export](docs/parts-and-export.md): list_parts, replace_part, save_custom_items, rebuilding older characters, export_vrm
- [Visual review](docs/visual-review.md): screenshot views, capture_review, before/after comparison and its limits
- [Tool reference](docs/tools.md): all 42 tools with parameters and defaults, parameter domains and value formats
- [Behavior and limitations](docs/limitations.md): batches, timeouts, isolation, out-of-scope features, validation status
- [Troubleshooting](docs/troubleshooting.md): error messages and what to do
- [Development and tests](docs/development.md): unit tests, live acceptance scripts, validation history, source layout
- [Changelog](CHANGELOG.md): release notes (current version 0.4.0)

## License

MIT. See [LICENSE](LICENSE).
- VRoid Studio is not included and is covered by its own terms.
