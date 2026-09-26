# VRoid Character MCP

**v0.3.2 · Windows · 34 MCP tools · stdio**

[繁體中文](#繁體中文) | [English](#english)

## 繁體中文

讓 AI 透過 MCP 直接調整 VRoid Studio 的角色參數、套用髮型與服裝，並使用原生截圖檢查結果。操作經由 Frida 與 VRoid 原生方法執行，不使用滑鼠、鍵盤或 OCR。

本專案是**非官方、本機實驗性工具**。伺服器只啟動指定的 VRoid 實體副本，使用獨立 profile，不附加使用者原本開啟的 VRoid 程序。副本與程序內寫入保護不等於作業系統沙箱。

### 功能

| 範圍 | 支援內容 |
|---|---|
| 臉部與體型 | 眼睛、眉毛、鼻子、嘴巴、臉型、頭身比例、肩頸、胸腰及四肢滑桿 |
| 身高 | 指定公分目標，透過全身大小參數校正並回報誤差 |
| 髮型 | 套用髮型／髮片預設；髮群與髮束參數、導向位移／旋轉／縮放、粗細、扭轉、截面、形狀曲線；新增生成式髮群與移除髮群／髮束 |
| 髮骨 | 骨骼分組、骨骼數、硬度、重力、碰撞半徑與自動生成 |
| 服裝與配件 | 套用已擁有預設、調整衣物形狀；新增／複製／移除配件及其可用參數 |
| 色彩 | 眼睛、頭髮、眉睫、膚色等 VRoid 原生顏色控制 |
| 表情與拍攝 | 表情定義與預覽、姿勢、手勢、燈光、風、鏡頭及可用拍攝參數 |
| 圖像檢查 | 256–2048 像素原生截圖、多角度檢查、前後圖片及參數比較 |
| 歷史與存檔 | 原生 Undo／Redo，僅另存新的 .vroid 檔案 |

不包含貼圖繪製、自製材質、手繪髮束、VRM 匯出或任意程式碼執行。可用參數依角色、部件與模式改變；不是所有內部 API 都已覆蓋。

### 相容環境

已驗證的組合：

- Windows x64。
- VRoid Studio 2.14.0，Unity 6000.0.62f1。
- Python 3.10、Frida 17.16.0、MCP Python SDK 1.30.0。
- frida-il2cpp-bridge 0.14.0，透過 npm 安裝 JavaScript bridge。

安裝另需 Git、Node.js 與 npm。啟動時會檢查 GameAssembly.dll 的 SHA-256，僅接受下列已驗證的 binary；版本名稱相同但 hash 不同也會拒絕：

~~~text
793eb5fcff3093f344ee930fbfa0c0796ed7780ac91c45bdb7ce6bd34d62fd3c
~~~

VRoid 安裝檔、角色、截圖、測試輸出及私人設定不隨儲存庫提供，需自行準備相容的 VRoid 安裝。

### 安裝

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

### MCP 連線

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
- 每個 lab 同時只能由一個 MCP 伺服器持有。Codex、Claude Code 同時使用時，請分別製作 lab。
- 若客戶端允許調整 timeout，可給較長的首次呼叫時間，例如 120 秒。
- 更新程式後需重新載入 MCP 才能取得新工具。先另存角色，因伺服器結束會關閉自己啟動的副本。

### 使用流程

1. 呼叫 **list_face_params**，取得 model_token；後續修改帶入 expected_model。
2. 先列出相關參數／預設，再使用回傳的 id、範圍與型別。依 next_offset 讀取後續頁面。
3. 修改前以 **capture_review** 留下比較基準。
4. 用 **set_face_params、set_body_params、set_parameters** 或預設工具調整角色。
5. 用 **screenshot／capture_review** 看圖檢查，必要時 Undo。更換髮型、衣服或結構後重新列舉參數。
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

### 多角度截圖檢查

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

### 行為與限制

- 批次不是交易。雖然會先驗證輸入，原生執行錯誤仍可能留下部分修改；檢查 ok／applied／error。Undo 可能需要多步。
- save_as 只接受單一 .vroid 檔名，寫到 lab/saves/，拒絕覆蓋現有檔案。
- restart_session(discard_unsaved=true) 會重建 MCP 自己的副本並丟棄未保存修改；新 token 使舊模型識別失效。
- 部分原生髮型套用後不保留整套勾選狀態。selected=false 不一定是失敗，請檢查 changed、confirmation 及截圖。
- 身高受造型與比例影響。get_height 同時回報 UI 快取 centimeters 與即時測量 live_centimeters，兩者可能略有差異。
- 目前以 F00 為主要驗證對象；M00、完整失焦操作與長時間穩定性尚未完成同等程度驗收。

### 測試

單元測試不需要啟動 VRoid：

~~~powershell
& .\.venv\Scripts\python.exe -m pip install pytest
& .\.venv\Scripts\python.exe -m pytest -q
~~~

真實 MCP／VRoid 測試放在 tests/。請使用另外製作的 lab，一次只執行一個測試。例如：

~~~powershell
& .\.venv\Scripts\python.exe .\tests\stdio_acceptance.py C:\VRoid-MCP-test-lab .\test-evidence\stdio
~~~

0.3.2 本機驗證包含 26 項單元測試，以及多角度截圖、圖片尺寸、前後比較、Undo、錯誤輸入及舊截圖介面的真實 MCP 測試。測試證據與角色素材保留本機，未放入儲存庫。

---

## English

Control VRoid Studio character parameters, apply hair and clothing presets, and inspect the result through native screenshots using MCP. Operations run through Frida and VRoid's native methods, without mouse input, keyboard automation, or OCR.

This is an **unofficial, experimental local tool**. The server launches only a designated physical copy of VRoid with a separate profile. It does not attach to your existing VRoid process. Copy isolation and in-process write guards are not an operating-system sandbox.

### Features

| Area | Supported controls |
|---|---|
| Face and body | Eyes, eyebrows, nose, mouth, face shape, head/body proportions, shoulders, neck, chest, waist and limbs |
| Height | Centimeter target, whole-body scale adjustment and measurement error |
| Hair | Owned hairstyle/part presets; group/strand parameters, guide transforms, width, thickness, twist, cross-sections and shape curves; procedural group creation and group/strand removal |
| Hair bones | Grouping, bone count, stiffness, gravity, collision radius and generation settings |
| Clothing and accessories | Owned presets, garment shape controls, accessory creation/duplication/removal and available parameters |
| Colors | Native eye, hair, eyebrow, eyelash, skin and related color controls |
| Expressions and photo preview | Expression definitions and preview, poses, hands, lighting, wind, camera and available photo parameters |
| Visual review | Native 256–2048 pixel screenshots, multiple views, before/after images and parameter comparisons |
| History and saving | Native Undo/Redo and save-as to a new .vroid file |

Texture painting, custom material authoring, hand-drawn hair strands, VRM export and arbitrary code execution are outside the current scope. Available parameters vary by model, part and mode; this is not complete coverage of every internal API.

### Compatibility

Validated with Windows x64, VRoid Studio 2.14.0 / Unity 6000.0.62f1, Python 3.10, Frida 17.16.0, MCP Python SDK 1.30.0 and frida-il2cpp-bridge 0.14.0. Git, Node.js and npm are required for checkout and dependency installation.

Startup checks GameAssembly.dll against this SHA-256 and rejects other binaries, even if their displayed version is identical:

~~~text
793eb5fcff3093f344ee930fbfa0c0796ed7780ac91c45bdb7ce6bd34d62fd3c
~~~

The repository does not include VRoid binaries, characters, screenshots, test output or private client configuration. Supply your own compatible VRoid installation.

### Installation

PowerShell example; replace paths with your own:

~~~powershell
git clone https://github.com/Karylcode/VRoid-MCP.git C:\VRoid-MCP
Set-Location C:\VRoid-MCP
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm ci
& .\.venv\Scripts\python.exe .\prepare_lab.py --source 'D:\SteamLibrary\steamapps\common\VRoid Studio' --lab 'C:\VRoid-MCP-lab'
~~~

prepare_lab.py copies and verifies the installation without modifying its source. The lab directory must **not already exist**. Neither directory may contain the other, and junctions/symlinks are rejected. Allow enough disk space for a full installation copy.

### MCP connection

Configure command, args and env in a stdio-capable MCP client. This generic JSON example may need to be adapted to your client's configuration format:

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

- Tool discovery is immediate. The VRoid copy starts on the **first tool call**.
- A new server session creates an F00 character by default. Add --variant M00 for the male base.
- To open an existing character, add --model followed by an absolute path to a .vroid file **inside the lab**. Reconnecting does not automatically resume your last character.
- Only one server can own a lab at a time. Create separate labs for simultaneous Codex and Claude Code sessions.
- If configurable, allow a longer first-call timeout, such as 120 seconds.
- Reload the MCP connection after updating the code. Save first: shutting down the server closes its own VRoid copy.

### Editing workflow

1. Call **list_face_params** to obtain model_token. Pass it as expected_model when editing.
2. List parameters or presets before applying changes. Use returned IDs, types, limits and options; follow next_offset pagination.
3. Capture a baseline with **capture_review**.
4. Edit through **set_face_params, set_body_params, set_parameters** or preset tools.
5. Inspect **screenshot/capture_review** images and use Undo when needed. Relist parameters after changing hair, clothing or structure.
6. Apply **set_height** after styling, then **save_as** with a new filename such as character.vroid.

Example arguments for set_parameters. Replace the token and confirm these controls exist and are editable:

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

For hair, call list_hair_nodes(category="HairTied"), use a returned node ID as scope in list_parameters(domain="hair", category="HairTied", scope=...), then call set_parameters.

For photo preview, use set_preview_mode(mode="photo"), list_parameters(domain="photo"), adjust settings, then screenshot(view="photo"). Return to mode="edit" before editing, capture_review or saving. Photo settings are session-only and are not stored in the .vroid file.

### Screenshot review

screenshot accepts front, side, back and three_quarter for the head; prefix them with full_ for full-body views. Use photo for the active photo preview. size defaults to 512 and accepts 256–2048 pixels.

capture_review defaults to four 1024-pixel images: front, three_quarter, full_front and full_back. You can request one to six distinct model views:

~~~json
{
  "expected_model": "<model_token>",
  "label": "Before editing",
  "views": ["front", "three_quarter", "full_front", "full_back"],
  "size": 1024
}
~~~

The tool returns images, a capture_id, height readings and a visual checklist. PNGs and parameter snapshots are saved under `lab/reviews/<capture_id>/`.

After editing, pass the previous capture_id as baseline_id with the same views and size to obtain before/after images and face/body/clothing/color parameter differences. Reviews with different model tokens are explicitly identified.

This provides evidence for visual inspection, **not an automated beauty score or collision test**. Hair geometry changes require image inspection, and hair physics may vary between frames. Capturing images does not save the character.

### Behavior and limitations

- Batches are not transactions. Inputs are validated first, but a native execution error may leave partial edits. Inspect ok, applied and error. A batch may require several Undo steps.
- save_as accepts a single .vroid filename, writes only under lab/saves/ and refuses to overwrite an existing file.
- restart_session(discard_unsaved=true) recreates only the MCP-owned copy and discards unsaved changes. Its new token invalidates the previous model identity.
- Some hair presets expand into parts without retaining the whole-set checkbox. selected=false alone does not establish failure; inspect changed, confirmation and screenshots.
- Height depends on styling and proportions. get_height reports both cached UI centimeters and live_centimeters; they can differ slightly.
- F00 is the primary validation target. M00, comprehensive unfocused operation and long-running stability have not received equivalent validation.

### Tests

Unit tests do not start VRoid:

~~~powershell
& .\.venv\Scripts\python.exe -m pip install pytest
& .\.venv\Scripts\python.exe -m pytest -q
~~~

Live MCP/VRoid tests are in tests/. Prepare a separate lab and run only one test against it at a time:

~~~powershell
& .\.venv\Scripts\python.exe .\tests\stdio_acceptance.py C:\VRoid-MCP-test-lab .\test-evidence\stdio
~~~

Local validation for 0.3.2 included 26 unit tests and real MCP tests covering multi-view images, resolutions, before/after comparison, Undo, invalid requests and compatibility with the original screenshot interface. Evidence and character fixtures are kept locally rather than committed.

### Source layout / 原始碼結構

| Path | Purpose / 用途 |
|---|---|
| launch.py | stdio entry point / stdio 入口 |
| prepare_lab.py | Verified installation copy / 製作並驗證安裝副本 |
| vroid_mcp/server.py | MCP tool definitions / MCP 工具定義 |
| vroid_mcp/runtime.py | Process lifecycle, native calls and artifacts / 程序生命週期、原生呼叫與檔案處理 |
| agent/bootstrap.js | Unity main-thread dispatch / Unity 主執行緒派送 |
| agent/isolate.js | Private profile and in-process write guards / 私有 profile 與程序內寫入保護 |
| agent/operations.js | Model, history, saving and capture / 模型、歷史、存檔與截圖 |
| agent/parameters.js | Typed parameter interfaces / 型別化參數介面 |
| tests/ | Unit and live integration tests / 單元與真實整合測試 |
