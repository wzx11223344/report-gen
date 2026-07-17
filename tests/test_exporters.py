"""
测试多格式导出器

覆盖:
    - HTML 导出
    - Markdown 导出
    - JSON 导出
    - Excel 导出（依赖 openpyxl）
    - PDF 导出降级
"""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reportgen.exporters import (
    HTMLExporter,
    MarkdownExporter,
    JSONExporter,
    ExcelExporter,
    PDFExporter,
    ExporterFactory,
)


SAMPLE_HTML = "<html><body><h1>测试报告</h1><p>内容</p></body></html>"
SAMPLE_MD = "# 测试报告\n\n内容\n"
SAMPLE_DATA = [
    {"月份": "1月", "收入": 100, "支出": 60},
    {"月份": "2月", "收入": 150, "支出": 80},
    {"月份": "3月", "收入": 200, "支出": 90},
]


class TestHTMLExporter:
    """测试 HTML 导出"""

    def test_export_html(self):
        exporter = HTMLExporter()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output = f.name
        try:
            result = exporter.export(SAMPLE_HTML, output)
            assert result == output
            assert os.path.exists(output)
            with open(output, "r", encoding="utf-8") as f:
                content = f.read()
            assert "测试报告" in content
            assert "内容" in content  # 应该包含 body 内容
        finally:
            if os.path.exists(output):
                os.unlink(output)


class TestMarkdownExporter:
    """测试 Markdown 导出"""

    def test_export_markdown(self):
        exporter = MarkdownExporter()
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            output = f.name
        try:
            result = exporter.export(SAMPLE_MD, output)
            assert result == output
            assert os.path.exists(output)
            with open(output, "r", encoding="utf-8") as f:
                content = f.read()
            assert "# 测试报告" in content
        finally:
            if os.path.exists(output):
                os.unlink(output)


class TestJSONExporter:
    """测试 JSON 导出"""

    def test_export_json_basic(self):
        exporter = JSONExporter()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output = f.name
        try:
            result = exporter.export(SAMPLE_DATA, output)
            assert result == output
            assert os.path.exists(output)
            with open(output, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert "data" in data
            assert len(data["data"]) == 3
            assert data["data"][0]["月份"] == "1月"
        finally:
            if os.path.exists(output):
                os.unlink(output)

    def test_export_json_with_metadata(self):
        exporter = JSONExporter()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output = f.name
        try:
            metadata = {"title": "测试", "version": 1}
            result = exporter.export(SAMPLE_DATA, output, metadata=metadata)
            with open(output, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["metadata"]["title"] == "测试"
            assert data["metadata"]["version"] == 1
            assert "exported_at" in data
        finally:
            if os.path.exists(output):
                os.unlink(output)


class TestExcelExporter:
    """测试 Excel 导出"""

    def test_export_excel(self):
        exporter = ExcelExporter()
        if not exporter.available:
            pytest.skip("openpyxl 未安装，跳过 Excel 测试")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            output = f.name
        try:
            result = exporter.export(SAMPLE_DATA, output)
            assert result == output
            assert os.path.exists(output)
            # 验证文件是有效的 xlsx
            assert os.path.getsize(output) > 0
        finally:
            if os.path.exists(output):
                os.unlink(output)

    def test_export_excel_empty_data(self):
        exporter = ExcelExporter()
        if not exporter.available:
            pytest.skip("openpyxl 未安装")
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            output = f.name
        try:
            result = exporter.export([], output)
            assert os.path.exists(output)
        finally:
            if os.path.exists(output):
                os.unlink(output)


class TestPDFExporter:
    """测试 PDF 导出"""

    def test_pdf_unavailable_fallback(self):
        """测试 weasyprint 不可用时的降级行为"""
        exporter = PDFExporter()
        if exporter.available:
            pytest.skip("weasyprint 已安装，跳过降级测试")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output = f.name
        try:
            with pytest.warns(UserWarning, match="PDF导出需要安装weasyprint"):
                result = exporter.export(SAMPLE_HTML, output)
            # 应该降级为 HTML
            assert result.endswith(".html")
            assert os.path.exists(result)
            # 清理 HTML 文件
            if os.path.exists(result):
                os.unlink(result)
        finally:
            if os.path.exists(output) and os.path.isfile(output):
                os.unlink(output)

    def test_pdf_available(self):
        """测试 weasyprint 可用时的 PDF 导出"""
        exporter = PDFExporter()
        if not exporter.available:
            pytest.skip("weasyprint 未安装")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            output = f.name
        try:
            result = exporter.export(SAMPLE_HTML, output)
            assert result == output
            assert os.path.exists(output)
            assert os.path.getsize(output) > 0
        finally:
            if os.path.exists(output):
                os.unlink(output)


class TestExporterFactory:
    """测试导出器工厂"""

    def test_create_html(self):
        exporter = ExporterFactory.create("html")
        assert isinstance(exporter, HTMLExporter)

    def test_create_markdown(self):
        exporter = ExporterFactory.create("markdown")
        assert isinstance(exporter, MarkdownExporter)

    def test_create_json(self):
        exporter = ExporterFactory.create("json")
        assert isinstance(exporter, JSONExporter)

    def test_create_pdf(self):
        exporter = ExporterFactory.create("pdf")
        assert isinstance(exporter, PDFExporter)

    def test_create_excel(self):
        exporter = ExporterFactory.create("excel")
        assert isinstance(exporter, ExcelExporter)

    def test_create_invalid_format(self):
        with pytest.raises(ValueError, match="不支持的输出格式"):
            ExporterFactory.create("invalid")

    def test_list_formats(self):
        formats = ExporterFactory.list_formats()
        assert "html" in formats
        assert "pdf" in formats
        assert "excel" in formats
        assert "markdown" in formats
        assert "json" in formats
