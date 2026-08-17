# CI 管線強化設計 — P0~P2

日期：2026-08-17
狀態：已核准（等待實作計畫）

## 背景

對 `.github/workflows/ai-newsletter.yml` 與 `scripts/build-html.sh` 的程式碼審查發現：

- **P0-1**：`build-html.sh` 的 archive 月份分組迴圈在 pipeline subshell 執行，最後一個月份的 `</ul></details>` 未輸出，線上 `archive.html` 結構錯誤，但 CI 仍判定成功。
- **P0-2**：CI 沒有產物驗證，結構錯誤或無效 JSON 仍會部署。
- **P1-1**：CI 只在 push 到 main 後執行，缺少 PR 階段的建置與驗證。
- **P1-2**：`search_data.json` 以 `sed` 手工轉義生成，無法可靠處理所有 Markdown 輸入；`date` 只有日（如 `"17"`）而非完整日期；結果未排序。
- **P1-3**：搜尋頁 JS 將使用者輸入直接丟進 `RegExp`，輸入 `[`、`\` 等會中斷搜尋；並以 `innerHTML` 插入未過濾的標題與內容。
- **P1-4**：產物追蹤不一致：Git 追蹤 16 篇 HTML、`index.html`、`archive.html`、`search.html`、`search_data.json`，但 CI 會重新生成全部 154 篇；來源刪除後舊 HTML 可能殘留。
- **P2-1**：多數 `output/**/*.md` 首行不符標題規範；CI 內的 `normalize-md.sh` 修改不會回寫 Git，造成來源與線上內容不一致。
- **P2-2**：`/ai-newsletter/` 路徑部分寫死、部分使用 `$PROJECT_NAME`，阻礙自訂網域或改名部署。

## 範圍

修正 P0 至 P2 問題。不導入靜態網站生成器，不實作 RSS/Sitemap（P3）。

## 已確認的決策

1. **產物不追蹤**：自動生成的 HTML/JSON 不再進 Git。
2. **可設定 base path**：預設 `/ai-newsletter`，可由環境變數覆寫。
3. **一次全面正規化**：歷史 Markdown 標題一次修正完成，之後 CI 只驗證不修改。
4. **Shell + Python 輔助**：Shell 保留 Pandoc 建置流程，Python 負責搜尋 JSON 生成與驗證。

## 架構

- `output/**/*.md` 是唯一內容來源。
- `docs/` 中僅追蹤人工維護檔案：
  - `docs/README.md`
  - `docs/assets/style.css`
  - `docs/templates/header.html`、`docs/templates/footer.html`
- 以下改為生成產物，不再追蹤（加入 `.gitignore`）：
  - `docs/reports/**/*.html`
  - `docs/index.html`
  - `docs/archive.html`
  - `docs/search.html`
  - `docs/assets/search_data.json`
- `scripts/build-html.sh` 建置前先清除上述生成產物，再由 Markdown 完整重建。
- 新增 Python 工具（單一檔案，標準函式庫即可）：
  - 生成 `search_data.json`（`json.dumps`，完整日期，依日期排序）
  - 驗證：ledger 與 search JSON 可解析；HTML 報告數與 Markdown 數一致；`index.html`、`archive.html`、`search.html`、`search_data.json` 存在；archive 的 `<details>`/`</details>` 與 `<ul>`/`</ul>` 數量平衡；search 記錄的 `date` 為 `YYYY/MM/DD`；所有 Markdown 首行符合 `# 📰 AI Daily Newsletter — YYYY年MM月DD日 HH:MM`。
- 驗證失敗時輸出違規檔案清單並以非零退出，阻止部署。

## 搜尋頁修正

- `search.html` 內嵌 JS 改為：
  - 查詢字串先做 regex 跳脫再進入 `RegExp`。
  - 結果卡片以 DOM API 建構；原文用 `textContent`，highlight 以 `createElement('mark')` 分段組裝；標題與日期一律 `textContent`。
- 查詢空字串時不渲染結果（與現況一致）。

## 標題正規化遷移

- 一次性修正全部 154 篇 Markdown 首行為 `# 📰 AI Daily Newsletter — YYYY年MM月DD日 HH:MM`（月、日、時、分不足兩位補零）。時間優先取檔案前三行中的既有 newsletter 標題，無時間時預設 `09:00`；若舊標題包在前三行的 `---` front matter 內，遷移時折疊為單一首行標題，避免重複。
- 修正後移除建置流程中的 `normalize-md.sh` 呼叫，改為驗證步驟；驗證失敗即建置失敗。

## CI 流程

- `pull_request`（含 `output/**`、`docs/**`、`scripts/**`、workflow 檔案）：build + validate，不部署。
- `push` 到 `main`（路徑過濾同現況）：build + validate + deploy。
- `workflow_dispatch`：build + validate + deploy。
- Pandoc 改用 `r-lib/actions/setup-pandoc@v2` 固定版本 `3.8.3`。
- `BASE_PATH` 由 CI 環境變數或 `build-html.sh` 參數注入，預設 `/ai-newsletter`；所有資源連結、fetch、導覽連結統一使用。

## 測試

- 新增本地測試腳本，覆蓋：
  - 搜尋 JSON 生成（欄位、日期格式、排序、特殊字元跳脫）
  - 標題驗證（含規格樣本與違規樣本）
  - archive 完整性驗證（含結構錯誤樣本）
- 以全部現有 `output/**/*.md` 做資料驅動驗證。
- CI 在建置前執行測試。

## 錯誤處理

- 任一驗證或測試失敗：非零退出、輸出明確檔案清單、不進入部署。
- `set -euo pipefail` 套用至所有 Shell 腳本。

## 非目標

- RSS/Sitemap、平行化 Pandoc、自訂網域實際設定（僅預留 BASE_PATH 能力）。
