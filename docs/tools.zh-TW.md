# 工具參考

[English](tools.md) | **繁體中文** · [文件索引](README.zh-TW.md)

伺服器提供 42 個工具。參數寫成「名稱=預設值」；沒有預設值的參數是必填。

- 會修改模型的工具要帶 expected_model，也就是 list_face_params 回傳的 model_token（get_status 與多數列舉工具也會回傳）。列出參數後模型若已改變，呼叫會被拒絕並回報 STALE_MODEL；請重新列出並改用新 token。
- 拍攝預覽開著時，編輯工具會被拒絕並回報 RETURN_TO_EDIT_MODE_FIRST。例外是 domain="photo" 的 set_parameters。
- 每次原生呼叫上限 30 秒。請看[行為與限制](limitations.zh-TW.md)。

## 工作階段與自己開的 VRoid

| 工具 | 參數 | 說明 |
|---|---|---|
| get_status | — | 回報狀態旗標，不是進度：mode（copy 或 attached）、connected、model_ready、model_token、updating、presets_loading、command_busy、photo_active、background、focused、writes_blocked。斷線後會回報原因與復原方式。 |
| attach_open_vroid | pid=None, discard_copy_unsaved=False | 所有工具改為操作你自己開啟的 VRoid。請看[接上自己開的 VRoid](own-vroid.zh-TW.md)。 |
| detach_open_vroid | — | 停止控制你的 VRoid，VRoid 繼續開著。下一次工具呼叫會啟動 MCP 副本。 |
| list_start_models | — | VRoid 開始畫面上的模型卡：recent、sample、old。 |
| open_start_model | name, group=None | group：recent、sample 或 old。只在還沒開模型時開啟卡片，最多等 90 秒。主要用於你自己的 VRoid：MCP 副本一定已經開著模型。 |
| restart_session | discard_unsaved=False | 重建 MCP 副本並丟棄未保存修改；必須帶 discard_unsaved=true。新 model_token 會使舊 ID 失效。接上狀態下只會離開你的 VRoid。 |

## 歷史

| 工具 | 參數 | 說明 |
|---|---|---|
| undo | expected_model, steps=1 | steps 1–32。適用所有範圍的原生歷史。回傳臉部參數；其他範圍請重新列出。 |
| redo | expected_model, steps=1 | steps 1–32。同 undo。 |

## 滑桿與身高

