[English](usage.md) | **繁體中文** · [文件索引](README.zh-TW.md)

# 使用方式

## 可以編輯的內容

| 範圍 | 支援內容 |
|---|---|
| 臉部與體型 | 眼睛、眉毛、鼻子、嘴巴、臉型、頭身比例、肩頸、胸腰及四肢滑桿 |
| 身高 | 指定公分目標，透過全身大小參數校正並回報誤差 |
| 髮型 | 套用已擁有的髮型／髮片預設；髮群與髮束參數、導向位移／旋轉／縮放、寬度、粗細、扭轉、截面、形狀曲線；新增生成式髮群與移除髮群／髮束 |
| 髮骨 | 骨骼分組、骨骼數、硬度、重力、碰撞半徑與自動生成設定 |
| 服裝與配件 | 套用已擁有預設與衣櫃中的自訂物件、調整衣物形狀；新增／複製／移除配件及其可用參數 |
| 部件 | 列出模型由哪些部件組成、依 ID 單獨替換一個部件、把穿戴中的部件存成自訂物件 |
| 色彩 | 眼睛、頭髮、眉睫、膚色等 VRoid 原生顏色控制 |
| 表情與拍攝 | 表情定義與預覽、姿勢、手勢、燈光、風、鏡頭及可用拍攝參數 |
| 圖像檢查 | 256–2048 像素原生截圖、多角度檢查、前後圖片及參數比較 |
| 歷史、存檔與匯出 | 原生 Undo／Redo，另存新的 .vroid 檔案，透過 VRoid 自己的匯出器輸出 VRM 0.x／1.0 |
| 自己開的 VRoid | 接上使用者開啟的 VRoid Studio、開啟開始畫面的模型卡、離開時不關閉 VRoid |

不包含貼圖繪製、自製材質、手繪髮束或任意程式碼執行。可用參數依角色、部件與模式改變；不是所有內部 API 都已覆蓋。每個工具的確切參數請看[工具參考](tools.zh-TW.md)。

## 使用流程

1. 呼叫 **list_face_params**，取得 model_token；後續修改帶入 expected_model。
2. 先列出相關參數／預設，再使用回傳的 id、範圍與型別。依 next_offset 讀取後續頁面。
3. 修改前以 **capture_review** 留下比較基準。
4. 用 **set_face_params、set_body_params、set_parameters** 或預設工具調整角色。
5. 用 **screenshot／capture_review** 看圖檢查，必要時 Undo。更換髮型、衣服、部件或結構後重新列舉參數。
6. 完成造型後執行 **set_height**，再用 **save_as** 另存，例如 character.vroid。

## 範例：色彩

set_parameters 色彩範例；必須以實際 token 取代占位文字，並先確認參數存在且 editable=true：

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

顏色是 0 到 1 的 RGBA 浮點數。

## 髮型

髮型調整：list_hair_nodes(category="HairTied") → 以節點 id 作為 scope 呼叫 list_parameters(domain="hair", category="HairTied", scope=...) → set_parameters。

- 髮型參數的分類：HairFront、HairBack、AllHair、HairTied、HairSideburns、HairAhoge、HairHanege。
- edit_hair_structure 可新增生成式髮群（action="add_procedural"），或移除髮群／髮束（action="remove" 並帶 node_id）。之後請重新列出節點。
- 髮骨：list_hair_bone_groups(category=...) → list_parameters(domain="hair_bones", category=...) → set_parameters。
- generate_hair_bones 依 hair_bones 領域裡的生成設定建立骨骼分組。它可能取代現有分組；可用原生 Undo 復原。

## 配件

先呼叫 list_accessory_templates，再呼叫 edit_accessories(action="add", template_id=...)。list_accessories 會回傳實例 id，拿它當 scope 呼叫 list_parameters(domain="accessories", scope=...)，再用 set_parameters 修改。edit_accessories 的 action="remove" 或 "duplicate" 要帶 instance_id。新增或移除後，請重新列出實例與參數。

## 拍攝預覽

拍攝流程：set_preview_mode(mode="photo") → list_parameters(domain="photo") → 調整拍攝參數 → screenshot(view="photo")。set_photo_camera 以公尺設定鏡頭位置與注視目標。回到 mode="edit" 後再編輯、capture_review 或存檔。拍攝設定只屬於當次工作階段，不保存到 .vroid。

## 身高

髮型與比例會影響 VRoid 量到的身高，所以請在完成造型後再呼叫 set_height。它調整全身大小、保持相對比例，並檢查 VRoid 的實測身高是否落在 tolerance_cm 內（預設 0.05 公分）。實際能到的範圍依模型而定，可能比 20–400 公分窄。達不到目標時會還原原本的大小，並回報錯誤。

get_height 同時回報 UI 快取 centimeters 與即時測量 live_centimeters，兩者可能略有差異。

## 超出 UI 範圍的數值

set_face_params 與 set_body_params 可加 allow_out_of_ui_range=true，允許超出 UI 範圍最多一個滑桿跨度。只用來照搬別的模型真的存著的值（例如舊版 VRoid 做的樣本），不要拿來自創數值。
