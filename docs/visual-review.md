**English** | [繁體中文](visual-review.zh-TW.md) · [Documentation index](README.md)

# Visual review

Both tools render native PNG images into an offscreen texture, so the image size does not depend on the VRoid window. Before capturing they clear editor selections and guides; they do not edit or save the character.

## screenshot

screenshot returns one PNG. size defaults to 512 and accepts 256–2048 pixels:

| Framing | view |
|---|---|
| Head | front, side, back, three_quarter |
| Full body | full_front, full_side, full_back, full_three_quarter |
| Photo preview | photo |

view defaults to front. photo captures the active photo preview and requires set_preview_mode(mode="photo").

## capture_review

capture_review defaults to four 1024-pixel images: front, three_quarter, full_front and full_back. You can request one to six distinct model views:

~~~json
{
  "expected_model": "<model_token>",
  "label": "Before editing",
  "views": ["front", "three_quarter", "full_front", "full_back"],
  "size": 1024
}
~~~

- photo is not accepted: review uses reproducible model views. Use screenshot for the photo preview.
- It requires edit mode. Return with set_preview_mode(mode="edit") first.
- label is optional, up to 80 characters.

The tool returns images, a capture_id, height readings and a visual checklist. PNGs and parameter snapshots are saved under `lab/reviews/<capture_id>/`.

After editing, pass the previous capture_id as baseline_id with the same views and size to obtain before/after images and face/body/clothing/color parameter differences. Baseline images are checked against their saved hashes and refused if modified. Reviews with different model tokens are explicitly identified.

The checklist asks you to look at eye and eyebrow balance, bangs covering the eyes, hair/scalp gaps, hair/clothing intersections, head/body and limb proportions, and the front/side/back silhouette.

## Limits

This provides evidence for visual inspection, **not an automated beauty score or collision test**. Hair geometry changes require image inspection, and hair physics may vary between frames. Capturing images does not save the character.
