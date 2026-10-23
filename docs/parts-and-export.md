**English** | [繁體中文](parts-and-export.zh-TW.md) · [Documentation index](README.md)

# Parts, custom items and VRM export

## Parts and custom items

- **list_parts** lists every part (transferable group) the model is built from: id, type, resource_name, original_resource_name for custom parts, and custom/updated flags.
- **replace_part(part_id)** replaces exactly one built-in part, for example a single face shape without the rest of its face set. part_id is a `*.transferablegroup` ID, such as a built-in part ID from list_parts. The tool first looks the ID up in this VRoid's asset catalog and refuses IDs that are missing there, such as part IDs from files made with older VRoid versions and closet custom items, because VRoid's native loader crashes on them. Afterwards it confirms that the part is active; if not, it reports REPLACE_PART_FAILED and VRoid logs the native error in Player.log. Native history supports Undo. Relist parameters afterwards.
- **save_custom_items(types?)** saves worn parts that VRoid marks savable (custom or modified) as custom items, like VRoid's own "save as custom item". types limits it to part types such as `["Iris", "AllHair"]`. Files go to the custom_items folder of the controlled VRoid: the lab profile for the copy, your real closet when attached.
- list_presets also lists closet custom items with custom=true; apply them with apply_preset. replace_part does not accept them.

## Rebuilding an older character

To rebuild an older character on the current VRoid version, match its parts by resource_name, save its custom or modified parts with save_custom_items, apply them on the new model with apply_preset, use replace_part for single built-in parts, then copy the values and compare.

## VRM export

**export_vrm(expected_model, filename, version=1)** exports through VRoid's own exporter. version 1 is VRM 1.0 and 0 is VRM 0.x.

- filename is a single .vrm filename. Files are written under lab/exports/, and an existing file with the same name is refused. The export screen is entered and left automatically.
- Name, authors and license come from the VRM export meta stored in the model. Export is refused if the model has no VRM name (1.0) or title (0.x); set it in VRoid first.
- VRoid's default settings are used: hair meshes combined, no material or mesh reduction. Hair mesh combination follows the export screen's current setting.
- Works on the MCP copy and on your own VRoid after attach_open_vroid.
- The tool waits up to 15 minutes for the export to finish. If VRoid reports a failure, the tool returns VRM_EXPORT_FAILED; see Player.log.
- The result includes the file path, size in bytes and SHA-256.

## Saving

**save_as(expected_model, filename)** accepts a single .vroid filename (no path separators or reserved Windows names), writes only under lab/saves/ and refuses to overwrite an existing file. It is refused while attached to your own VRoid. The result includes the path, size in bytes and SHA-256.
