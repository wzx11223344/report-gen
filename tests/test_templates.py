"""
测试模板系统

覆盖:
    - 模板变量替换
    - 循环渲染
    - 条件渲染
    - 预置模板可用性
    - 自定义模板
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reportgen.templates import (
    ReportTemplate,
    TemplateManager,
    TemplateContext,
    TEMPLATE_META,
)


class TestReportTemplate:
    """测试报告模板"""

    def test_render_variable(self):
        """测试变量替换"""
        template = ReportTemplate("test", "Hello, {{ name }}!")
        result = template.render({"name": "World"})
        assert result == "Hello, World!"

    def test_render_for_loop(self):
        """测试循环渲染"""
        template = ReportTemplate(
            "test",
            "{% for item in items %}{{ item }},{% endfor %}",
        )
        result = template.render({"items": ["A", "B", "C"]})
        assert result == "A,B,C,"

    def test_render_if_condition(self):
        """测试条件渲染"""
        template = ReportTemplate(
            "test",
            "{% if show %}SHOW{% else %}HIDE{% endif %}",
        )
        assert template.render({"show": True}) == "SHOW"
        assert template.render({"show": False}) == "HIDE"

    def test_render_nested_context(self):
        """测试嵌套上下文"""
        template = ReportTemplate(
            "test",
            "{{ title }}: {% for row in data %}{{ row.name }}-{{ row.val }},{% endfor %}",
        )
        result = template.render({
            "title": "Report",
            "data": [{"name": "A", "val": 1}, {"name": "B", "val": 2}],
        })
        assert "Report:" in result
        assert "A-1" in result
        assert "B-2" in result

    def test_render_empty_list(self):
        """测试空列表渲染"""
        template = ReportTemplate(
            "test",
            "{% for item in items %}{{ item }}{% endfor %}DONE",
        )
        assert template.render({"items": []}) == "DONE"

    def test_validate_valid(self):
        template = ReportTemplate("test", "Hello {{ name }}")
        assert template.validate() is True

    def test_validate_invalid(self):
        template = ReportTemplate("test", "Hello {{ name ")
        assert template.validate() is False


class TestTemplateManager:
    """测试模板管理器"""

    def test_get_monthly_template(self):
        mgr = TemplateManager()
        tpl = mgr.get_template("monthly", "html")
        assert tpl is not None
        assert tpl.name == "monthly_html"

    def test_get_weekly_template(self):
        mgr = TemplateManager()
        tpl = mgr.get_template("weekly", "html")
        assert tpl is not None

    def test_get_summary_template(self):
        mgr = TemplateManager()
        tpl = mgr.get_template("summary", "html")
        assert tpl is not None

    def test_get_custom_template(self):
        mgr = TemplateManager()
        tpl = mgr.get_template("custom", "html")
        assert tpl is not None

    def test_get_markdown_monthly(self):
        mgr = TemplateManager()
        tpl = mgr.get_template("monthly", "markdown")
        assert tpl is not None

    def test_get_nonexistent_template(self):
        mgr = TemplateManager()
        with pytest.raises(ValueError, match="未知模板"):
            mgr.get_template("nonexistent")

    def test_get_unsupported_format(self):
        mgr = TemplateManager()
        with pytest.raises(ValueError, match="不支持格式"):
            mgr.get_template("custom", "markdown")

    def test_list_templates(self):
        mgr = TemplateManager()
        templates = mgr.list_templates()
        assert len(templates) >= 4
        names = [t["name"] for t in templates]
        assert "monthly" in names
        assert "weekly" in names
        assert "summary" in names
        assert "custom" in names

    def test_add_custom_template(self):
        mgr = TemplateManager()
        tpl = mgr.add_custom_template(
            "my_template",
            "Custom: {{ title }}",
            fmt="html",
        )
        assert tpl is not None
        assert tpl.name == "my_template"
        assert tpl.validate() is True

        # 验证可以获取
        retrieved = mgr.get_template("my_template", "html")
        assert retrieved is tpl


class TestTemplateContext:
    """测试模板上下文"""

    def test_context_defaults(self):
        ctx = TemplateContext()
        assert ctx.title == "报告"
        assert ctx.data == []
        assert ctx.columns == []
        assert ctx.kpi_cards == []
        assert ctx.chart_image is None

    def test_context_to_dict(self):
        ctx = TemplateContext(
            title="测试",
            date="2024年1月",
            generated_at="2024-01-01 12:00:00",
        )
        d = ctx.to_dict()
        assert d["title"] == "测试"
        assert d["date"] == "2024年1月"
        assert d["generated_at"] == "2024-01-01 12:00:00"

    def test_context_with_kpi(self):
        ctx = TemplateContext(
            kpi_cards=[
                {"label": "收入", "value": "100万"},
                {"label": "支出", "value": "60万"},
            ],
        )
        d = ctx.to_dict()
        assert len(d["kpi_cards"]) == 2

    def test_context_with_extra(self):
        ctx = TemplateContext()
        ctx.extra["custom_key"] = "custom_value"
        d = ctx.to_dict()
        assert d["custom_key"] == "custom_value"


class TestTemplateMeta:
    """测试模板元数据"""

    def test_monthly_meta(self):
        assert "monthly" in TEMPLATE_META
        assert TEMPLATE_META["monthly"]["name"] == "月度报告"

    def test_weekly_meta(self):
        assert "weekly" in TEMPLATE_META
        assert TEMPLATE_META["weekly"]["name"] == "周报"

    def test_summary_meta(self):
        assert "summary" in TEMPLATE_META
        assert TEMPLATE_META["summary"]["name"] == "摘要报告"

    def test_custom_meta(self):
        assert "custom" in TEMPLATE_META


class TestTemplateRenderingResult:
    """测试模板渲染结果质量"""

    def test_monthly_html_contains_structure(self):
        mgr = TemplateManager()
        tpl = mgr.get_template("monthly", "html")
        ctx = TemplateContext(
            title="月度经营报告",
            date="2024年",
            generated_at="2024-12-01",
            data=[{"月份": "1月", "收入": 100}],
            columns=["月份", "收入"],
            kpi_cards=[{"label": "总收入", "value": "100万", "change": 5.0}],
            analysis=["分析内容"],
        )
        html = tpl.render(ctx.to_dict())
        assert "月度经营报告" in html
        assert "总收入" in html
        assert "1月" in html
        assert "分析内容" in html
        assert "100万" in html
        assert "环比" in html

    def test_weekly_html_contains_structure(self):
        mgr = TemplateManager()
        tpl = mgr.get_template("weekly", "html")
        ctx = TemplateContext(
            title="周报",
            date="第48周",
            generated_at="2024-11-29",
            data=[{"指标": "活跃用户", "数值": 1500}],
            columns=["指标", "数值"],
            kpi_cards=[{"label": "DAU", "value": "1,500", "trend": 3.2}],
        )
        html = tpl.render(ctx.to_dict())
        assert "周报" in html
        assert "DAU" in html
        assert "活跃用户" in html

    def test_summary_html_contains_structure(self):
        mgr = TemplateManager()
        tpl = mgr.get_template("summary", "html")
        ctx = TemplateContext(
            title="摘要报告",
            date="2024年度",
            generated_at="2024-12-31",
            data=[{"项目": "营收", "金额": 1000}],
            columns=["项目", "金额"],
            metrics=[{"label": "总收入", "value": "1000万"}],
            summary_text=["本年度营收稳步增长。"],
        )
        html = tpl.render(ctx.to_dict())
        assert "摘要报告" in html
        assert "总收入" in html
        assert "本年度营收稳步增长" in html
