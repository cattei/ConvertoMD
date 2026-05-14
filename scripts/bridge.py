# -*- coding: utf-8 -*-
"""
MarkItDown 桥接脚本 - 供 Go GUI 调用
支持 DeepSeek 大模型增强、图片提取与描述、保持目录结构、批量转换

用法:
    python bridge.py --source <源目录> --target <目标目录> [--api_key <key>] [--model <model>] [--base_url <url>]

输出格式 (每行一条):
    PROGRESS:<当前>/<总数>
    SUCCESS:<相对路径>
    FAIL:<相对路径>|<错误信息>
    DONE:<成功数>|<失败数>
"""

import os
import re
import sys
import base64
import zipfile
import hashlib
import argparse
from pathlib import Path

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".pdf", ".html", ".htm", ".txt", ".csv", ".tsv",
    ".xml", ".json", ".md", ".rst", ".rtf",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp",
    ".mp3", ".wav", ".m4a", ".ogg",
    ".zip",
}

# 图片 MIME 类型到扩展名映射
MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
    "image/x-emf": ".emf",
    "image/x-wmf": ".wmf",
}


def find_convertible_files(source_dir: Path) -> tuple:
    """递归查找所有可转换的文件，返回 (文件列表, 目录数)"""
    files = []
    dir_count = 0
    for root, dirs, filenames in os.walk(source_dir):
        dir_count += 1
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                files.append(Path(root) / filename)
    return sorted(files), dir_count


def create_markitdown(api_key: str = "", model: str = "", base_url: str = ""):
    """创建 MarkItDown 实例，可选配置大模型"""
    from markitdown import MarkItDown

    llm_client = None
    llm_model = None

    if api_key and model:
        try:
            from openai import OpenAI

            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url

            llm_client = OpenAI(**client_kwargs)
            llm_model = model
        except ImportError:
            print("WARN:openai包未安装，大模型增强功能不可用", file=sys.stderr)
        except Exception as e:
            print(f"WARN:大模型初始化失败: {e}", file=sys.stderr)

    md_kwargs = {"llm_temperature": 0.0}
    if llm_client:
        md_kwargs["llm_client"] = llm_client
        md_kwargs["llm_model"] = llm_model

    return MarkItDown(**md_kwargs)


def extract_images_from_docx(docx_path: Path, images_dir: Path) -> dict:
    """
    从 DOCX 文件中提取所有图片，保存到 images_dir
    返回: {原始文件名: 保存后的相对路径}
    """
    extracted = {}
    if not docx_path.exists() or not zipfile.is_zipfile(docx_path):
        return extracted

    images_dir.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(docx_path, "r") as zf:
            media_files = [f for f in zf.namelist() if f.startswith("word/media/")]
            for media_path in media_files:
                try:
                    data = zf.read(media_path)
                    if len(data) == 0:
                        continue

                    # 根据扩展名确定文件名
                    original_name = os.path.basename(media_path)
                    # 用内容 hash 生成唯一文件名，避免重名
                    content_hash = hashlib.md5(data).hexdigest()[:8]
                    ext = os.path.splitext(original_name)[1].lower()
                    if not ext:
                        # 尝试通过 magic bytes 判断
                        ext = guess_image_ext(data)
                    if not ext:
                        ext = ".png"

                    safe_name = f"img_{content_hash}{ext}"
                    save_path = images_dir / safe_name

                    with open(save_path, "wb") as img_f:
                        img_f.write(data)

                    extracted[original_name] = safe_name
                except Exception:
                    continue
    except Exception:
        pass

    return extracted


def guess_image_ext(data: bytes) -> str:
    """通过 magic bytes 猜测图片扩展名"""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    elif data[:2] == b"\xff\xd8":
        return ".jpg"
    elif data[:4] == b"GIF8":
        return ".gif"
    elif data[:4] == b"BM":
        return ".bmp"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ""


