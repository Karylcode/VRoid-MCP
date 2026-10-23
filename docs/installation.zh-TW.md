[English](installation.md) | **繁體中文** · [文件索引](README.zh-TW.md)

# 安裝

## 相容環境

已驗證的組合：

- Windows x64。
- VRoid Studio 2.14.0，Unity 6000.0.62f1。
- Python 3.10、Frida 17.16.0、MCP Python SDK 1.30.0。
- frida-il2cpp-bridge 0.14.0，透過 npm 安裝。

安裝另需 Git、Node.js 與 npm。pyproject.toml 接受 Python 3.10 以上，但只驗證過 3.10。

啟動時會檢查 GameAssembly.dll 的 SHA-256，只接受下列已驗證的 binary；版本名稱相同但 hash 不同也會拒絕。prepare_lab.py 複製前做同樣的檢查，attach_open_vroid 也會檢查你自己開啟的 VRoid：

~~~text
793eb5fcff3093f344ee930fbfa0c0796ed7780ac91c45bdb7ce6bd34d62fd3c
~~~

Frida agent 也會拒絕 6000.0.62f1 以外的 Unity 版本。

VRoid 安裝檔、角色、截圖、測試輸出及私人設定不隨儲存庫提供，需自行準備相容的 VRoid 安裝。

## 安裝步驟

以下為 PowerShell 範例，請依實際位置替換路徑：

~~~powershell
git clone https://github.com/Karylcode/VRoid-MCP.git C:\VRoid-MCP
Set-Location C:\VRoid-MCP
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
~~~

npm ci 會把 frida-il2cpp-bridge 裝進儲存庫內的 node_modules。伺服器從那裡載入它。

## 製作 lab

~~~powershell
& .\.venv\Scripts\python.exe .\prepare_lab.py --source 'D:\SteamLibrary\steamapps\common\VRoid Studio' --lab 'C:\VRoid-MCP-lab'
~~~

prepare_lab.py 會複製並驗證檔案，不修改來源：

- lab 必須是**尚不存在**的目錄。
- 兩個目錄不能互相包含。
- 來源內有 junction／symlink 時會拒絕。
- 每個來源檔案都會計算 hash，複製到 `<lab>\app\` 後再檢查一次。hash 寫入 `<lab>\source-manifest.json`。

請預留完整安裝副本所需的空間。伺服器之後會視需要在 lab 內建立 `profile\`（副本的私有 profile）、`runs\`（記錄檔）、`saves\`、`exports\` 與 `reviews\`。

## MCP 連線

在支援 stdio 的 MCP 用戶端設定以下 command、args 與 env。這是通用 JSON 範例；請依用戶端所需格式填入對應欄位。

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
- 若用戶端允許調整 timeout，可給較長的首次呼叫時間，例如 120 秒。
- 更新程式後需重新載入 MCP 才能取得新工具。請先另存角色，因為伺服器結束會關閉自己啟動的副本；你自己開的 VRoid 不會被關閉。

## 命令列參數

| 參數 | 必填 | 預設 | 說明 |
|---|---|---|---|
| --lab | 是 | — | lab 目錄，內含實體的 `app\VRoidStudio.exe` 副本 |
| --variant | 否 | F00 | 新模型的基底角色：F00 或 M00。只在沒有 --model 時使用 |
| --model | 否 | — | 已在 lab 內的 .vroid 檔，啟動時開啟它，不建立新模型 |

## 選用：指令入口

`pip install -e .` 也會在 `.venv\Scripts` 註冊 `vroid-face-mcp` 指令。請用可編輯安裝（`-e`）：伺服器從儲存庫載入 `agent\*.js` 與 `node_modules`，一般安裝不會包含它們。venv 沒有啟用時不在 PATH 上，所以請給用戶端完整路徑：

~~~json
"command": "C:\\VRoid-MCP\\.venv\\Scripts\\vroid-face-mcp.exe",
"args": ["--lab", "C:\\VRoid-MCP-lab"]
~~~

env 設定與上面相同。前面用 launch.py 的設定不需要 `pip install -e .`。
