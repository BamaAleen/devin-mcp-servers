#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp", "requests"]
# ///

import asyncio
import json
import os
import time
import requests

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

JOB_URL = os.environ.get(
    "PADDLEOCR_JOB_URL",
    "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs",
)
TOKEN = os.environ.get("PADDLEOCR_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "PADDLEOCR_TOKEN environment variable is required. "
        "Set it in your MCP host config (e.g. mcp_config.json env field)."
    )
MODEL = os.environ.get("PADDLEOCR_MODEL", "PaddleOCR-VL-1.5")

server = Server("paddleocr")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="ocr",
            description=(
                "使用 PaddleOCR 对图片或 PDF 文件进行 OCR 识别，支持本地文件路径和 URL。"
                "返回识别出的 Markdown 格式文本内容。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "本地文件路径（如 C:/path/to/file.pdf）或文件 URL（http/https）",
                    },
                    "save_output": {
                        "type": "boolean",
                        "description": "是否将识别结果保存到本地 output 目录（默认 false）",
                        "default": False,
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "输出目录路径（仅 save_output=true 时有效，默认 ./output）",
                        "default": "./output",
                    },
                },
                "required": ["file_path"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != "ocr":
        raise ValueError(f"Unknown tool: {name}")

    file_path = arguments["file_path"]
    save_output = arguments.get("save_output", False)
    output_dir = arguments.get("output_dir", "./output")

    auth_headers = {"Authorization": f"bearer {TOKEN}"}
    optional_payload = {
        "useDocOrientationClassify": False,
        "useDocUnwarping": False,
        "useChartRecognition": False,
    }

    # ── 提交任务 ──────────────────────────────────────────────
    try:
        if file_path.startswith("http"):
            headers = {**auth_headers, "Content-Type": "application/json"}
            payload = {
                "fileUrl": file_path,
                "model": MODEL,
                "optionalPayload": optional_payload,
            }
            job_response = requests.post(JOB_URL, json=payload, headers=headers)
        else:
            if not os.path.exists(file_path):
                return [TextContent(type="text", text=f"错误：文件不存在 {file_path}")]
            data = {"model": MODEL, "optionalPayload": json.dumps(optional_payload)}
            with open(file_path, "rb") as f:
                job_response = requests.post(
                    JOB_URL, headers=auth_headers, data=data, files={"file": f}
                )
    except Exception as e:
        return [TextContent(type="text", text=f"提交任务失败：{e}")]

    if job_response.status_code != 200:
        return [
            TextContent(
                type="text",
                text=f"提交任务失败（{job_response.status_code}）：{job_response.text}",
            )
        ]

    job_id = job_response.json()["data"]["jobId"]

    # ── 轮询结果 ──────────────────────────────────────────────
    jsonl_url = ""
    for _ in range(120):  # 最多等待 10 分钟
        try:
            result_response = requests.get(f"{JOB_URL}/{job_id}", headers=auth_headers)
            data = result_response.json()["data"]
            state = data["state"]

            if state == "done":
                jsonl_url = data["resultUrl"]["jsonUrl"]
                break
            elif state == "failed":
                error_msg = data.get("errorMsg", "未知错误")
                return [TextContent(type="text", text=f"OCR 任务失败：{error_msg}")]
        except Exception as e:
            return [TextContent(type="text", text=f"轮询结果时出错：{e}")]

        await asyncio.sleep(5)

    if not jsonl_url:
        return [TextContent(type="text", text="OCR 任务超时（超过 10 分钟）")]

    # ── 获取并解析结果 ────────────────────────────────────────
    try:
        jsonl_response = requests.get(jsonl_url)
        jsonl_response.raise_for_status()
    except Exception as e:
        return [TextContent(type="text", text=f"下载结果失败：{e}")]

    lines = jsonl_response.text.strip().split("\n")
    all_markdown = []

    if save_output:
        os.makedirs(output_dir, exist_ok=True)

    page_num = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            result = json.loads(line)["result"]
        except Exception:
            continue

        for res in result.get("layoutParsingResults", []):
            md_text = res["markdown"]["text"]
            all_markdown.append(md_text)

            if save_output:
                md_path = os.path.join(output_dir, f"doc_{page_num}.md")
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_text)

                # 保存内联图片
                for img_path, img_url in res["markdown"].get("images", {}).items():
                    full_path = os.path.join(output_dir, img_path)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    img_bytes = requests.get(img_url).content
                    with open(full_path, "wb") as f:
                        f.write(img_bytes)

                # 保存输出图片
                for img_name, img_url in res.get("outputImages", {}).items():
                    img_resp = requests.get(img_url)
                    if img_resp.status_code == 200:
                        img_file = os.path.join(
                            output_dir, f"{img_name}_{page_num}.jpg"
                        )
                        with open(img_file, "wb") as f:
                            f.write(img_resp.content)

            page_num += 1

    result_text = (
        "\n\n---\n\n".join(all_markdown) if all_markdown else "未识别到任何内容"
    )
    if save_output:
        result_text += f"\n\n（文件已保存至 {os.path.abspath(output_dir)}）"

    return [TextContent(type="text", text=result_text)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
