# 需求庫網站

把 [產品需求清單-學生視角.md](../_分析/彙整/產品需求清單-學生視角.md) 與 [產品需求清單-老師視角.md](../_分析/彙整/產品需求清單-老師視角.md) 渲染成可搜尋的需求庫網站。

## 本機預覽

```bash
cd site
python3 -m http.server 8000
```

打開 http://localhost:8000

## 更新流程

修改 `_分析/彙整/` 底下任一份 .md 之後：

```bash
python3 site/build.py    # 重新產生 site/data.json
git add site/data.json _分析/彙整/*.md
git commit -m "更新需求清單"
git push
```

GitHub Pages 會自動發布。

## 部署到 GitHub Pages

1. 把整個專案 push 到 GitHub repo（公開即可）
2. 倉庫 Settings → Pages
3. Source 選 **Deploy from a branch**，Branch 選 `main`，Folder 選 `/site`
4. 儲存後 5 分鐘內網址會出現在 Settings → Pages 頂部

## 檔案

| 檔案 | 用途 | 是否手動編輯 |
| --- | --- | --- |
| `build.py` | Markdown → data.json 解析器 | ✓ |
| `index.html` | 網頁骨架 | ✓ |
| `app.js` | 搜尋、篩選、側欄邏輯 | ✓ |
| `styles.css` | 樣式 | ✓ |
| `data.json` | 由 build.py 產生（commit 進去） | ✗ 不要手改 |

## 操作說明（給瀏覽者）

- **搜尋**：上方搜尋框接受關鍵字、編號（如 `A.1`）、原句片段
- **視角／類別篩選**：搜尋框下方的 chip
- **點任一卡片**：右側推開細節面板
- **跨視角關聯**：細節面板裡的關聯項目可點，直接切換到對應的另一視角卡片，左上有「返回」按回上一張
- **可分享網址**：URL 會自動同步當前搜尋條件與開啟的卡片，複製給同事即可開啟同一視圖
- **快捷鍵**：`/` 聚焦搜尋；`Esc` 關閉側欄
