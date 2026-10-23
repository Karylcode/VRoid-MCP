[English](troubleshooting.md) | **繁體中文** · [文件索引](README.zh-TW.md)

# 疑難排解

## 常見情況

- **第一次呼叫很慢或逾時。** 第一次工具呼叫才會啟動 VRoid。若用戶端可調 timeout，請給長一點，例如 120 秒。
- **「Another MCP process already owns this lab」。** 每個 lab 同時只能由一個伺服器持有，接上自己的 VRoid 時也一樣。請關掉另一個伺服器，或另外製作 lab，例如 Codex、Claude Code 各用一個。
- **接上時出現 PermissionError。** VRoid 以系統管理員執行（例如 Steam 以管理員開啟）。請也以管理員執行 MCP 用戶端，或改用非管理員方式啟動 Steam／VRoid。
- **「VRoid main thread did not respond」。** VRoid 失焦時 Unity 會暫停主迴圈。點一下 VRoid 視窗再呼叫一次。
- **更新後看不到新工具。** 請重新載入 MCP。先另存角色，因為伺服器結束會關閉自己啟動的副本。

## 錯誤訊息

| 訊息 | 處理方式 |
|---|---|
| Untested VRoid binary／UNTESTED_UNITY_VERSION | VRoid 版本與驗證過的 SHA-256 或 Unity 版本不符。請使用[安裝](installation.zh-TW.md#相容環境)列出的版本。 |
| VRoid copy or frida-il2cpp-bridge is missing | 在儲存庫執行 npm ci，並確認 --lab 指向 prepare_lab.py 做出的 lab。 |
| app/ must be a physical copy, not a link | 用 prepare_lab.py 製作新的 lab。 |
| No VRoid Studio window opened outside the MCP was found | 呼叫 attach_open_vroid 前，請先自己開啟 VRoid。 |
| Several VRoid windows are open; pass pid | 從列出的 pid 選一個，再呼叫一次 attach_open_vroid。 |
| The MCP copy is running: save_as first or pass discard_copy_unsaved=true | 需要的話先 save_as，再帶 discard_copy_unsaved=true 接上。 |
| NO_MODEL | 你的 VRoid 停在開始畫面。請用 open_start_model，或在 VRoid 開啟模型。 |
| EXPECTED_MODEL_REQUIRED | 呼叫沒有帶 model_token。請呼叫 list_face_params，把它的 model_token 當成 expected_model 帶入。 |
| STALE_MODEL／MODEL_CHANGED_DURING_OPERATION | 模型已改變。請重新列出參數，改用新的 model_token。 |
| RETURN_TO_EDIT_MODE_FIRST | 呼叫 set_preview_mode(mode="edit")。 |
| PHOTO_MODE_REQUIRED | 先呼叫 set_preview_mode(mode="photo")。 |
| COPY_DISCONNECTED | 副本已結束。呼叫 restart_session(discard_unsaved=true) 或重新啟動 MCP 伺服器；副本未保存的修改會遺失。 |
| ATTACHED_VROID_DISCONNECTED | 再呼叫一次 attach_open_vroid，或呼叫 detach_open_vroid。 |
| Native call timed out／PREVIOUS_CALL_UNCERTAIN | 不要重試那筆修改。請看[行為與限制](limitations.zh-TW.md#行為)。 |
| Height did not converge within native range | 目標超出這個模型能到的範圍。原本的大小已還原。 |
| UNKNOWN_PART_ID | 這個 VRoid 的資源庫沒有這個 ID；replace_part 只接受內建部件 ID。內建預設與衣櫃自訂物件請用 list_presets 加 apply_preset。 |
| VRM_META_NAME_REQUIRED／VRM_META_TITLE_REQUIRED | 先在 VRoid 設定模型的 VRM 名稱（1.0）或標題（0.x）。 |
| Refusing to overwrite an existing file | 換一個新檔名。 |
| REPLACE_PART_FAILED／VRM_EXPORT_FAILED | 查看 VRoid 的 Player.log（見下方）。 |

## 記錄檔

每個工作階段會把 bridge.jsonl（bridge 事件）寫到 `<lab>\runs\<時間>-<id>\`。副本的 Player.log（VRoid 的記錄）也寫在同一個資料夾。接上自己的 VRoid 時，Player.log 由 VRoid 寫在它平常的位置。
