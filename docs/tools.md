**English** | [繁體中文](tools.zh-TW.md) · [Documentation index](README.md)

# Tool reference

The server provides 42 tools. Parameters are listed as name=default; parameters without a default are required.

- Tools that change the model take expected_model: the model_token from list_face_params (get_status and most list tools return it too). If the model changed since you listed it, the call is refused with STALE_MODEL; list again and use the new token. An empty expected_model is refused with EXPECTED_MODEL_REQUIRED. Both checks run before anything is changed.
- While the photo preview is active, editing tools are refused with RETURN_TO_EDIT_MODE_FIRST. set_parameters with domain="photo" is the exception.
- Each native call has a 30-second limit. See [Behavior and limitations](limitations.md).

## Session and your own VRoid

| Tool | Parameters | Notes |
|---|---|---|
| get_status | — | Reports state flags, not progress: mode (copy or attached), connected, model_ready, model_token, updating, presets_loading, command_busy, photo_active, background, focused, writes_blocked. After a disconnect it returns the reason and the recovery step. |
| attach_open_vroid | pid=None, discard_copy_unsaved=False | Switches every tool to a VRoid you opened yourself. See [Working with your own VRoid](own-vroid.md). |
| detach_open_vroid | — | Stops controlling your VRoid; it keeps running. The next tool call starts the MCP copy. |
| list_start_models | — | Model cards on VRoid's start screen: recent, sample and old. |
| open_start_model | name, group=None | group: recent, sample or old. Opens a card only while no model is open and waits up to 90 s. Mainly for your own VRoid: the MCP copy always has a model open. |
| restart_session | discard_unsaved=False | Recreates the MCP copy and discards its unsaved changes; requires discard_unsaved=true. The new model_token invalidates old IDs. While attached, it only detaches from your VRoid. |

## History

| Tool | Parameters | Notes |
|---|---|---|
| undo | expected_model, steps=1 | steps 1–32. Native history for any area. Returns face parameters; relist other areas. |
| redo | expected_model, steps=1 | steps 1–32. Same as undo. |

## Sliders and height

