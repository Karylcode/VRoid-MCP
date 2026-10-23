# VRoid Character MCP

**v0.4.0 · Windows · 42 MCP tools · stdio**

[English](README.md) | **繁體中文**

讓 AI 透過 MCP 直接調整 VRoid Studio 的角色參數、套用髮型與服裝，並使用原生截圖檢查結果。操作經由 Frida 與 VRoid 原生方法執行，不使用滑鼠、鍵盤或 OCR。

本專案是**非官方、本機實驗性工具**。伺服器預設只啟動指定的 VRoid 實體副本，使用獨立 profile。只有呼叫 **attach_open_vroid** 時，才會接上使用者自己開啟的 VRoid，之後的修改會直接作用在使用者的模型。副本與程序內寫入保護不等於作業系統沙箱。

## 功能

| 範圍 | 支援內容 |
|---|---|
| 臉部與體型 | 眼睛、眉毛、鼻子、嘴巴、臉型、頭身比例、肩頸、胸腰及四肢滑桿 |
| 身高 | 指定公分目標，透過全身大小參數校正並回報誤差 |
| 髮型 | 套用髮型／髮片預設；髮群與髮束參數、導向位移／旋轉／縮放、粗細、扭轉、截面、形狀曲線；新增生成式髮群與移除髮群／髮束 |
| 髮骨 | 骨骼分組、骨骼數、硬度、重力、碰撞半徑與自動生成 |
| 服裝與配件 | 套用已擁有預設與衣櫃中的自訂物件、調整衣物形狀；新增／複製／移除配件及其可用參數 |
| 部件 | 列出模型由哪些部件組成、依 ID 單獨替換一個部件、把穿戴中的部件存成自訂物件 |
| 色彩 | 眼睛、頭髮、眉睫、膚色等 VRoid 原生顏色控制 |
| 表情與拍攝 | 表情定義與預覽、姿勢、手勢、燈光、風、鏡頭及可用拍攝參數 |
| 圖像檢查 | 256–2048 像素原生截圖、多角度檢查、前後圖片及參數比較 |
| 歷史、存檔與匯出 | 原生 Undo／Redo，另存新的 .vroid 檔案，透過 VRoid 自己的匯出器輸出 VRM 0.x／1.0 |
| 自己開的 VRoid | 接上使用者開啟的 VRoid Studio、開啟開始畫面的模型卡、離開時不關閉 VRoid |

不包含貼圖繪製、自製材質、手繪髮束或任意程式碼執行。可用參數依角色、部件與模式改變；不是所有內部 API 都已覆蓋。

## 相容環境

已驗證的組合：

- Windows x64。
- VRoid Studio 2.14.0，Unity 6000.0.62f1。
- Python 3.10、Frida 17.16.0、MCP Python SDK 1.30.0。
- frida-il2cpp-bridge 0.14.0，透過 npm 安裝 JavaScript bridge。

安裝另需 Git、Node.js 與 npm。啟動時會檢查 GameAssembly.dll 的 SHA-256，僅接受下列已驗證的 binary；版本名稱相同但 hash 不同也會拒絕。attach_open_vroid 對使用者開啟的 VRoid 做同樣的檢查：

~~~text
793eb5fcff3093f344ee930fbfa0c0796ed7780ac91c45bdb7ce6bd34d62fd3c
~~~

VRoid 安裝檔、角色、截圖、測試輸出及私人設定不隨儲存庫提供，需自行準備相容的 VRoid 安裝。

## 安裝

以下為 PowerShell 範例，請依實際位置替換路徑：

~~~powershell
git clone https://github.com/Karylcode/VRoid-MCP.git C:\VRoid-MCP
Set-Location C:\VRoid-MCP
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
& .\.venv\Scripts\python.exe .\prepare_lab.py --source 'D:\SteamLibrary\steamapps\common\VRoid Studio' --lab 'C:\VRoid-MCP-lab'
~~~

prepare_lab.py 會複製並驗證檔案，不修改來源。lab 必須是**尚不存在**的目錄，與原安裝位置互不包含；不接受 junction／symlink。請預留完整安裝副本所需的空間。

## MCP 連線

在支援 stdio 的 MCP 客戶端設定以下 command、args 與 env。這是通用 JSON 範例；請依客戶端所需格式填入對應欄位。

