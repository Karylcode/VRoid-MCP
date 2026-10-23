# Installation

**English** | [繁體中文](installation.zh-TW.md) · [Documentation index](README.md)

## Compatibility

Validated combination:

- Windows x64
- VRoid Studio 2.14.0, Unity 6000.0.62f1
- Python 3.10, Frida 17.16.0, MCP Python SDK 1.30.0
- frida-il2cpp-bridge 0.14.0, installed through npm

Git, Node.js and npm are required for checkout and dependency installation. pyproject.toml accepts Python 3.10 or later, but only 3.10 has been validated.

Startup checks GameAssembly.dll against this SHA-256 and rejects other binaries, even if their displayed version is identical. prepare_lab.py applies the same check before copying, and attach_open_vroid applies it to the VRoid you opened:

~~~text
793eb5fcff3093f344ee930fbfa0c0796ed7780ac91c45bdb7ce6bd34d62fd3c
~~~

The Frida agent also refuses a Unity version other than 6000.0.62f1.

The repository does not include VRoid binaries, characters, screenshots, test output or private client configuration. Supply your own compatible VRoid installation.

## Install

PowerShell example; replace paths with your own:

~~~powershell
git clone https://github.com/Karylcode/VRoid-MCP.git C:\VRoid-MCP
Set-Location C:\VRoid-MCP
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
~~~

npm ci installs frida-il2cpp-bridge into node_modules inside the repository. The server loads it from there.

## Prepare a lab

~~~powershell
& .\.venv\Scripts\python.exe .\prepare_lab.py --source 'D:\SteamLibrary\steamapps\common\VRoid Studio' --lab 'C:\VRoid-MCP-lab'
~~~

prepare_lab.py copies and verifies the installation without modifying its source:

- The lab directory must **not already exist**.
- Neither directory may contain the other.
- Junctions and symlinks in the source are rejected.
- Every source file is hashed, copied to `<lab>\app\` and checked again. The hashes are written to `<lab>\source-manifest.json`.

Allow enough disk space for a full installation copy. The server later creates `profile\` (the copy's private profile), `runs\` (logs), `saves\`, `exports\` and `reviews\` inside the lab as needed.

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

## Command-line options

| Option | Required | Default | Meaning |
|---|---|---|---|
| --lab | Yes | — | Lab directory containing a physical `app\VRoidStudio.exe` copy |
| --variant | No | F00 | Base character for a new model: F00 or M00. Used only without --model |
| --model | No | — | A .vroid file already inside the lab, opened at startup instead of a new model |

## Optional: console script

`pip install -e .` also registers a `vroid-face-mcp` command in `.venv\Scripts`. Use an editable install (`-e`): the server loads `agent\*.js` and `node_modules` from the repository checkout, and a regular install does not package them. The venv is not on PATH unless it is activated, so give the client the full path:

~~~json
"command": "C:\\VRoid-MCP\\.venv\\Scripts\\vroid-face-mcp.exe",
"args": ["--lab", "C:\\VRoid-MCP-lab"]
~~~

Keep the same env entries as above. The launch.py setup shown earlier does not need `pip install -e .`.
