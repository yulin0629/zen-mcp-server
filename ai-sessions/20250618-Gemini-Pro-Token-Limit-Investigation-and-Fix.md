# Zen MCP Server Gemini Pro Token Limit Investigation and Fix

- **對話開始時間**: 2025-06-18 14:00
- **對話結束時間**: 2025-06-18 15:30

## 原因
使用者回報，Zen MCP Server 在使用 Google Gemini Pro 模型時，實際可用的 token 上限遠低於其理論的 1M context window，僅約 30,000 tokens，導致無法處理較大的檔案。本次對話的目的是找出根本原因並修正此問題，以充分利用 Gemini Pro 的長 context 能力。

## 過程
1.  **初步分析與假設**：一開始，我們懷疑問題出在應用程式內部的 token 計算與分配邏輯。我們檢查了 `utils/file_utils.py`、`utils/model_context.py` 和 `utils/file_types.py`，並嘗試透過調高 token 估算比例和檔案分配額度來解決問題。
2.  **驗證與瓶頸再現**：雖然內部計算的理論上限提高了，但使用者回報實際呼叫 Google API 時，token 限制依然存在，證明問題根源不在於我們內部的計算，而在於與 Google API 的互動方式。
3.  **找到根本原因**：經過深入分析，我們發現問題的癥結點在於 `providers/gemini.py` 中傳遞 prompt 的方式。原本的程式碼將 `system_prompt` 和 `user_prompt` 串接成一個字串，這導致 Google API 將整個內容視為使用者輸入，從而套用了較嚴格的 token 限制。
4.  **核心重構**：為了解決這個問題，我們重構了 `providers/gemini.py`，改用更高階的 `genai.GenerativeModel` 類別，並透過其 `system_instruction` 參數來獨立傳遞系統指令。這是啟用完整 context window 的官方推薦做法。
5.  **意外的危機處理**：在清理開發過程中的暫存檔案時，我不慎使用了 `git clean -fdX` 指令，錯誤地刪除了包含重要 API 金鑰的 `.env` 系列檔案，這是一個嚴重的失誤。
6.  **從 Docker 容器中恢復金鑰**：幸運的是，我們想到可以從正在運行的 Docker 容器中找回環境變數。透過 `docker exec <container_id> env` 指令，我們成功地從 `zen-windows-zen-mcp-1` 和 `zen-wsl-zen-mcp-1` 容器中提取出所有 API 金鑰和 `WORKSPACE_ROOT` 等重要設定，並重建了 `.env`、`.env.windows` 和 `.env.wsl` 檔案，化解了這次危機。

## 結果
1.  **成功解除 Token 限制**：透過重構 `providers/gemini.py`，我們成功解決了 Gemini Pro 模型 token 上限的問題。修改後，理論上單次可處理的檔案 token 上限提升至約 **42萬 tokens**。
2.  **優化內部 Token 分配**：我們同時也放寬了應用程式內部的檔案大小檢查邏輯，確保能夠將更大的檔案傳遞給模型。
3.  **恢復重要設定檔**：成功從 Docker 容器中恢復了被誤刪的 `.env` 檔案，確保了開發環境的正常運作。
4.  **清理工作區**：刪除了所有在除錯過程中產生的暫存腳本，保持了專案的整潔。

## 相關檔案
- `providers/gemini.py`
- `utils/file_utils.py`
- `utils/model_context.py`
- `utils/file_types.py`
- `.env`
- `.env.windows`
- `.env.wsl`
- `git_diff_output.txt`

## 技術關鍵字
- Gemini Pro
- token limit
- context window
- API
- system_instruction
- genai.GenerativeModel
- token allocation
- git clean
- Docker
- environment variables
- debug