~~~json
{
  "mcpServers": {
    "vroid": {
      "command": "C:\\VRoid-MCP\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\VRoid-MCP\\launch.py",
        "--lab",
        "C:\\VRoid-MCP-lab"
      ],
      "env": {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
~~~

- 工具清單立即可用，**第一次工具呼叫才啟動 VRoid 副本**。
- 每次新伺服器工作階段預設建立 F00 角色；加入 --variant M00 可改用男性基底。
- 要開啟既有角色，在 args 加入 --model 和 **lab 內**的 .vroid 絕對路徑。重新連線不會自動延續上次編輯。
- 每個 lab 同時只能由一個 MCP 伺服器持有，接上自己的 VRoid 時也一樣。Codex、Claude Code 同時使用時，請分別製作 lab。
- 若客戶端允許調整 timeout，可給較長的首次呼叫時間，例如 120 秒。
- 更新程式後需重新載入 MCP 才能取得新工具。先另存角色，因伺服器結束會關閉自己啟動的副本；使用者自己開的 VRoid 不會被關閉。

## 使用流程

1. 呼叫 **list_face_params**，取得 model_token；後續修改帶入 expected_model。
2. 先列出相關參數／預設，再使用回傳的 id、範圍與型別。依 next_offset 讀取後續頁面。
3. 修改前以 **capture_review** 留下比較基準。
4. 用 **set_face_params、set_body_params、set_parameters** 或預設工具調整角色。
5. 用 **screenshot／capture_review** 看圖檢查，必要時 Undo。更換髮型、衣服、部件或結構後重新列舉參數。
6. 完成造型後執行 **set_height**，再用 **save_as** 另存，例如 character.vroid。

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

髮型調整：list_hair_nodes(category="HairTied") → 以節點 id 作為 scope 呼叫 list_parameters(domain="hair", category="HairTied", scope=...) → set_parameters。

拍攝流程：set_preview_mode(mode="photo") → list_parameters(domain="photo") → 調整拍攝參數 → screenshot(view="photo")。回到 mode="edit" 後再編輯、capture_review 或存檔。拍攝設定只屬於當次工作階段，不保存到 .vroid。

set_face_params 與 set_body_params 可加 allow_out_of_ui_range=true，允許超出 UI 範圍最多一個滑桿跨度。只用來照搬別的模型真的存著的值（例如舊版 VRoid 做的樣本），不要拿來自創數值。

## 接上自己開的 VRoid

- **attach_open_vroid(pid?)**：所有工具改為操作使用者自己開啟的 VRoid Studio（例如 Steam 版）。只開一個時免填 pid；開了多個時，錯誤訊息會列出候選 pid。若 MCP 副本已啟動，需加 discard_copy_unsaved=true，副本會被關閉（需要的話先 save_as）。
- 修改走 VRoid 原生歷史，可在 VRoid 內 Ctrl+Z。save_as、開啟或新建模型一律拒絕，請在 VRoid 自己存檔。
- 不載入隔離 hook，不改寫使用者的檔案路徑、登錄檔與子程序，只裝讀寫參數所需的 hook。
- VRoid 失焦時 Unity 會暫停主迴圈。接上時會喚醒訊息迴圈，讓 VRoid 在背景繼續處理。若主執行緒仍無回應，點一下 VRoid 視窗再呼叫一次。
- VRoid 停在開始畫面時，**list_start_models** 列出最近的模型、內建 AvatarSample 與舊版模型；**open_start_model(name)** 等同點擊該卡片，最多等待 90 秒。只在還沒開模型時可用，不會覆蓋未存檔內容。
- **detach_open_vroid**：歸還 VRoid 原本的背景執行設定、釋放 handle、卸載 hook 後離開。VRoid 繼續開著，未存檔內容不受影響；之後的工具呼叫回到 MCP 副本。接上狀態下 restart_session 也只會離開。
- VRoid 以系統管理員執行時（例如 Steam 以管理員開啟），MCP 客戶端也必須以管理員執行，否則回報 PermissionError。

## 部件與自訂物件

- **list_parts**：列出模型由哪些部件（transferable group）組成，含 id、type、resource_name、自訂部件的內建來源 original_resource_name，以及 custom／updated 旗標。
- **replace_part(part_id)**：單獨替換一個部件，例如只換臉型而不動同套組的其他部分。接受內建 ID 與已登錄在該 VRoid 衣櫃的自訂物件。資源庫裡沒有的 ID（例如舊版 VRoid 檔案的部件 ID）一律拒絕，因為原生載入器遇到它會讓 VRoid 當掉。
- **save_custom_items(types?)**：等同 VRoid「存成自訂物件」，把穿戴中 VRoid 標為可存（自訂或修改過）的部件存起來。檔案寫入受控 VRoid 的 custom_items：副本寫在 lab profile，接上時寫進使用者真正的衣櫃。
- list_presets 也會列出衣櫃中的自訂物件（custom=true），可用 apply_preset 套用。

在新版 VRoid 重建舊角色：依 resource_name 對應部件，用 save_custom_items 存下自訂或修改過的部件並套到新模型，單一部件用 replace_part 替換，最後搬數值並逐項比對。

## VRM 匯出

**export_vrm(expected_model, filename, version=1)** 走 VRoid 自己的匯出器。version 1 為 VRM 1.0，0 為 VRM 0.x。

- 檔案寫到 lab/exports/，不覆寫既有檔案。會自動進出匯出畫面。
- 名稱、作者、授權取自模型存的 VRM 匯出資訊；模型沒有名稱時拒絕匯出。
- 採 VRoid 預設設定：合併頭髮網格，不縮減材質／網格。
- MCP 副本與 attach_open_vroid 後的使用者 VRoid 都能用。

## 多角度截圖檢查

screenshot 的 size 預設 512，可設 256–2048：

| 視角 | view |
|---|---|
| 頭部 | front、side、back、three_quarter |
| 全身 | full_front、full_side、full_back、full_three_quarter |
| 拍攝預覽 | photo |

capture_review 預設輸出四張 1024 圖片，也可指定一至六個不重複的模型視角：

~~~json
{
  "expected_model": "<model_token>",
  "label": "Before editing",
  "views": ["front", "three_quarter", "full_front", "full_back"],
  "size": 1024
}
~~~

工具回傳圖片、capture_id、身高及檢查提示，將 PNG 與參數快照寫入 `lab/reviews/<capture_id>/`。修改後再次呼叫，帶入先前的 baseline_id，保持相同 views 與 size，即可取得前後圖片與臉部／體型／衣物／顏色參數差異。

這是供 AI 或使用者看圖的工具，**沒有自動美貌評分或穿模判定**。髮型幾何變化需目視比較，物理模擬可能造成幀間差異；不同 model_token 的比較會明確標記。截圖不等於存檔。

## 行為與限制

- 批次不是交易。雖然會先驗證輸入，原生執行錯誤仍可能留下部分修改；檢查 ok／applied／error。Undo 可能需要多步。
- save_as 只接受單一 .vroid 檔名，寫到 lab/saves/，拒絕覆蓋現有檔案。
- restart_session(discard_unsaved=true) 會重建 MCP 自己的副本並丟棄未保存修改；新 token 使舊模型識別失效。
- 部分原生髮型套用後不保留整套勾選狀態。selected=false 不一定是失敗，請檢查 changed、confirmation 及截圖。
- 身高受造型與比例影響。get_height 同時回報 UI 快取 centimeters 與即時測量 live_centimeters，兩者可能略有差異。
- 目前以 F00 為主要驗證對象；M00、完整失焦操作與長時間穩定性尚未完成同等程度驗收。

## 0.4.0 更新內容

- 新工具：attach_open_vroid、detach_open_vroid、list_start_models、open_start_model、list_parts、replace_part、save_custom_items、export_vrm。
- 隔離修正：0.3.2 的副本仍可能把 file_access_history.json、history_temp、vroid_file_temporary 寫進使用者真正的 `LocalLow\pixiv\VRoid Studio`。原因是 Unity 透過 windows.storage.dll 取得資料路徑、部分檔案呼叫直接進 kernelbase.dll，而且 agent 發出的原生呼叫期間 Frida 不會觸發 Interceptor。現在所有匯出資料夾查詢的模組都會被 hook；檔案與登錄檔 hook 改掛在 kernelbase.dll，並補上 CreateFile2、CopyFile*、MoveFileWithProgressW、SetFileAttributesW、CreateDirectoryExW；agent/traps.js 讓所有 NativeFunction 使用 traps:'all'。
- 配件 IsVisible 改用 VRoid 原生的顯示歷史命令。原本只改清單圖示，模型照樣顯示。
- set_face_params、set_body_params 新增 allow_out_of_ui_range。
- capture_review 不再把每張 PNG 以 base64 結構化內容重複送一次。

## 測試

單元測試不需要啟動 VRoid：

~~~powershell
& .\.venv\Scripts\python.exe -m pip install pytest
& .\.venv\Scripts\python.exe -m pytest -q
~~~

真實 MCP／VRoid 測試放在 tests/。請使用另外製作的 lab，一次只執行一個測試。例如：

~~~powershell
& .\.venv\Scripts\python.exe .\tests\stdio_acceptance.py C:\VRoid-MCP-test-lab .\test-evidence\stdio
~~~

0.3.2 本機驗證包含 26 項單元測試，以及多角度截圖、圖片尺寸、前後比較、Undo、錯誤輸入及舊截圖介面的真實 MCP 測試。0.4.0 的新功能在 VRoid Studio 2.14.0 上手動驗證：副本存檔時真實 profile 沒有被寫入；同一個 .vroid 重複匯出的 VRM 位元組完全相同；用部件重建的 AvatarSample_M 與原版 38 個部件及所有列出的數值都相同。這些功能在 tests/ 裡還沒有驗收腳本。測試證據與角色素材保留本機，未放入儲存庫。

## 原始碼結構

| 路徑 | 用途 |
|---|---|
| launch.py | stdio 入口 |
| prepare_lab.py | 製作並驗證安裝副本 |
| vroid_mcp/server.py | MCP 工具定義 |
| vroid_mcp/runtime.py | 程序生命週期、接上既有 VRoid、原生呼叫與檔案處理 |
| agent/traps.js | 讓原生呼叫期間隔離 hook 照樣生效 |
| agent/bootstrap.js | Unity 主執行緒派送，接管已在執行的 VRoid |
| agent/isolate.js | 私有 profile 與程序內寫入保護 |
| agent/operations.js | 模型、歷史、部件、存檔、VRM 匯出與截圖 |
| agent/parameters.js | 型別化參數介面 |
| tests/ | 單元與真實整合測試 |
