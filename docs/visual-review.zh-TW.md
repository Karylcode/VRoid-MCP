# 圖像檢查

[English](visual-review.md) | **繁體中文** · [文件索引](README.zh-TW.md)

兩個工具都把原生畫面渲染到離屏貼圖，再輸出 PNG，所以圖片大小與 VRoid 視窗無關。截圖前會清掉編輯器的選取與輔助線；不會修改或儲存角色。

## screenshot

screenshot 回傳一張 PNG。size 預設 512，可設 256–2048：

| 視角 | view |
|---|---|
| 頭部 | front、side、back、three_quarter |
| 全身 | full_front、full_side、full_back、full_three_quarter |
| 拍攝預覽 | photo |

view 預設 front。photo 拍的是目前的拍攝預覽，需要先 set_preview_mode(mode="photo")。

## capture_review

capture_review 預設輸出四張 1024 圖片：front、three_quarter、full_front、full_back。也可指定一至六個不重複的模型視角：

~~~json
{
  "expected_model": "<model_token>",
  "label": "Before editing",
  "views": ["front", "three_quarter", "full_front", "full_back"],
  "size": 1024
}
~~~

- 不接受 photo：檢查只用可重現的模型視角。拍攝預覽請用 screenshot。
- 必須在編輯模式。請先用 set_preview_mode(mode="edit") 回來。
- label 可省略，最多 80 個字元。

工具回傳圖片、capture_id、身高及檢查提示，將 PNG 與參數快照寫入 `lab/reviews/<capture_id>/`。

修改後再次呼叫，帶入先前的 capture_id 作為 baseline_id，保持相同 views 與 size，即可取得前後圖片與臉部／體型／衣物／顏色參數差異。基準圖片會比對存下的 hash，被改過就拒絕。不同 model_token 的比較會明確標記。

檢查提示請你看：眼睛與眉毛是否平衡、瀏海是否遮眼、頭髮與頭皮間隙、頭髮與衣物穿插、頭身與四肢比例、正面／側面／背面輪廓。

## 限制

這是供 AI 或使用者看圖的工具，**沒有自動美貌評分或穿模判定**。髮型幾何變化需目視比較，物理模擬可能造成幀間差異。截圖不等於存檔。
