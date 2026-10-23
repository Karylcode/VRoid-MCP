# 更新紀錄

[English](CHANGELOG.md) | **繁體中文** · [README](README.zh-TW.md)

## 尚未發布

- 文件：README 改為簡短入口，細節移到 [docs/](docs/README.zh-TW.md)。
- 授權：本專案改採 [MIT 授權](LICENSE)。
- 修正：所有寫入工具在任何原生呼叫之前，會先拒絕空的 expected_model（回報 EXPECTED_MODEL_REQUIRED），並先比對 token 與目前開著的模型。之前 export_vrm(expected_model="") 不檢查模型就匯出，save_custom_items 帶空 token 會先存檔、事後才報錯。screenshot 現在也會拒絕空 token。
- 修正：replace_part 的說明寫衣櫃自訂物件也能用，其實只接受內建部件 ID；衣櫃自訂物件請用 list_presets 加 apply_preset。

## 0.4.0 — 2026-10-23

### 新增

- 新工具：attach_open_vroid、detach_open_vroid、list_start_models、open_start_model、list_parts、replace_part、save_custom_items、export_vrm。
- set_face_params、set_body_params 新增 allow_out_of_ui_range。

### 修正

- 隔離修正：0.3.2 的副本仍可能把 file_access_history.json、history_temp、vroid_file_temporary 寫進使用者真正的 `LocalLow\pixiv\VRoid Studio`。原因是 Unity 透過 windows.storage.dll 取得資料路徑、部分檔案呼叫直接進 kernelbase.dll，而且 agent 發出的原生呼叫期間 Frida 不會觸發 Interceptor。現在所有匯出資料夾查詢的模組都會被 hook；檔案與登錄檔 hook 改掛在 kernelbase.dll，並補上 CreateFile2、CopyFile*、MoveFileWithProgressW、SetFileAttributesW、CreateDirectoryExW；agent/traps.js 讓所有 NativeFunction 使用 traps:'all'。
- 配件 IsVisible 改用 VRoid 原生的顯示歷史命令。原本只改清單圖示，模型照樣顯示。

### 變更

- capture_review 不再把每張 PNG 以 base64 結構化內容重複送一次。

更早的版本沒有記錄在這個檔案。
