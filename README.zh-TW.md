# VRoid Character MCP

[English](README.md) | **繁體中文**

**v0.4.0 · Windows · 42 MCP tools · stdio**

這是在本機執行的 MCP 伺服器，讓 AI 用戶端編輯 VRoid Studio 角色：臉部、體型與服裝滑桿、髮型、配件、顏色、預設和部件。它用原生截圖檢查結果，也能匯出 VRM。操作經由 Frida 與 VRoid 自己的原生方法執行，不模擬滑鼠、鍵盤，也不使用 OCR。程式以 Python（MCP Python SDK）和 JavaScript Frida agent（frida-il2cpp-bridge）寫成，可搭配支援 stdio 的 MCP 用戶端，例如 Codex、Claude Code。

> [!IMPORTANT]
> - 本專案是**非官方、本機實驗性工具**。
> - 與 VRoid Studio 開發商 pixiv Inc. 無關，也未獲其認可。
> - 伺服器預設只啟動指定的 VRoid 實體副本，使用獨立 profile。副本與程序內寫入保護不等於作業系統沙箱。
> - 呼叫 **attach_open_vroid** 會接上你自己開啟的 VRoid，之後的修改會直接作用在你的模型。

## 能做什麼

- 臉部、體型與服裝滑桿，以及指定公分的身高
- 髮型預設、髮群與髮束參數、生成式髮群、髮骨
- 配件、顏色、表情與拍攝預覽設定
- 列出模型的部件、替換單一部件、把穿戴中的部件存成自訂物件
- 原生截圖與多角度前後比較
- 原生 Undo／Redo、另存新的 .vroid 檔、匯出 VRM 0.x／1.0
- 接上你自己開啟的 VRoid Studio

完整範圍：[使用方式](docs/usage.zh-TW.md#可以編輯的內容)。

## 需求

- Windows x64
- 通過 SHA-256 檢查的 VRoid Studio 2.14.0（Unity 6000.0.62f1）；其他版本會被拒絕
- Python 3.10、Frida 17.16.0、MCP Python SDK 1.30.0
- Node.js 與 npm（安裝 frida-il2cpp-bridge 0.14.0 用），以及 Git

儲存庫不包含 VRoid。hash 值與安裝規則請看[安裝](docs/installation.zh-TW.md)。

## 快速開始

以下為 PowerShell 範例，請依實際位置替換路徑：

~~~powershell
git clone https://github.com/Karylcode/VRoid-MCP.git C:\VRoid-MCP
Set-Location C:\VRoid-MCP
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
& .\.venv\Scripts\python.exe .\prepare_lab.py --source 'D:\SteamLibrary\steamapps\common\VRoid Studio' --lab 'C:\VRoid-MCP-lab'
~~~

在支援 stdio 的 MCP 用戶端加入伺服器。這是通用 JSON 範例，請依用戶端格式調整：

~~~json
{
  "mcpServers": {
    "vroid": {
      "command": "C:\\VRoid-MCP\\.venv\\Scripts\\python.exe",
      "args": ["C:\\VRoid-MCP\\launch.py", "--lab", "C:\\VRoid-MCP-lab"],
      "env": {
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
~~~

接著請 AI 用戶端：

1. 呼叫 **list_face_params**，取得 model_token；修改時帶入 expected_model。
2. 用 **set_face_params**、**set_body_params**、**set_parameters** 或預設工具修改。
3. 用 **capture_review** 檢查結果，再用 **save_as** 另存新的 .vroid 檔。

完整流程與範例：[使用方式](docs/usage.zh-TW.md)。

## 疑難排解

- 第一次工具呼叫才會啟動 VRoid。若用戶端可調 timeout，請給長一點，例如 120 秒。
- 每個 lab 同時只能由一個 MCP 伺服器持有。Codex、Claude Code 請分別製作 lab。
- VRoid 以系統管理員執行時，MCP 用戶端也必須以管理員執行，否則接上時會回報 PermissionError。
- 接上的 VRoid 失焦時會暫停主迴圈。若沒有回應，點一下 VRoid 視窗再呼叫一次。

更多：[疑難排解](docs/troubleshooting.zh-TW.md)。

## 文件

- [文件索引](docs/README.zh-TW.md)
- [安裝](docs/installation.zh-TW.md)
- [使用方式](docs/usage.zh-TW.md)
- [接上自己開的 VRoid](docs/own-vroid.zh-TW.md)
- [部件、自訂物件與 VRM 匯出](docs/parts-and-export.zh-TW.md)
- [圖像檢查](docs/visual-review.zh-TW.md)
- [工具參考](docs/tools.zh-TW.md)
- [行為與限制](docs/limitations.zh-TW.md)
- [疑難排解](docs/troubleshooting.zh-TW.md)
- [開發與測試](docs/development.zh-TW.md)
- [更新紀錄](CHANGELOG.zh-TW.md)
