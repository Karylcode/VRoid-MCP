# Development and tests

**English** | [繁體中文](development.zh-TW.md) · [Documentation index](README.md)

## Unit tests

Unit tests do not start VRoid:

~~~powershell
& .\.venv\Scripts\python.exe -m pip install pytest
& .\.venv\Scripts\python.exe -m pytest -q
~~~

pytest collects only `tests/test_*.py`: 27 test cases for the save/export filename policy and the capture/review input checks. They import vroid_mcp.runtime, so install requirements.txt first.

## Live acceptance scripts

Live MCP/VRoid tests are in tests/. They are standalone scripts that pytest does not collect. Prepare a separate lab and run only one test against it at a time. For example:

~~~powershell
& .\.venv\Scripts\python.exe .\tests\stdio_acceptance.py C:\VRoid-MCP-test-lab .\test-evidence\stdio
~~~

| Script | Arguments | Checks |
|---|---|---|
| stdio_acceptance.py | lab, output | Real MCP protocol over stdio |
| live_acceptance.py | lab, output | Native bridge on a newly spawned copy; expects the F00 face catalog |
| extension_acceptance.py | lab, output | Body, hair and clothing controls, Undo, rendering, save and reload |
| parameter_acceptance.py | lab, output | Typed parameters through stdio, including save and reopen |
| parameter_extras.py | lab, model, output | Structural operations, photo-mode switching and clean capture |
| recovery_acceptance.py | repository, lab, output | Fast tool discovery, native preset completion, recovery after the copy is killed |
| reopen_acceptance.py | lab, saved .vroid, output | Persistence in a fresh process and --model startup |
| review_acceptance.py | repository, lab, output, model | capture_review, before/after evidence and guards |

repository is the folder that contains launch.py. model and saved .vroid files must be inside the lab.

## Validation history

- Local validation for 0.3.2 included 26 unit tests and real MCP tests covering multi-view images, resolutions, before/after comparison, Undo, invalid requests and compatibility with the original screenshot interface.
- The 0.4.0 features were checked by hand against VRoid Studio 2.14.0: saving from the copy left the real profile unchanged, repeated exports of the same .vroid were byte-identical, and an AvatarSample_M rebuilt through parts matched the original in all 38 parts and every listed value.
- These 0.4.0 features do not have acceptance scripts in tests/ yet: attach_open_vroid, detach_open_vroid, list_start_models, open_start_model, list_parts, replace_part, save_custom_items and export_vrm.
- Evidence and character fixtures are kept locally rather than committed.

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
