**English** | [繁體中文](usage.zh-TW.md) · [Documentation index](README.md)

# Usage

## What you can edit

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

Texture painting, custom material authoring, hand-drawn hair strands and arbitrary code execution are outside the current scope. Available parameters vary by model, part and mode; this is not complete coverage of every internal API. Exact parameters for every tool: [Tool reference](tools.md).

## Editing workflow

1. Call **list_face_params** to obtain model_token. Pass it as expected_model when editing.
2. List parameters or presets before applying changes. Use returned IDs, types, limits and options; follow next_offset pagination.
3. Capture a baseline with **capture_review**.
4. Edit through **set_face_params, set_body_params, set_parameters** or preset tools.
5. Inspect **screenshot/capture_review** images and use Undo when needed. Relist parameters after changing hair, clothing, parts or structure.
6. Apply **set_height** after styling, then **save_as** with a new filename such as character.vroid.

## Example: colors

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

Colors are RGBA floats from 0 to 1.

## Hair

For hair, call list_hair_nodes(category="HairTied"), use a returned node ID as scope in list_parameters(domain="hair", category="HairTied", scope=...), then call set_parameters.

- Hair parameter categories: HairFront, HairBack, AllHair, HairTied, HairSideburns, HairAhoge and HairHanege.
- edit_hair_structure adds a procedural group (action="add_procedural") or removes a group or strand (action="remove" with node_id). Relist nodes afterwards.
- Hair bones: list_hair_bone_groups(category=...), then list_parameters(domain="hair_bones", category=...) and set_parameters.
- generate_hair_bones builds bone groups from the generation settings in the hair_bones domain. It can replace the existing grouping; native Undo is supported.

## Accessories

Call list_accessory_templates, then edit_accessories(action="add", template_id=...). list_accessories returns instance IDs. Use one as scope in list_parameters(domain="accessories", scope=...), then call set_parameters. edit_accessories with action="remove" or "duplicate" takes instance_id. Relist instances and parameters after adding or removing.

## Photo preview

For photo preview, use set_preview_mode(mode="photo"), list_parameters(domain="photo"), adjust settings, then screenshot(view="photo"). set_photo_camera sets the camera position and look-at target in meters. Return to mode="edit" before editing, capture_review or saving. Photo settings are session-only and are not stored in the .vroid file.

## Height

Hairstyle and proportions can affect VRoid's measured height, so call set_height after styling. It adjusts whole-body size, keeps relative proportions and checks VRoid's measured height against tolerance_cm (default 0.05 cm). The native reachable range depends on the model and can be narrower than 20–400 cm. If the target cannot be reached, the original scale is restored and an error is returned.

get_height reports both cached UI centimeters and live_centimeters; they can differ slightly.

## Values outside the UI range

set_face_params and set_body_params accept allow_out_of_ui_range=true, which permits values up to one slider span beyond the UI limits. Use it only to copy values another model really holds, such as samples made with older VRoid versions, not to invent new ones.
