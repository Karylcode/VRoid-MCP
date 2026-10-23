[English](limitations.md) | **繁體中文** · [文件索引](README.zh-TW.md)

# 行為與限制

## 行為

- 批次不是交易。雖然會先驗證輸入，原生執行錯誤仍可能留下部分修改；檢查 ok／applied／error。Undo 可能需要多步。
- save_as 只接受單一 .vroid 檔名，寫到 lab/saves/，拒絕覆蓋現有檔案。
- restart_session(discard_unsaved=true) 會重建 MCP 自己的副本並丟棄未保存修改；新 token 使舊模型識別失效。
- 部分原生髮型套用後不保留整套勾選狀態。selected=false 不一定是失敗，請檢查 changed、confirmation 及截圖。
- 身高受造型與比例影響。get_height 同時回報 UI 快取 centimeters 與即時測量 live_centimeters，兩者可能略有差異。set_height 接受 20–400 公分，但實際能到的範圍依模型而定，可能更窄。
- 每次原生呼叫上限 30 秒。逾時後結果不確定：之後的呼叫會以 PREVIOUS_CALL_UNCERTAIN 拒絕，get_status 顯示 writes_blocked=true。不要重試那筆修改。副本請用 restart_session(discard_unsaved=true) 復原；你自己的 VRoid 請再呼叫一次 attach_open_vroid。
- 拍攝設定只屬於當次工作階段，不保存到 .vroid。
- MCP 副本一定已經開著模型，所以 open_start_model 主要用於你自己的 VRoid。

## 副本隔離

伺服器預設只啟動指定的 VRoid 實體副本，使用獨立 profile。副本與程序內寫入保護不等於作業系統沙箱。

對副本，伺服器會：

- 把 USERPROFILE、APPDATA、LOCALAPPDATA、TEMP、TMP 指向 `<lab>\profile\`；
- 把系統資料夾查詢與你真正 profile 底下的檔案路徑，轉到這個私有 profile；
- 擋下 lab 以外的檔案寫入，以及開啟 lab 以外的 .vroid；
- 讓副本使用自己的登錄檔機碼，不用 VRoid 原本的；
- 擋下子程序，因為重新啟動的 VRoid 會失去這些保護。

它不會擋網路連線，也不會擋讀取其他檔案。接上你自己的 VRoid 時，這些保護都不會載入。0.4.0 的隔離修正請看[更新紀錄](../CHANGELOG.zh-TW.md)。

## 不支援的功能

不包含貼圖繪製、自製材質、手繪髮束或任意程式碼執行。可用參數依角色、部件與模式改變；不是所有內部 API 都已覆蓋。

## 驗證狀態

- 只驗證過[安裝](installation.zh-TW.md#相容環境)列出的組合。
- 目前以 F00 為主要驗證對象；M00、完整失焦操作與長時間穩定性尚未完成同等程度驗收。
- 0.4.0 的新功能經手動驗證，tests/ 裡還沒有驗收腳本。請看[開發與測試](development.zh-TW.md#驗證紀錄)。
