**English** | [繁體中文](CHANGELOG.zh-TW.md) · [README](README.md)

# Changelog

## Unreleased

- Documentation: the README is now a short entry point; details moved to [docs/](docs/README.md).
- License: the project is now under the [MIT License](LICENSE).
- Fixed: every write tool refuses an empty expected_model with EXPECTED_MODEL_REQUIRED before any native call, and checks the token against the open model first. Before, export_vrm(expected_model="") exported without a model check and save_custom_items with an empty token saved first and failed afterwards. screenshot also refuses an empty token now.
- Fixed: the replace_part description said closet custom items work. It takes built-in part IDs only; apply closet custom items with list_presets and apply_preset.

## 0.4.0 — 2026-10-23

### Added

- New tools: attach_open_vroid, detach_open_vroid, list_start_models, open_start_model, list_parts, replace_part, save_custom_items and export_vrm.
- set_face_params and set_body_params accept allow_out_of_ui_range.

### Fixed

- Isolation fix: in 0.3.2 the copy could still write file_access_history.json, history_temp and vroid_file_temporary into your real `LocalLow\pixiv\VRoid Studio` profile. Unity resolves its data path through windows.storage.dll, some file calls go straight to kernelbase.dll, and Frida skips Interceptor listeners during native calls made from the agent. Folder lookups are now hooked in every exporting module, file and registry hooks sit on kernelbase.dll with CreateFile2, CopyFile*, MoveFileWithProgressW, SetFileAttributesW and CreateDirectoryExW added, and agent/traps.js makes every NativeFunction use traps:'all'.
- Accessory IsVisible now uses VRoid's native visibility history command. Before, it only changed the list icon and the mesh stayed visible.

### Changed

- capture_review no longer sends every PNG a second time as base64 structured content.

Earlier versions are not recorded in this file.
