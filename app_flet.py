# -*- coding: utf-8 -*-
"""
MD转换神器 - 基于 Flet 的文档转换工具
"""

import flet as ft
import threading
import os
import re
import hashlib
import zipfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

API_KEY = "sk-duohvgsidlebysltfcbozhhdfmririmmxalakbzdqwikxaqhq"
MODEL = "deepseek-ai/DeepSeek-OCR"
BASE_URL = "https://api.siliconflow.cn/v1"

SUPPORTED_EXTENSIONS = {
    ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
    ".pdf", ".html", ".htm", ".txt", ".csv", ".tsv",
    ".xml", ".json", ".md", ".rst", ".rtf",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp",
}


class MDConverterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "MD转换神器"
        self.page.window_width = 780
        self.page.window_height = 780
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        self.source_dir = ""
        self.target_dir = ""
        self.is_converting = False
        self.failures = []
        self.stats = {"dirs": "0", "total": "0", "done": "0", "pending": "0"}
        
        self._build_ui()
    
    def _build_ui(self):
        self.page.add(ft.Text("MD转换神器", size=28, weight=ft.FontWeight.BOLD))
        self.page.add(ft.Divider())
        
        self.page.add(ft.Text("📂 源目录（包含待转换文档的目录）", size=14, weight=ft.FontWeight.W_500))
        
        self.source_input = ft.TextField(hint_text="请选择要转换的文档目录...", expand=True, read_only=True)
        row1 = ft.Row([self.source_input, ft.ElevatedButton("选择目录", on_click=self._select_source)])
        self.page.add(row1)
        
        self.page.add(ft.Text("📁 目标目录（Markdown 输出目录）", size=14, weight=ft.FontWeight.W_500))
        
        self.target_input = ft.TextField(hint_text="请选择 Markdown 输出目录...", expand=True, read_only=True)
        row2 = ft.Row([self.target_input, ft.ElevatedButton("选择目录", on_click=self._select_target)])
        self.page.add(row2)
        
        self.page.add(ft.Divider())
        
        self.stat_dirs = ft.Text("📂 目录数: 0", size=14)
        self.stat_total = ft.Text("📄 总文件数: 0", size=14)
        self.stat_done = ft.Text("✅ 已转换: 0", size=14)
        self.stat_pending = ft.Text("⏳ 待转换: 0", size=14)
        
        self.page.add(ft.Row([self.stat_dirs, self.stat_total, self.stat_done, self.stat_pending]))
        
        self.page.add(ft.Container(content=ft.Text("DeepSeek-OCR 已内置 | 图片 OCR 已启用", size=12), bgcolor="#e0e7ff", padding=8))
        
        self.progress_status = ft.Text("就绪", size=13)
        self.progress_bar = ft.ProgressBar(width=700)
        self.page.add(self.progress_status)
        self.page.add(self.progress_bar)
        
        self.page.add(ft.Divider())
        
        self.log_list = ft.ListView(height=180)
        self.page.add(ft.Container(content=self.log_list, padding=10))
        self._add_log("欢迎使用 MarkItDown 文档转换工具")
        
        self.failures_list = ft.ListView(height=120)
        self.failures_section = ft.Column([ft.Text("❌ 转换失败列表", size=13, weight=ft.FontWeight.W_600, color="red"), self.failures_list])
        self.failures_section.visible = False
        self.page.add(self.failures_section)
        
        self.convert_btn = ft.ElevatedButton("🚀 开始转换", on_click=self._start_convert, width=700)
        self.page.add(self.convert_btn)
        
        self.page.add(ft.Divider())
        self.page.add(ft.Text("MD转换神器 · 图片自动提取 + DeepSeek-OCR 文字识别", size=12, color="gray"))
        self.page.add(ft.Row([
            ft.TextButton("代码开源", on_click=lambda _: self.page.launch_url("https://github.com/cattei/ConvertoMD")),
            ft.TextButton("打赏", on_click=self._show_donate),
        ]))
    
    def _add_log(self, text: str, color: str = "black"):
        self.log_list.controls.append(ft.Text(text, size=12, color=color))
        self.page.update()
    
    async def _select_source(self, e):
        result = await self.page.pick_folder_dialog_async()
        if result:
            self.source_dir = result.path
            self.source_input.value = result.path
            if not self.target_dir:
                self.target_dir = result.path + "_md"
                self.target_input.value = self.target_dir
            self.page.update()
    
    async def _select_target(self, e):
        result = await self.page.pick_folder_dialog_async()
        if result:
            self.target_dir = result.path
            self.target_input.value = result.path
            self.page.update()
    
    def _show_donate(self, e):
        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("如果这个工具对你有帮助，欢迎打赏支持！"),
            content=ft.Column([
                ft.Image(src="wechat.jpg", width=250, height=250),
                ft.Text("微信支付", size=13),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[ft.TextButton("关闭", on_click=lambda _: self.page.close_dialog())],
        ))
    
    def _start_convert(self, e):
        if self.is_converting:
            return
        if not self.source_dir:
            self._show_error("请选择源目录")
            return
        if not self.target_dir:
            self._show_error("请选择目标目录")
            return
        
        self.is_converting = True
        self.convert_btn.text = "⏳ 转换中..."
        self.convert_btn.disabled = True
        self.failures = []
        self.failures_section.visible = False
        self.failures_list.controls.clear()
        self.log_list.controls.clear()
        self.stats = {"dirs": "0", "total": "0", "done": "0", "pending": "0"}
        self._update_all_stats()
        self.page.update()
        
        threading.Thread(target=self._convert_thread, daemon=True).start()
    
    def _update_all_stats(self):
        self.stat_dirs.value = f"📂 目录数: {self.stats['dirs']}"
        self.stat_total.value = f"📄 总文件数: {self.stats['total']}"
        self.stat_done.value = f"✅ 已转换: {self.stats['done']}"
        self.stat_pending.value = f"⏳ 待转换: {self.stats['pending']}"
    
    def _convert_thread(self):
        try:
            files, dir_count = self._find_files(Path(self.source_dir))
            total = len(files)
            
            self.stats["dirs"] = str(dir_count)
            self.stats["total"] = str(total)
            self.stats["pending"] = str(total)
            self._update_all_stats_safe()
            
            if total == 0:
                self._add_log_safe("未找到可转换的文件", "orange")
                self._conversion_complete(0, 0, 0)
                return
            
            success_count = 0
            fail_count = 0
            skip_count = 0
            
            for i, src_file in enumerate(files, 1):
                rel_path = src_file.relative_to(self.source_dir)
                
                if src_file.suffix.lower() == ".md":
                    out_path = Path(self.target_dir) / rel_path
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, out_path)
                    skip_count += 1
                    self._add_log_safe(f"⏭️ {rel_path}", "orange")
                else:
                    try:
                        self._convert_file(src_file, Path(self.target_dir) / rel_path.with_suffix(".md"))
                        success_count += 1
                        self._add_log_safe(f"✅ {rel_path}", "green")
                    except Exception as ex:
                        fail_count += 1
                        self.failures.append((str(rel_path), str(ex)))
                        self._copy_failed(src_file, Path(self.target_dir) / rel_path)
                        self._add_log_safe(f"❌ {rel_path}", "red")
                
                pct = int((i / total) * 100)
                self.progress_bar.value = i / total
                self.progress_status.value = f"转换中 {i}/{total} ({pct}%)"
                self.stats["done"] = str(success_count)
                self.stats["pending"] = str(total - i)
                self._update_all_stats_safe()
            
            self._conversion_complete(success_count, fail_count, skip_count)
            
        except Exception as ex:
            self._add_log_safe(f"❌ 转换失败: {ex}", "red")
            self.is_converting = False
            self._reset_btn_safe()
    
    def _conversion_complete(self, success: int, fail: int, skip: int):
        self._add_log_safe(f"🏁 转换完成！成功: {success} | 失败: {fail} | 跳过: {skip}", "purple")
        self.progress_bar.value = 1
        self.progress_status.value = "转换完成"
        
        if fail > 0 and self.failures:
            self.failures_section.visible = True
            for path, reason in self.failures:
                self.failures_list.controls.append(ft.Text(f"{path} - {reason}", size=11, color="red"))
        
        msg = f"转换完成！\n\n成功转换: {success} 个\n"
        if fail > 0:
            msg += f"转换失败: {fail} 个（已复制原文件）\n"
        if skip > 0:
            msg += f"跳过（已复制）: {skip} 个\n"
        if fail + skip > 0:
            msg += f"\n{fail + skip} 个文档已复制到目标目录。"
        
        self._show_complete_safe(msg)
        self.is_converting = False
        self._reset_btn_safe()
    
    def _reset_btn_safe(self):
        def _reset():
            self.convert_btn.text = "🚀 开始转换"
            self.convert_btn.disabled = False
        self._call_safe(_reset)
    
    def _update_all_stats_safe(self):
        self._call_safe(self._update_all_stats)
    
    def _add_log_safe(self, text: str, color: str):
        def _add():
            self.log_list.controls.append(ft.Text(text, size=12, color=color))
            self.page.update()
        self._call_safe(_add)
    
    def _call_safe(self, func):
        def _call():
            func()
            self.page.update()
        self.page.run_task(_call)
    
    def _show_error(self, msg: str):
        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("提示"),
            content=ft.Text(msg),
            actions=[ft.TextButton("确定", on_click=lambda _: self.page.close_dialog())],
        ))
    
    def _show_complete_safe(self, msg: str):
        def _show():
            self.page.show_dialog(ft.AlertDialog(
                modal=True,
                title=ft.Text("转换完成"),
                content=ft.Text(msg),
                actions=[ft.TextButton("确定", on_click=lambda _: self.page.close_dialog())],
            ))
            self.page.update()
        self._call_safe(_show)
    
    def _find_files(self, source_dir: Path) -> Tuple[List[Path], int]:
        files = []
        dir_count = 0
        for root, dirs, filenames in os.walk(source_dir):
            dir_count += 1
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    files.append(Path(root) / filename)
        return sorted(files), dir_count
    
    def _convert_file(self, src_file: Path, out_path: Path):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        images_dir = out_path.parent / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        extracted_images = {}
        if src_file.suffix.lower() == ".docx":
            extracted_images = self._extract_docx_images(src_file, images_dir)
        
        md = self._create_markitdown()
        result = md.convert(str(src_file), keep_data_uris=True)
        markdown_text = result.text_content
        
        if extracted_images:
            markdown_text = self._process_markdown_images(markdown_text, extracted_images)
        
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
    
    def _extract_docx_images(self, docx_path: Path, images_dir: Path) -> Dict[str, str]:
        extracted = {}
        if not zipfile.is_zipfile(docx_path):
            return extracted
        
        try:
            with zipfile.ZipFile(docx_path, "r") as zf:
                for media_path in zf.namelist():
                    if not media_path.startswith("word/media/"):
                        continue
                    try:
                        data = zf.read(media_path)
                        if len(data) == 0:
                            continue
                        
                        content_hash = hashlib.md5(data).hexdigest()[:8]
                        ext = os.path.splitext(media_path)[1].lower() or ".png"
                        safe_name = f"img_{content_hash}{ext}"
                        
                        with open(images_dir / safe_name, "wb") as img_f:
                            img_f.write(data)
                        
                        extracted[os.path.basename(media_path)] = safe_name
                    except:
                        continue
        except:
            pass
        
        return extracted
    
    def _process_markdown_images(self, text: str, images: Dict[str, str]) -> str:
        img_pattern = re.compile(r"(!\[[^\]]*\]\()([^)]+)(\))")
        
        def replace(match):
            prefix = match.group(1)
            src = match.group(2)
            suffix = match.group(3)
            
            if not src.startswith("data:"):
                return match.group(0)
            
            for orig_name, safe_name in sorted(images.items(), key=lambda x: -len(x[0])):
                return f"{prefix}images/{safe_name}{suffix}"
            
            return match.group(0)
        
        return img_pattern.sub(replace, text)
    
    def _create_markitdown(self):
        from markitdown import MarkItDown
        from openai import OpenAI
        
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        return MarkItDown(llm_client=client, llm_model=MODEL, llm_temperature=0.0)
    
    def _copy_failed(self, src: Path, dst: Path):
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(src, dst)
        except:
            pass


def main(page: ft.Page):
    page.theme = ft.Theme(color_scheme_seed="#667eea", font_family="Microsoft YaHei")
    MDConverterApp(page)


ft.run(main, assets_dir="img")
