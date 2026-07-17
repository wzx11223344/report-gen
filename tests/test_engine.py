"""
测试报告生成引擎

覆盖:
    - ReportEngine 初始化
    - 数据预处理（排序/过滤/聚合）
    - KPI 卡片计算
    - 环比分析
    - 图表生成
    - 完整报告生成流程
"""

import os
import sys
import tempfile

import pytest

# 确保 reportgen 可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reportgen import ReportEngine


SAMPLE_DATA = [
    {"月份": "2024-01", "收入": 120000, "支出": 85000, "利润": 35000, "用户数": 1520},
    {"月份": "2024-02", "收入": 135000, "支出": 82000, "利润": 53000, "用户数": 1680},
    {"月份": "2024-03", "收入": 142000, "支出": 90000, "利润": 52000, "用户数": 1750},
    {"月份": "2024-04", "收入": 158000, "支出": 88000, "利润": 70000, "用户数": 1890},
    {"月份": "2024-05", "收入": 165000, "支出": 92000, "利润": 73000, "用户数": 2010},
    {"月份": "2024-06", "收入": 180000, "支出": 95000, "利润": 85000, "用户数": 2150},
    {"月份": "2024-07", "收入": 175000, "支出": 98000, "利润": 77000, "用户数": 2230},
    {"月份": "2024-08", "收入": 190000, "支出": 100000, "利润": 90000, "用户数": 2380},
    {"月份": "2024-09", "收入": 210000, "支出": 105000, "利润": 105000, "用户数": 2560},
    {"月份": "2024-10", "收入": 225000, "支出": 110000, "利润": 115000, "用户数": 2700},
    {"月份": "2024-11", "收入": 240000, "支出": 115000, "利润": 125000, "用户数": 2850},
    {"月份": "2024-12", "收入": 260000, "支出": 120000, "利润": 140000, "用户数": 3100},
]


class TestEngineInitialization:
    """测试引擎初始化"""

    def test_engine_create(self):
        engine = ReportEngine()
        assert engine is not None
        assert engine.template_manager is not None
        assert engine.exporter_factory is not None

    def test_list_templates(self):
        engine = ReportEngine()
        templates = engine.list_templates()
        assert len(templates) >= 4
        names = [t["name"] for t in templates]
        assert "monthly" in names
        assert "weekly" in names
        assert "summary" in names
        assert "custom" in names


class TestDataPreprocessing:
    """测试数据预处理"""

    def test_sort_ascending(self):
        result = ReportEngine.preprocess(SAMPLE_DATA, sort_by="收入")
        assert result[0]["月份"] == "2024-01"
        assert result[-1]["月份"] == "2024-12"

    def test_sort_descending(self):
        result = ReportEngine.preprocess(SAMPLE_DATA, sort_by="收入", sort_desc=True)
        assert result[0]["月份"] == "2024-12"
        assert result[-1]["月份"] == "2024-01"

    def test_filter(self):
        result = ReportEngine.preprocess(
            SAMPLE_DATA, filter_fn=lambda r: r["收入"] > 200000
        )
        assert len(result) == 4
        for row in result:
            assert row["收入"] > 180000

    def test_aggregate_sum(self):
        result = ReportEngine.preprocess(SAMPLE_DATA, aggregate={"收入": "sum"})
        assert len(result) == 1
        assert result[0]["收入"] == sum(r["收入"] for r in SAMPLE_DATA)

    def test_aggregate_avg(self):
        result = ReportEngine.preprocess(SAMPLE_DATA, aggregate={"收入": "avg"})
        assert len(result) == 1
        import statistics
        expected = statistics.mean([r["收入"] for r in SAMPLE_DATA])
        assert abs(result[0]["收入"] - expected) < 0.01

    def test_aggregate_min_max(self):
        result = ReportEngine.preprocess(SAMPLE_DATA, aggregate={"收入": "min"})
        assert result[0]["收入"] == 120000

        result = ReportEngine.preprocess(SAMPLE_DATA, aggregate={"收入": "max"})
        assert result[0]["收入"] == 260000