def describe_image_with_ocr(ocr_client, ocr_model: str, image_path: Path) -> str:
    """使用 DeepSeek-OCR 对图片进行 OCR 识别和内容描述"""
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = image_path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".emf": "image/x-emf",
            ".wmf": "image/x-wmf",
        }
        mime_type = mime_map.get(ext, "image/png")

        if mime_type in ("image/x-emf", "image/x-wmf"):
            return "[此图片格式不支持 OCR 识别]"

        response = ocr_client.chat.completions.create(
            model=ocr_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            },
                        },
                        {
                            "type": "text",
                            "text": "<|grounding|>OCR this image. 请用中文识别并描述图片中的所有文字内容，保持原始排版格式。",
                        },
                    ],
                }
            ],
            max_tokens=4096,
            temperature=0.0,
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[图片识别失败: {str(e)}]"


def post_process_markdown(
    markdown_text: str,
    images_dir_name: str,
    extracted_images: dict,
    llm_client=None,
    llm_model: str = "",
) -> str:
    """
    后处理 Markdown 文本：
    1. 替换截断的 base64 data URI 为实际图片文件引用
    2. 如果有大模型，为每张图片添加描述
    """
    if not extracted_images:
        return markdown_text

    # 按文件名长度降序排列，优先匹配更具体的文件名
    sorted_images = sorted(extracted_images.items(), key=lambda x: -len(x[0]))

    # 匹配所有图片语法: ![alt](src) 或 ![](src)
    img_pattern = re.compile(r"(!\[[^\]]*\]\()([^)]+)(\))")

    def replace_img(match):
        prefix = match.group(1)  # ![...](
        src = match.group(2)     # data:image/... 或 URL
        suffix = match.group(3)  # )

        # 只处理 data URI（被截断的或完整的）
        if not src.startswith("data:"):
            return match.group(0)

        # 从 data URI 中提取 MIME 类型
        mime_type = "image/png"
        mime_match = re.match(r"data:(image/[\w+-]+)", src)
        if mime_match:
            mime_type = mime_match.group(1)

        # 查找最匹配的提取图片
        target_ext = MIME_TO_EXT.get(mime_type, ".png")
        best_match = None
        for orig_name, safe_name in sorted_images:
            if orig_name.lower().endswith(target_ext) or target_ext == ".png":
                best_match = safe_name
                break

        if not best_match and sorted_images:
            best_match = sorted_images[0][1]

        if not best_match:
            return match.group(0)

        # 构建相对路径引用
        img_ref = f"{images_dir_name}/{best_match}"

        # 如果有大模型，获取图片描述
        description = ""
        if llm_client and llm_model:
            # 需要找到图片的绝对路径
            # 这里传入的是 images_dir 的父目录上下文中的相对路径
            # 在调用处已处理
            pass  # 描述在外部添加

        return f"{prefix}{img_ref}{suffix}"

    result = img_pattern.sub(replace_img, markdown_text)
    return result


def convert_single_file(
    src_file: Path,
    out_path: Path,
    md_converter,
    ocr_client=None,
    ocr_model: str = "",
) -> str:
    """
    转换单个文件，提取图片并可选添加大模型描述
    返回: "SUCCESS" 或错误信息
    """
    # 确定图片输出目录（与 md 文件同级的 images 子目录）
    images_dir = out_path.parent / "images"
    images_dir_name = "images"

    # 如果是 DOCX，先提取图片
    extracted_images = {}
    if src_file.suffix.lower() == ".docx":
        extracted_images = extract_images_from_docx(src_file, images_dir)

    # 执行 markitdown 转换（启用 keep_data_uris 保留完整 base64 用于匹配）
    result = md_converter.convert(str(src_file), keep_data_uris=True)
    markdown_text = result.text_content

    # 后处理：替换 base64 为实际图片引用
    if extracted_images:
        markdown_text = post_process_markdown(
            markdown_text, images_dir_name, extracted_images
        )

        # 如果有 OCR 模型，为每张图片添加 OCR 文字
        if ocr_client and ocr_model:
            markdown_text = add_image_ocr_text(
                markdown_text, images_dir, images_dir_name, ocr_client, ocr_model
            )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown_text)

    return "SUCCESS"


