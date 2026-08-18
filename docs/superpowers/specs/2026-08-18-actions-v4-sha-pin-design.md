# GitHub Actions v4 SHA Pin Design

日期：2026-08-18
狀態：已核准

## 目標

將 Pages artifact action 升級至 v4，同時維持所有可執行 GitHub Actions 使用不可變的完整 commit SHA，避免放寬現有供應鏈安全測試。

## 變更

- `actions/checkout`：恢復 v4 SHA `11d5960a326750d5838078e36cf38b85af677262`。
- `actions/upload-pages-artifact`：使用 v4 SHA `7b1f4a764d45c48632c6b24a0339c27f5614fb0b`。
- `actions/configure-pages`：恢復 v4 SHA `1f0c5cde4bc74cd7e1254d0cb4de8d49e9068c7d`。
- `actions/deploy-pages`：恢復 v4 SHA `d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e`。
- `r-lib/actions/setup-pandoc`：維持既有 v2 SHA，不變更。
- 每個 SHA 後保留 major version 註解，方便 Dependabot 與人工辨識。

## 驗證

- 確認五個 Action reference 都是 40 字元 SHA。
- 確認新 `upload-pages-artifact` SHA 對應 upstream v4 tag。
- 執行 workflow contract tests 與完整單元測試。
- 不修改測試規則，不提交生成網站產物。
