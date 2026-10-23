# 部件、自訂物件與 VRM 匯出

[English](parts-and-export.md) | **繁體中文** · [文件索引](README.zh-TW.md)

## 部件與自訂物件

- **list_parts**：列出模型由哪些部件（transferable group）組成，含 id、type、resource_name、自訂部件的內建來源 original_resource_name，以及 custom／updated 旗標。
- **replace_part(part_id)**：單獨替換一個內建部件，例如只換臉型而不動同套組的其他部分。part_id 是 `*.transferablegroup` 格式的 ID，例如 list_parts 列出的內建部件 ID。工具會先在這個 VRoid 的資源庫查這個 ID，查不到就拒絕（例如舊版 VRoid 檔案的部件 ID、衣櫃的自訂物件），因為原生載入器遇到它會讓 VRoid 當掉。替換後會確認部件已生效；沒生效時回報 REPLACE_PART_FAILED，原生錯誤記在 VRoid 的 Player.log。可用原生 Undo 復原。之後請重新列舉參數。
- **save_custom_items(types?)**：等同 VRoid「存成自訂物件」，把穿戴中 VRoid 標為可存（自訂或修改過）的部件存起來。types 可限定部件類型，例如 `["Iris", "AllHair"]`。檔案寫入受控 VRoid 的 custom_items：副本寫在 lab profile，接上時寫進使用者真正的衣櫃。
- list_presets 也會列出衣櫃中的自訂物件（custom=true），可用 apply_preset 套用。replace_part 不接受它們。

## 在新版 VRoid 重建舊角色

依 resource_name 對應部件，用 save_custom_items 存下自訂或修改過的部件，再用 apply_preset 套到新模型，單一內建部件用 replace_part 替換，最後搬數值並逐項比對。

## VRM 匯出

**export_vrm(expected_model, filename, version=1)** 走 VRoid 自己的匯出器。version 1 為 VRM 1.0，0 為 VRM 0.x。

- filename 只接受單一 .vrm 檔名。檔案寫到 lab/exports/，同名檔案已存在時會拒絕。會自動進出匯出畫面。
- 名稱、作者、授權取自模型存的 VRM 匯出資訊；模型沒有 VRM 名稱（1.0）或標題（0.x）時拒絕匯出，請先在 VRoid 設定。
- 採 VRoid 預設設定：合併頭髮網格，不縮減材質／網格。合併頭髮網格依匯出畫面目前的設定。
- MCP 副本與 attach_open_vroid 後的使用者 VRoid 都能用。
- 工具最多等 15 分鐘讓匯出完成。VRoid 回報失敗時，工具回傳 VRM_EXPORT_FAILED；請看 Player.log。
- 結果包含檔案路徑、位元組大小與 SHA-256。

## 存檔

**save_as(expected_model, filename)** 只接受單一 .vroid 檔名（不能含路徑分隔符號或 Windows 保留名稱），寫到 lab/saves/，拒絕覆蓋現有檔案。接上自己的 VRoid 時會拒絕。結果包含路徑、位元組大小與 SHA-256。
