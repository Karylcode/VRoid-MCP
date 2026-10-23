# 開發與測試

[English](development.md) | **繁體中文** · [文件索引](README.zh-TW.md)

## 單元測試

單元測試不需要啟動 VRoid：

~~~powershell
& .\.venv\Scripts\python.exe -m pip install pytest
& .\.venv\Scripts\python.exe -m pytest -q
~~~

pytest 只會收集 `tests/test_*.py`：共 27 個測試案例，檢查存檔／匯出檔名規則與截圖檢查的輸入。它們會匯入 vroid_mcp.runtime，所以請先安裝 requirements.txt。

## 真實驗收腳本

真實 MCP／VRoid 測試放在 tests/。它們是獨立腳本，pytest 不會收集。請使用另外製作的 lab，一次只執行一個測試。例如：

~~~powershell
& .\.venv\Scripts\python.exe .\tests\stdio_acceptance.py C:\VRoid-MCP-test-lab .\test-evidence\stdio
~~~

| 腳本 | 參數 | 檢查內容 |
|---|---|---|
| stdio_acceptance.py | lab、output | 透過 stdio 的真實 MCP 協定 |
| live_acceptance.py | lab、output | 在新啟動的副本上執行原生 bridge；預期 F00 的臉部參數清單 |
| extension_acceptance.py | lab、output | 體型、髮型、衣物控制、Undo、渲染、存檔與重新載入 |
| parameter_acceptance.py | lab、output | 透過 stdio 的型別化參數，含存檔後重新開啟 |
| parameter_extras.py | lab、model、output | 結構操作、拍攝模式切換與乾淨截圖 |
| recovery_acceptance.py | repository、lab、output | 快速取得工具清單、原生預設完成、副本被結束後的復原 |
| reopen_acceptance.py | lab、saved .vroid、output | 新程序中的保存結果與 --model 啟動 |
| review_acceptance.py | repository、lab、output、model | capture_review、前後比較證據與防護 |

repository 是包含 launch.py 的資料夾。model 與 saved .vroid 必須在 lab 內。

## 驗證紀錄

- 0.3.2 本機驗證包含 26 項單元測試，以及多角度截圖、圖片尺寸、前後比較、Undo、錯誤輸入及舊截圖介面的真實 MCP 測試。
- 0.4.0 的新功能在 VRoid Studio 2.14.0 上手動驗證：副本存檔時真實 profile 沒有被寫入；同一個 .vroid 重複匯出的 VRM 位元組完全相同；用部件重建的 AvatarSample_M 與原版 38 個部件及所有列出的數值都相同。
- 以下 0.4.0 功能在 tests/ 裡還沒有驗收腳本：attach_open_vroid、detach_open_vroid、list_start_models、open_start_model、list_parts、replace_part、save_custom_items、export_vrm。
- 測試證據與角色素材保留本機，未放入儲存庫。

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
