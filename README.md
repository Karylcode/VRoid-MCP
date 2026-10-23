# VRoid Character MCP

**English** | [繁體中文](README.zh-TW.md)

**v0.4.0 · Windows · 42 MCP tools · stdio**

A local MCP server that lets an AI client edit VRoid Studio characters: face, body and clothing sliders, hair, accessories, colors, presets and parts. It checks the result with native screenshots and exports VRM files. Operations run through Frida and VRoid's own native methods; the server does not simulate mouse or keyboard input or use OCR. It is built with Python (MCP Python SDK) and a JavaScript Frida agent (frida-il2cpp-bridge), and works with stdio MCP clients such as Codex and Claude Code.

> [!IMPORTANT]
> - This is an **unofficial, experimental local tool**.
> - It is not affiliated with or endorsed by pixiv Inc., the developer of VRoid Studio.
> - By default the server launches only a designated physical copy of VRoid with a separate profile. Copy isolation and in-process write guards are not an operating-system sandbox.
> - **attach_open_vroid** connects to a VRoid you opened yourself. Edits then change your real model.

## What it can do

- Face, body and clothing sliders, and height to a centimeter target
- Hair presets, hair group and strand parameters, procedural hair groups and hair bones
- Accessories, colors, expressions and photo-preview settings
- List the parts of a model, replace one part, save worn parts as custom items
- Native screenshots and multi-view before/after review
- Native Undo/Redo, save-as to a new .vroid file, VRM 0.x / 1.0 export
- Attach to a VRoid Studio you opened yourself

Full coverage: [Usage](docs/usage.md#what-you-can-edit).

## Requirements

- Windows x64
- SHA-256-checked VRoid Studio 2.14.0 (Unity 6000.0.62f1); other builds are refused
- Python 3.10, Frida 17.16.0, MCP Python SDK 1.30.0
- Node.js and npm (for frida-il2cpp-bridge 0.14.0), and Git

The repository does not include VRoid. See [Installation](docs/installation.md) for the hash and the setup rules.

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

Full workflow and examples: [Usage](docs/usage.md).

## Troubleshooting

- The first tool call starts VRoid. If your client allows it, set a longer first-call timeout, such as 120 seconds.
- Only one MCP server can own a lab at a time. Create separate labs for Codex and Claude Code.
- If VRoid runs as administrator, the MCP client must too; otherwise attaching fails with PermissionError.
- A VRoid you attached to pauses its main loop while unfocused. If it stops responding, click the VRoid window once and call again.

More: [Troubleshooting](docs/troubleshooting.md).

## Documentation

- [Documentation index](docs/README.md)
- [Installation](docs/installation.md)
- [Usage](docs/usage.md)
- [Working with your own VRoid](docs/own-vroid.md)
- [Parts, custom items and VRM export](docs/parts-and-export.md)
- [Visual review](docs/visual-review.md)
- [Tool reference](docs/tools.md)
- [Behavior and limitations](docs/limitations.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development and tests](docs/development.md)
- [Changelog](CHANGELOG.md)