| Tool | Parameters | Notes |
|---|---|---|
| list_face_params | — | UI face sliders: localized labels, ranges, current values, aliases and model_token. |
| set_face_params | expected_model, changes, allow_out_of_ui_range=False | changes: 1–64 items of {id, value}. All values are validated first; duplicate aliases are rejected. |
| list_body_params | — | Body proportions, height and limb sliders. |
| set_body_params | expected_model, changes, allow_out_of_ui_range=False | 1–64 changes through native history. |
| list_clothing_params | — | Shape sliders on currently worn clothes. IDs change when garments change. |
| set_clothing_params | expected_model, changes | 1–64 changes from a fresh list_clothing_params result. |
| get_height | — | Native height in centimeters (cached UI value), label and live_centimeters. |
| set_height | expected_model, centimeters, tolerance_cm=0.05 | centimeters 20–400; tolerance_cm 0.01–0.5. See [Usage](usage.md#height). |

allow_out_of_ui_range: see [Usage](usage.md#values-outside-the-ui-range).

## Typed parameters

| Tool | Parameters | Notes |
|---|---|---|
| list_parameters | domain, scope=None, category=None, offset=0, limit=200 | limit 1–500. Typed native controls with values, ranges, units or options. Read every next_offset page. |
| set_parameters | expected_model, domain, changes, scope=None, category=None | 1–64 changes of {id, value} from a fresh list_parameters result. All values validate before writes. |

### Domains

| domain | scope / category | Contents |
|---|---|---|
| face, body | — | The same sliders as list_face_params and list_body_params |
| clothing | — | Garment shape sliders; per garment a bone selector and part-origin position when available |
| colors | — | Native color controls, RGBA 0–1 (sRGB), including colors/Hair/All |
| expressions | scope (optional): expression ID | Expression definition weights |
| general | — | Gaze limits, outline width, rim light, shading, spring bone amplitude and error reduction |
| hair | category and scope required: node ID from list_hair_nodes | Name, visibility, editability, group color, guide position/rotation/scale, native hair properties (numbers, options, curve templates and curves, override flags) |
| hair_bones | category (default HairFront); scope (optional): bone group ID | Generation settings listed with persistent=false: count (1–100) and grouping threshold (0–1); per group BoneCount (1–20), SpringRootRate, Stiffness, Gravity, ColliderRadius (0–1) and name |
| accessories | scope required: instance ID from list_accessories | Visibility, editability, local scale/position/rotation, bone selector, shape parameters, colors |
| photo | photo mode required | Session-only: poses, animations, pose controls, hand poses, lighting, wind, post effects, gaze, blinking, camera field of view and orthographic settings |

### Value formats

- Numbers: float, int, or enum index from the listed options
- bool: true or false
- Color: [r, g, b, a], each 0–1
- Vector: [x, y, z] (meters for positions); scale components must be greater than 0 and at most 100
- Quaternion: [x, y, z, w], normalized
- Curve: 2–64 control points [[x, y], ...], each value within -10 to 10
- String: up to 128 characters

## Presets and parts

| Tool | Parameters | Notes |
|---|---|---|
| list_presets | area, category=None, offset=0, limit=100 | area: face, body, hair or clothing. limit 1–200. Owned presets across every category, plus closet custom items (custom=true). |
| apply_preset | expected_model, area, preset_id | Applies an owned preset or closet custom item. Relist parameters after structural changes. |
| list_hair_presets | category=None, offset=0, limit=100 | limit 1–200. Owned hairstyles and hair parts. Labels are category/resource codes. |
| apply_hair_preset | expected_model, preset_id | Native Undo supported. |
| list_clothing_presets | category=None, offset=0, limit=100 | limit 1–200. Outfits, tops, bottoms, shoes and other clothing categories. |
| apply_clothing_preset | expected_model, preset_id | Can replace conflicting garments; relist clothing sliders afterwards. |
| list_parts | — | Parts (transferable groups): id, type, resource_name, original_resource_name, custom and updated flags. |
| replace_part | expected_model, part_id | A built-in `*.transferablegroup` ID. Refuses IDs missing from this VRoid's asset catalog, closet custom items included (use apply_preset for those). See [Parts](parts-and-export.md). |
| save_custom_items | expected_model, types=None | Saves savable worn parts as custom items. Writes to your real closet when attached. |

## Hair structure and hair bones

| Tool | Parameters | Notes |
|---|---|---|
| list_hair_nodes | category="HairFront" | Groups and strands in HairFront, HairBack, AllHair, HairTied, HairSideburns, HairAhoge or HairHanege. Use an id as scope for domain="hair". |
| edit_hair_structure | expected_model, category, action, node_id=None | action: add_procedural, or remove with node_id. Native Undo supported. No manual strand drawing. |
| list_hair_bone_groups | category="HairFront" | Hair physics groups. Their parameters are in domain="hair_bones". |
| generate_hair_bones | expected_model, category="HairFront" | Generates bone groups from the hair_bones generation settings. Existing grouping can be replaced; native Undo supported. |

## Accessories

| Tool | Parameters | Notes |
|---|---|---|
| list_accessory_templates | — | Templates across glasses, animal ears, tails and hats. |
| list_accessories | — | Worn accessory instance IDs with label and visibility. |
| edit_accessories | expected_model, action, template_id=None, instance_id=None | action: add (template_id), remove or duplicate (instance_id). Relist instances and parameters afterwards. |

## Expressions and photo preview

| Tool | Parameters | Notes |
|---|---|---|
| list_expressions | — | Expression IDs. Weights are in list_parameters(domain="expressions", scope=id). |
| preview_expression | expected_model, expression=None | Previews an expression by ID; null resets the preview. Does not change expression weights. |
| set_preview_mode | expected_model, mode | mode: photo or edit. Return to edit before editing or saving. |
| set_photo_camera | expected_model, position, target | [x, y, z] in meters. Requires photo mode. Then screenshot(view="photo"). |

## Images

| Tool | Parameters | Notes |
|---|---|---|
| screenshot | expected_model, view="front", size=512 | size 256–2048. One PNG. See [Visual review](visual-review.md). |
| capture_review | expected_model, label="", views=None, size=1024, baseline_id=None | 1–6 distinct model views (default front, three_quarter, full_front, full_back). Rejects photo; requires edit mode. label up to 80 characters. |

## Saving and export

| Tool | Parameters | Notes |
|---|---|---|
| save_as | expected_model, filename | New .vroid under lab/saves/; refuses existing files; refused while attached. |
| export_vrm | expected_model, filename, version=1 | .vrm under lab/exports/; 1 = VRM 1.0, 0 = VRM 0.x; refuses existing files. |
