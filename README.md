# devin-mcp-servers

**公开仓库**，集中存放给云端 Devin 用的 **MCP 服务器脚本**。

> 为什么公开：云端 Devin 的 MCP 运行在隔离沙箱里，通过 `uv run --script <raw URL>` **匿名**拉取脚本，只有公开仓库的 raw 地址才能被拉到。
> **这些脚本均不含任何密钥**（token 一律通过环境变量注入），公开是安全的。

## 目录

- `paddleocr/` — PaddleOCR OCR 服务（提交图片/PDF → 远端识别 → 返回 Markdown）
  - `server.py` — MCP 服务器本体
  - `mcp.config.json` — 注册用的脱敏配置模板
  - `BOOTSTRAP.md` — 在云端 Devin / 换账号时的启用步骤

## 换 Devin 账号后怎么用

打开各子目录的 `BOOTSTRAP.md`，按步骤在新账号的 **Settings → MCP Marketplace → Add Your Own** 里填好即可。脚本本身和 raw URL 不变。

## 规则

- 只放**无密钥**的 MCP 脚本与脱敏模板。
- token / 密钥一律走 **Devin Secrets** 或 MCP 表单的 env，**绝不提交到仓库**。
