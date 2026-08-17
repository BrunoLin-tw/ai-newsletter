# 🤖 AI Daily Newsletter - 使用指南

## 📋 頁面說明

### 1. **最新頁面** (`index.html`)
- 以卡片顯示**最新 3 期**電子報
- 每張卡片直接連到完整報告

### 2. **檔案頁面** (`archive.html`)  
- 按月份分組展示**所有**歷史電子報
- 每個月份可摺疊或展開
- 適合尋找**特定月份**的內容

### 3. **搜尋頁面** (`search.html`)
- 即時搜尋標題、完整日期（`YYYY/MM/DD`）與內容
- 使用安全的用戶端 DOM 操作高亮搜尋詞，不將內容寫入 `innerHTML`

---

## 🛠️ 產生方式

上述頁面、報告 HTML 與搜尋 JSON 均由正式建置入口產生：

```bash
BASE_PATH=/ai-newsletter bash scripts/build-html.sh
```

## 📱 樣式與手機支援

- 響應式樣式會在 `768px` 以下調整版面與卡片間距
- 頂部 sticky 導航可在最新、歷史存檔與搜尋頁面間切換
- 導航使用 active 狀態標示目前頁面
