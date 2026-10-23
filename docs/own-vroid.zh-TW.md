# 接上自己開的 VRoid

[English](own-vroid.md) | **繁體中文** · [文件索引](README.zh-TW.md)

預設所有工具都操作 MCP 副本。呼叫 **attach_open_vroid** 後，所有工具改為操作你自己開啟的 VRoid Studio。**之後的修改會直接作用在你的模型。**

## 接上

- **attach_open_vroid(pid?)**：所有工具改為操作你自己開啟的 VRoid Studio（例如 Steam 版）。只開一個時免填 pid；開了多個時，錯誤訊息會列出候選 pid。
- 若 MCP 副本已啟動，需加 discard_copy_unsaved=true，副本會被關閉（需要的話先 save_as）。
- attach_open_vroid 會用與副本相同的 SHA-256 檢查你的 VRoid 的 GameAssembly.dll。其他版本會被拒絕。
- 伺服器仍需要 --lab。每個 lab 同時只能由一個伺服器持有，接上時也一樣。
- VRoid 以系統管理員執行時（例如 Steam 以管理員開啟），MCP 用戶端也必須以管理員執行，否則回報 PermissionError。

## 接上期間

- 修改走 VRoid 原生歷史，可在 VRoid 內 Ctrl+Z。
- save_as、開啟或新建模型一律拒絕，請在 VRoid 自己存檔。唯一例外是開始畫面上的 open_start_model（見下方）。
- **save_custom_items** 會寫進你真正的衣櫃（你的 VRoid profile 裡的 custom_items 資料夾），不是 lab。
- export_vrm 可以使用，檔案寫到 lab 的 exports 資料夾。
- 不載入隔離 hook，不改寫你的檔案路徑、登錄檔與子程序，只裝讀寫參數所需的 hook。
- VRoid 失焦時 Unity 會暫停主迴圈。接上時會喚醒訊息迴圈，讓 VRoid 在背景繼續處理。若主執行緒仍無回應，點一下 VRoid 視窗再呼叫一次。

## 開始畫面

VRoid 停在開始畫面時，**list_start_models** 列出最近的模型、內建 AvatarSample 與舊版模型。**open_start_model(name)** 等同點擊該卡片；名稱重複時加上 group（recent、sample 或 old）。最多等待 90 秒，只在還沒開模型時可用，不會覆蓋未存檔內容。若載入較久（例如正在下載樣本或出現對話框），會回傳 opened=false；請用 get_status 確認。

MCP 副本一定已經開著模型，所以 open_start_model 主要用於你自己的 VRoid。

## 離開

- **detach_open_vroid**：歸還 VRoid 原本的背景執行設定、釋放 handle、卸載 hook 後離開。VRoid 繼續開著，未存檔內容不受影響；之後的工具呼叫回到 MCP 副本。
- 接上狀態下 restart_session 只會離開，不會關閉你的 VRoid；接著會啟動新的 MCP 副本。
- 伺服器結束時也是同樣離開，不會關閉你自己開的 VRoid。
- 與你的 VRoid 斷線時，工具會回報 ATTACHED_VROID_DISCONNECTED。請再呼叫一次 attach_open_vroid，或呼叫 detach_open_vroid。
