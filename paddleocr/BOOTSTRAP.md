# 在云端 Devin 使用 / 迁移 PaddleOCR MCP

这是一个 **STDIO 型 MCP 服务器**，本体是单文件 `server.py`（PEP 723 内联依赖，仅需 `mcp` + `requests`）。
它不在本地跑 PaddleOCR，而是把文件/URL 提交给远端托管服务
`https://paddleocr.aistudio-app.com/api/v2/ocr/jobs` 并轮询结果，因此非常适合云端使用（无需 GPU/模型）。

## 在云端 Devin 注册（每个账号一次性手动操作，约 1–2 分钟）

1. 打开 **Settings → MCP Marketplace → Add Your Own**，传输类型选 **STDIO**。
2. 按下表填写（即同目录 `mcp.config.json` 的内容）：

   | 字段 | 值 |
   |---|---|
   | command | `uv` |
   | args | `run`  `--script`  `https://raw.githubusercontent.com/BamaAleen/devin-mcp-servers/main/paddleocr/server.py` |
   | env `PADDLEOCR_TOKEN` | 你的 PaddleOCR token（**不要写进仓库**） |
   | env `PADDLEOCR_MODEL` | `PaddleOCR-VL-1.5` |
   | env `PADDLEOCR_JOB_URL` | `https://paddleocr.aistudio-app.com/api/v2/ocr/jobs` |

3. 点 **Test listing tools**，看到 `ocr` 工具即成功。

## 换一个全新 Devin 账号时

- `server.py` 和本模板已在本仓库，**脚本不用动**，raw URL 不变（仓库是公开的，沙箱可匿名拉取）。
- 在新账号里只需重复上面 3 步（手动），并把 `PADDLEOCR_TOKEN` 填进 env 或存为该账号的 Secret。
- 说明：云端 MCP 没有“自动导入”接口，必须在每个账号手动添加一次；但有本模板可直接复制粘贴。

## 安全提示

- `server.py` 内不含任何密钥（token 一律走环境变量），可放公开仓库。
- token 等敏感值只填进 MCP 表单 / Devin Secrets，**永远不要提交到仓库**。