| 工具 | 參數 | 說明 |
|---|---|---|
| list_face_params | — | UI 臉部滑桿：在地化標籤、範圍、目前數值、別名與 model_token。 |
| set_face_params | expected_model, changes, allow_out_of_ui_range=False | changes：1–64 筆 {id, value}。先驗證全部數值；重複的別名會被拒絕。 |
| list_body_params | — | 身體比例、身高與四肢滑桿。 |
| set_body_params | expected_model, changes, allow_out_of_ui_range=False | 1–64 筆修改，走原生歷史。 |
| list_clothing_params | — | 目前穿著衣物的形狀滑桿。換衣服後 ID 會改變。 |
| set_clothing_params | expected_model, changes | 1–64 筆修改，請用最新的 list_clothing_params 結果。 |
| get_height | — | 原生身高公分數（UI 快取值）、標籤與 live_centimeters。 |
| set_height | expected_model, centimeters, tolerance_cm=0.05 | centimeters 20–400；tolerance_cm 0.01–0.5。請看[使用方式](usage.zh-TW.md#身高)。 |

allow_out_of_ui_range：請看[使用方式](usage.zh-TW.md#超出-ui-範圍的數值)。

## 型別化參數

| 工具 | 參數 | 說明 |
|---|---|---|
| list_parameters | domain, scope=None, category=None, offset=0, limit=200 | limit 1–500。列出型別化原生控制，含數值、範圍、單位或選項。請讀完每個 next_offset 頁面。 |
| set_parameters | expected_model, domain, changes, scope=None, category=None | 1–64 筆 {id, value}，請用最新的 list_parameters 結果。寫入前先驗證全部數值。 |

### 參數領域

| domain | scope／category | 內容 |
|---|---|---|
| face、body | — | 與 list_face_params、list_body_params 相同的滑桿 |
| clothing | — | 衣物形狀滑桿；每件衣物的骨骼選擇，以及可用時的部件原點位置 |
| colors | — | 原生顏色控制，RGBA 0–1（sRGB），含 colors/Hair/All |
| expressions | scope（可省略）：表情 ID | 表情定義的權重 |
| general | — | 視線範圍、描邊寬度、邊緣光、陰影、搖晃幅度與誤差修正 |
| hair | 必填 category 與 scope：list_hair_nodes 的節點 ID | 名稱、顯示、可編輯、髮群顏色、導向位移／旋轉／縮放、原生髮型屬性（數值、選項、曲線範本與曲線、覆寫旗標） |
| hair_bones | category（預設 HairFront）；scope（可省略）：骨骼分組 ID | 標示 persistent=false 的生成設定：數量（1–100）與分組門檻（0–1）；每組的 BoneCount（1–20）、SpringRootRate、Stiffness、Gravity、ColliderRadius（0–1）與名稱 |
| accessories | 必填 scope：list_accessories 的實例 ID | 顯示、可編輯、本地縮放／位置／旋轉、骨骼選擇、形狀參數、顏色 |
| photo | 必須在拍攝模式 | 只屬於當次工作階段：姿勢、動畫、姿勢控制、手勢、燈光、風、後製效果、視線、眨眼、鏡頭視角與正交設定 |

### 數值格式

- 數字：float、int，或選項中的 enum 索引
- bool：true 或 false
- 顏色：[r, g, b, a]，每個 0–1
- 向量：[x, y, z]（位置單位為公尺）；縮放各分量必須大於 0、最多 100
- 四元數：[x, y, z, w]，須正規化
- 曲線：2–64 個控制點 [[x, y], ...]，每個值在 -10 到 10 之間
- 字串：最多 128 個字元

## 預設與部件

| 工具 | 參數 | 說明 |
|---|---|---|
| list_presets | area, category=None, offset=0, limit=100 | area：face、body、hair 或 clothing。limit 1–200。列出所有分類中已擁有的預設，以及衣櫃中的自訂物件（custom=true）。 |
| apply_preset | expected_model, area, preset_id | 套用已擁有的預設或衣櫃自訂物件。結構改變後請重新列舉參數。 |
| list_hair_presets | category=None, offset=0, limit=100 | limit 1–200。已擁有的髮型與髮片。標籤是分類／資源代碼。 |
| apply_hair_preset | expected_model, preset_id | 可用原生 Undo。 |
| list_clothing_presets | category=None, offset=0, limit=100 | limit 1–200。套裝、上衣、下著、鞋子與其他服裝分類。 |
| apply_clothing_preset | expected_model, preset_id | 可能替換衝突的衣物；之後請重新列出衣物滑桿。 |
| list_parts | — | 部件（transferable group）：id、type、resource_name、original_resource_name、custom 與 updated 旗標。 |
| replace_part | expected_model, part_id | `*.transferablegroup` 格式的 ID。這個 VRoid 資源庫沒有的 ID 會被拒絕。請看[部件](parts-and-export.zh-TW.md)。 |
| save_custom_items | expected_model, types=None | 把可存的穿戴部件存成自訂物件。接上時寫進你真正的衣櫃。 |

## 髮型結構與髮骨

| 工具 | 參數 | 說明 |
|---|---|---|
| list_hair_nodes | category="HairFront" | HairFront、HairBack、AllHair、HairTied、HairSideburns、HairAhoge 或 HairHanege 中的髮群與髮束。以 id 作為 domain="hair" 的 scope。 |
| edit_hair_structure | expected_model, category, action, node_id=None | action：add_procedural，或 remove 並帶 node_id。可用原生 Undo。不支援手繪髮束。 |
| list_hair_bone_groups | category="HairFront" | 頭髮物理分組。參數在 domain="hair_bones"。 |
| generate_hair_bones | expected_model, category="HairFront" | 依 hair_bones 的生成設定建立骨骼分組。可能取代現有分組；可用原生 Undo。 |

## 配件

| 工具 | 參數 | 說明 |
|---|---|---|
| list_accessory_templates | — | 眼鏡、獸耳、尾巴、帽子等範本。 |
| list_accessories | — | 穿戴中的配件實例 ID，含標籤與顯示狀態。 |
| edit_accessories | expected_model, action, template_id=None, instance_id=None | action：add（帶 template_id）、remove 或 duplicate（帶 instance_id）。之後請重新列出實例與參數。 |

## 表情與拍攝預覽

| 工具 | 參數 | 說明 |
|---|---|---|
| list_expressions | — | 表情 ID。權重在 list_parameters(domain="expressions", scope=id)。 |
| preview_expression | expected_model, expression=None | 依 ID 預覽表情；null 會重設預覽。不改變表情權重。 |
| set_preview_mode | expected_model, mode | mode：photo 或 edit。編輯或存檔前請回到 edit。 |
| set_photo_camera | expected_model, position, target | [x, y, z]，單位公尺。需在拍攝模式。之後用 screenshot(view="photo")。 |

## 圖像

| 工具 | 參數 | 說明 |
|---|---|---|
| screenshot | expected_model, view="front", size=512 | size 256–2048。一張 PNG。請看[圖像檢查](visual-review.zh-TW.md)。 |
| capture_review | expected_model, label="", views=None, size=1024, baseline_id=None | 1–6 個不重複的模型視角（預設 front、three_quarter、full_front、full_back）。不接受 photo；必須在編輯模式。label 最多 80 個字元。 |

## 存檔與匯出

| 工具 | 參數 | 說明 |
|---|---|---|
| save_as | expected_model, filename | 在 lab/saves/ 另存新 .vroid；拒絕覆蓋現有檔案；接上時拒絕。 |
| export_vrm | expected_model, filename, version=1 | 在 lab/exports/ 輸出 .vrm；1 = VRM 1.0，0 = VRM 0.x；拒絕覆蓋現有檔案。 |