def add_image_ocr_text(
    markdown_text: str,
    images_dir: Path,
    images_dir_name: str,
    ocr_client,
    ocr_model: str,
) -> str:
    """为 Markdown 中的每张图片添加 OCR 识别文字"""
    img_pattern = re.compile(r"(!\[[^\]]*\]\()([^)]+)(\))")

    def replace_with_ocr(match):
        prefix = match.group(1)
        img_ref = match.group(2)
        suffix = match.group(3)

        # 只处理本地图片引用
        if img_ref.startswith("data:") or img_ref.startswith("http"):
            return match.group(0)

        # 解析图片文件名
        img_filename = os.path.basename(img_ref)
        img_path = images_dir / img_filename

        if not img_path.exists():
            return match.group(0)

        # 调用 OCR 识别
        ocr_text = describe_image_with_ocr(ocr_client, ocr_model, img_path)

        # 在图片引用后添加 OCR 文字
        return f"{prefix}{img_ref}{suffix}\n\n> 📝 **图片文字识别**:\n>\n{ocr_text}\n"

    return img_pattern.sub(replace_with_ocr, markdown_text)


def convert_files(
    source_dir: Path,
    target_dir: Path,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
):
    """批量转换文件，保持目录结构"""
    files, dir_count = find_convertible_files(source_dir)
    total = len(files)

    import json
    stats = {"dirs": dir_count, "files": total}
    print(f"STATS:{json.dumps(stats)}")

    if total == 0:
        print("PROGRESS:0/0")
        print("DONE:0|0|0")
        return

    print(f"PROGRESS:0/{total}")

    md_converter = create_markitdown(api_key, model, base_url)

    ocr_client = None
    if api_key and model:
        try:
            from openai import OpenAI

            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            ocr_client = OpenAI(**client_kwargs)
        except Exception as e:
            print(f"WARN:OCR 模型初始化失败: {e}", file=sys.stderr)

    success_count = 0
    fail_count = 0
    skip_count = 0

    import shutil

    for i, src_file in enumerate(files, 1):
        try:
            rel_path = src_file.relative_to(source_dir)
            
            if src_file.suffix.lower() == ".md":
                out_path = target_dir / rel_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, out_path)
                skip_count += 1
                print(f"SKIP:{rel_path}")
            else:
                out_path = target_dir / rel_path.with_suffix(".md")
                out_path.parent.mkdir(parents=True, exist_ok=True)

                convert_single_file(
                    src_file, out_path, md_converter, ocr_client, model
                )

                success_count += 1
                print(f"SUCCESS:{rel_path}")
        except Exception as e:
            fail_count += 1
            rel_path = src_file.relative_to(source_dir)
            err_msg = str(e).replace("\n", " ").replace("|", "/")
            
            out_path = target_dir / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(src_file, out_path)
                err_msg += " (已复制原文件)"
            except:
                err_msg += " (复制原文件失败)"
            
            print(f"FAIL:{rel_path}|{err_msg}")

        print(f"PROGRESS:{i}/{total}")

    print(f"DONE:{success_count}|{fail_count}|{skip_count}")


def main():
    parser = argparse.ArgumentParser(description="MarkItDown 桥接脚本")
    parser.add_argument("--source", required=True, help="源目录路径")
    parser.add_argument("--target", required=True, help="目标目录路径")
    parser.add_argument("--api_key", default="", help="大模型 API Key")
    parser.add_argument("--model", default="", help="大模型名称")
    parser.add_argument("--base_url", default="", help="大模型 API 地址")
    args = parser.parse_args()

    source_dir = Path(args.source)
    target_dir = Path(args.target)

    if not source_dir.exists():
        print(f"ERROR:源目录不存在: {source_dir}", file=sys.stderr)
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    convert_files(source_dir, target_dir, args.api_key, args.model, args.base_url)


if __name__ == "__main__":
    main()