class TestKPIComputation:
    """测试 KPI 计算"""

    def test_kpi_sum(self):
        cards = ReportEngine.compute_kpi_cards(
            SAMPLE_DATA,
            [{"label": "总收入", "field": "收入", "method": "sum"}],
        )
        assert cards[0]["label"] == "总收入"
        assert "万" in cards[0]["value"] or "," in cards[0]["value"]

    def test_kpi_avg(self):
        cards = ReportEngine.compute_kpi_cards(
            SAMPLE_DATA,
            [{"label": "平均收入", "field": "收入", "method": "avg"}],
        )
        assert cards[0]["label"] == "平均收入"

    def test_kpi_count(self):
        cards = ReportEngine.compute_kpi_cards(
            SAMPLE_DATA,
            [{"label": "记录数", "field": "收入", "method": "count"}],
        )
        assert cards[0]["label"] == "记录数"
        assert cards[0]["value"] == "12"

    def test_multiple_kpis(self):
        cards = ReportEngine.compute_kpi_cards(
            SAMPLE_DATA,
            [
                {"label": "总收入", "field": "收入", "method": "sum"},
                {"label": "总支出", "field": "支出", "method": "sum"},
                {"label": "总利润", "field": "利润", "method": "sum"},
                {"label": "平均用户数", "field": "用户数", "method": "avg"},
            ],
        )
        assert len(cards) == 4


class TestMoMAnalysis:
    """测试环比分析"""

    def test_mom_with_sufficient_data(self):
        analysis = ReportEngine.compute_mom_analysis(SAMPLE_DATA, "收入")
        assert len(analysis) >= 2

    def test_mom_with_insufficient_data(self):
        analysis = ReportEngine.compute_mom_analysis(
            [{"收入": 100}], "收入"
        )
        assert "数据不足" in analysis[0]

    def test_mom_second_period_larger(self):
        data = [
            {"月份": "1月", "收入": 100},
            {"月份": "2月", "收入": 200},
            {"月份": "3月", "收入": 150},
        ]
        analysis = ReportEngine.compute_mom_analysis(data, "收入")
        assert any("增长" in line or "下降" in line for line in analysis)


class TestChartGeneration:
    """测试图表生成"""

    def test_generate_bar_chart(self):
        chart = ReportEngine.generate_chart(
            SAMPLE_DATA[:6],
            x_field="月份",
            y_field="收入",
            chart_type="bar",
        )
        # 验证返回的是有效的 base64 字符串
        assert chart
        assert isinstance(chart, str)
        assert len(chart) > 100  # base64 图片数据应该较长

    def test_generate_line_chart(self):
        chart = ReportEngine.generate_chart(
            SAMPLE_DATA[:6],
            x_field="月份",
            y_field="收入",
            chart_type="line",
        )
        assert chart
        assert isinstance(chart, str)


class TestFullReportGeneration:
    """测试完整报告生成"""

    def test_generate_html_report(self):
        engine = ReportEngine()
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            output = f.name

        try:
            result = engine.generate(
                template_name="monthly",
                data_source=SAMPLE_DATA,
                output_path=output,
                fmt="html",
                title="测试月报",
                chart_x="月份",
                chart_y="收入",
                kpi_config=[
                    {"label": "总收入", "field": "收入", "method": "sum"},
                    {"label": "总支出", "field": "支出", "method": "sum"},
                ],
            )
            assert result == output
            assert os.path.exists(output)
            with open(output, "r", encoding="utf-8") as f:
                content = f.read()
            assert "测试月报" in content
            assert "总收入" in content
        finally:
            if os.path.exists(output):
                os.unlink(output)

    def test_generate_markdown_report(self):
        engine = ReportEngine()
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            output = f.name

        try:
            result = engine.generate(
                template_name="weekly",
                data_source=SAMPLE_DATA,
                output_path=output,
                fmt="markdown",
                title="测试周报",
            )
            assert result == output
            assert os.path.exists(output)
            with open(output, "r", encoding="utf-8") as f:
                content = f.read()
            assert "测试周报" in content
        finally:
            if os.path.exists(output):
                os.unlink(output)

    def test_generate_json_report(self):
        engine = ReportEngine()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output = f.name

        try:
            result = engine.generate(
                template_name="monthly",
                data_source=SAMPLE_DATA,
                output_path=output,
                fmt="json",
                title="测试 JSON 报告",
            )
            assert result == output
            assert os.path.exists(output)
            import json
            with open(output, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert "data" in data
            assert "metadata" in data
            assert data["metadata"]["title"] == "测试 JSON 报告"
        finally:
            if os.path.exists(output):
                os.unlink(output)
