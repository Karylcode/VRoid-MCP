**English** | [繁體中文](limitations.zh-TW.md) · [Documentation index](README.md)

# Behavior and limitations

## Behavior

- Batches are not transactions. Inputs are validated first, but a native execution error may leave partial edits. Inspect ok, applied and error. A batch may require several Undo steps.
- save_as accepts a single .vroid filename, writes only under lab/saves/ and refuses to overwrite an existing file.
- restart_session(discard_unsaved=true) recreates only the MCP-owned copy and discards unsaved changes. Its new token invalidates the previous model identity.
- Some hair presets expand into parts without retaining the whole-set checkbox. selected=false alone does not establish failure; inspect changed, confirmation and screenshots.
- Height depends on styling and proportions. get_height reports both cached UI centimeters and live_centimeters; they can differ slightly. set_height accepts 20–400 cm, but the reachable range depends on the model and can be narrower.
- Each native call has a 30-second limit. After a timeout the result is uncertain: further calls are refused with PREVIOUS_CALL_UNCERTAIN and get_status shows writes_blocked=true. Do not retry the change. Recover with restart_session(discard_unsaved=true) for the copy, or attach_open_vroid again for your own VRoid.
- Photo settings are session-only and are not stored in the .vroid file.
- The MCP copy always has a model open, so open_start_model is mainly for your own VRoid.

## Copy isolation

By default the server launches only a designated physical copy of VRoid with a separate profile. Copy isolation and in-process write guards are not an operating-system sandbox.

For the copy, the server:

- points USERPROFILE, APPDATA, LOCALAPPDATA, TEMP and TMP into `<lab>\profile\`;
- redirects known-folder lookups and file paths under your real profile into that private profile;
- blocks file writes outside the lab and opening .vroid files outside the lab;
- gives the copy its own registry key instead of VRoid's;
- blocks child processes, because a relaunched VRoid would lose these guards.

It does not block network access or reading other files. None of these guards are loaded when you attach to your own VRoid. For the isolation fix in 0.4.0, see the [Changelog](../CHANGELOG.md).

## Out of scope

Texture painting, custom material authoring, hand-drawn hair strands and arbitrary code execution are outside the current scope. Available parameters vary by model, part and mode; this is not complete coverage of every internal API.

## Validation status

- Only the combination in [Installation](installation.md#compatibility) has been validated.
- F00 is the primary validation target. M00, comprehensive unfocused operation and long-running stability have not received equivalent validation.
- The 0.4.0 features were checked by hand and do not have acceptance scripts yet. See [Development and tests](development.md#validation-history).
