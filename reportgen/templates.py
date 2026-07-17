"""
模板系统模块

提供预置模板和 Jinja2 模板引擎，支持：
- 月报 / 周报 / 摘要 / 自定义 四种模板类型
- 变量替换、循环渲染、条件判断
- 内嵌 CSS 样式
"""

import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from jinja2 import Environment, BaseLoader, TemplateNotFound


# ──────────────────────────────────────────────
# 预置模板定义
# ──────────────────────────────────────────────

MONTHLY_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #f0f2f5; padding: 40px 20px; color: #333; }
    .container { max-width: 1100px; margin: 0 auto; }
    .header { background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; padding: 35px 40px; border-radius: 16px; margin-bottom: 28px; }
    .header h1 { font-size: 28px; margin-bottom: 8px; }
    .header .subtitle { opacity: 0.85; font-size: 14px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 28px; }
    .kpi-card { background: #fff; border-radius: 12px; padding: 22px 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .kpi-card .label { font-size: 13px; color: #888; margin-bottom: 6px; }
    .kpi-card .value { font-size: 28px; font-weight: 700; color: #333; }
    .kpi-card .change { font-size: 13px; margin-top: 6px; }
    .kpi-card .change.up { color: #52c41a; }
    .kpi-card .change.down { color: #ff4d4f; }
    .chart-container { background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); text-align: center; }
    .chart-container img { max-width: 100%; height: auto; border-radius: 8px; }
    .chart-container h3 { margin-bottom: 16px; color: #555; }
    table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 28px; }
    th { background: #fafafa; padding: 14px 16px; text-align: left; font-weight: 600; color: #555; font-size: 13px; }
    td { padding: 12px 16px; border-top: 1px solid #f0f0f0; font-size: 14px; }
    tr:hover td { background: #fafbff; }
    .analysis { background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 28px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
    .analysis h3 { margin-bottom: 12px; color: #555; }
    .analysis p { line-height: 1.8; color: #666; }
    .analysis .metric { display: inline-block; background: #f6f8fa; padding: 4px 12px; border-radius: 16px; font-size: 13px; margin: 2px 4px; }
    .footer { text-align: center; font-size: 12px; color: #aaa; padding: 20px 0; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="subtitle">报告期间：{{ date }} &nbsp;|&nbsp; 生成时间：{{ generated_at }}</div>
    </div>

    {% if kpi_cards %}
    <div class="kpi-grid">
        {% for kpi in kpi_cards %}
        <div class="kpi-card">
            <div class="label">{{ kpi.label }}</div>
            <div class="value">{{ kpi.value }}</div>
            {% if kpi.change is defined %}
            <div class="change {% if kpi.change > 0 %}up{% elif kpi.change < 0 %}down{% endif %}">
                环比 {{ "+" if kpi.change > 0 else "" }}{{ "%.1f"|format(kpi.change) }}%
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if chart_image %}
    <div class="chart-container">
        <h3>趋势分析图</h3>
        <img src="data:image/png;base64,{{ chart_image }}" alt="趋势图">
    </div>
    {% endif %}

    <table>
        <thead>
            <tr>
                {% for col in columns %}
                <th>{{ col }}</th>
                {% endfor %}
            </tr>
        </thead>
        <tbody>
            {% for row in data %}
            <tr>
                {% for col in columns %}
                <td>{{ row[col] if row[col] is not none else '-' }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </tbody>
    </table>

    {% if analysis %}
    <div class="analysis">
        <h3>环比分析</h3>
        {% for para in analysis %}
        <p>{{ para }}</p>
        {% endfor %}
    </div>
    {% endif %}

    <div class="footer">
        <p>由 ReportGen 自动生成 | {{ generated_at }}</p>
    </div>
</div>
</body>
</html>"""


WEEKLY_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #f5f7fa; padding: 30px 16px; color: #333; }
    .container { max-width: 1000px; margin: 0 auto; }
    .header { background: linear-gradient(135deg, #1a73e8, #0d47a1); color: #fff; padding: 28px 32px; border-radius: 14px; margin-bottom: 24px; }
    .header h1 { font-size: 24px; margin-bottom: 6px; }
    .header .subtitle { opacity: 0.8; font-size: 13px; }
    .kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .kpi-card { background: #fff; border-radius: 10px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 4px solid #1a73e8; }
    .kpi-card .label { font-size: 12px; color: #999; text-transform: uppercase; margin-bottom: 4px; }
    .kpi-card .value { font-size: 24px; font-weight: 700; color: #222; }
    .kpi-card .trend { font-size: 12px; margin-top: 4px; }
    .kpi-card .trend.up { color: #52c41a; }
    .kpi-card .trend.down { color: #ff4d4f; }
    .section { background: #fff; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .section h3 { font-size: 16px; color: #444; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #e8edf3; }
    .chart-box { text-align: center; margin: 16px 0; }
    .chart-box img { max-width: 100%; border-radius: 8px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { background: #f8f9fa; padding: 10px 12px; text-align: left; font-weight: 600; color: #555; }
    td { padding: 9px 12px; border-top: 1px solid #eee; }
    tr:hover td { background: #f5f8ff; }
    .footer { text-align: center; font-size: 12px; color: #bbb; padding: 16px 0; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="subtitle">周报期间：{{ date }} &nbsp;|&nbsp; {{ generated_at }}</div>
    </div>

    {% if kpi_cards %}
    <div class="kpi-row">
        {% for kpi in kpi_cards %}
        <div class="kpi-card">
            <div class="label">{{ kpi.label }}</div>
            <div class="value">{{ kpi.value }}</div>
            {% if kpi.trend is defined %}
            <div class="trend {% if kpi.trend >= 0 %}up{% else %}down{% endif %}">
                {{ "+" if kpi.trend >= 0 else "" }}{{ "%.1f"|format(kpi.trend) }}%
            </div>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if chart_image %}
    <div class="section">
        <h3>本周趋势图</h3>
        <div class="chart-box">
            <img src="data:image/png;base64,{{ chart_image }}" alt="趋势图">
        </div>
    </div>
    {% endif %}

    <div class="section">
        <h3>详细数据</h3>
        <table>
            <thead>
                <tr>
                    {% for col in columns %}
                    <th>{{ col }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for row in data %}
                <tr>
                    {% for col in columns %}
                    <td>{{ row[col] if row[col] is not none else '-' }}</td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="footer">
        <p>由 ReportGen 自动生成 | {{ generated_at }}</p>
    </div>
</div>
</body>
</html>"""


SUMMARY_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ title }}</title>
<style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #fafbfc; padding: 40px 20px; color: #333; }
    .container { max-width: 800px; margin: 0 auto; }
    .header { text-align: center; padding: 40px 0 30px; }
    .header h1 { font-size: 32px; color: #222; margin-bottom: 8px; }
    .header .date { color: #999; font-size: 14px; }
    .summary-card { background: #fff; border-radius: 16px; padding: 32px; margin-bottom: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
    .summary-card h2 { font-size: 18px; color: #444; margin-bottom: 16px; }
    .metric-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; }
    .metric-item { padding: 16px; background: #f8f9fc; border-radius: 10px; text-align: center; }
    .metric-item .val { font-size: 22px; font-weight: 700; color: #1a73e8; }
    .metric-item .lbl { font-size: 12px; color: #888; margin-top: 4px; }
    .content { line-height: 1.9; color: #555; }
    .content p { margin-bottom: 14px; }
    .footer { text-align: center; font-size: 12px; color: #ccc; padding: 30px 0; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{{ title }}</h1>
        <div class="date">{{ date }} &nbsp;|&nbsp; {{ generated_at }}</div>
    </div>

    {% if metrics %}
    <div class="summary-card">
        <h2>关键指标</h2>
        <div class="metric-list">
            {% for m in metrics %}
            <div class="metric-item">
                <div class="val">{{ m.value }}</div>
                <div class="lbl">{{ m.label }}</div>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <div class="summary-card">
        <h2>报告摘要</h2>
        <div class="content">
            {% if summary_text %}
                {% for para in summary_text %}
                <p>{{ para }}</p>
                {% endfor %}
            {% else %}
                <p>本报告基于 {{ data|length }} 条数据记录生成。</p>
            {% endif %}
        </div>
    </div>

    {% if chart_image %}
    <div class="summary-card" style="text-align:center;">
        <h2>数据概览</h2>
        <img src="data:image/png;base64,{{ chart_image }}" alt="概览图" style="max-width:100%;border-radius:8px;">
    </div>
    {% endif %}

    <div class="footer">
        <p>由 ReportGen 自动生成 | {{ generated_at }}</p>
    </div>
</div>
</body>
</html>"""


CUSTOM_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{{ title }}</title>
<style>
    body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; max-width: 960px; margin: 0 auto; padding: 20px; color: #333; line-height: 1.6; }
    h1 { color: #222; border-bottom: 2px solid #e8e8e8; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; margin: 16px 0; }
    th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }
    th { background: #f5f5f5; font-weight: 600; }
    img { max-width: 100%; }
    .footer { margin-top: 30px; font-size: 12px; color: #aaa; text-align: center; }
</style>
</head>
<body>
    <h1>{{ title }}</h1>
    <p><strong>日期：</strong>{{ date }} &nbsp;|&nbsp; <strong>生成：</strong>{{ generated_at }}</p>

    {% if kpi_cards %}
    <div style="display:flex;gap:16px;flex-wrap:wrap;margin:16px 0;">
        {% for kpi in kpi_cards %}
        <div style="flex:1;min-width:120px;background:#f8f9fc;border-radius:8px;padding:12px 16px;text-align:center;">
            <div style="font-size:12px;color:#888;">{{ kpi.label }}</div>
            <div style="font-size:20px;font-weight:700;color:#333;">{{ kpi.value }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    {% if chart_image %}
    <div style="text-align:center;margin:20px 0;">
        <img src="data:image/png;base64,{{ chart_image }}" alt="Chart">
    </div>
    {% endif %}

    <table>
        <thead><tr>{% for col in columns %}<th>{{ col }}</th>{% endfor %}</tr></thead>
        <tbody>
            {% for row in data %}
            <tr>{% for col in columns %}<td>{{ row[col] if row[col] is not none else '-' }}</td>{% endfor %}</tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="footer">由 ReportGen 自动生成 | {{ generated_at }}</div>
</body>
</html>"""


# Markdown 模板
MONTHLY_MD_TEMPLATE = """# {{ title }}

> 报告期间：{{ date }} | 生成时间：{{ generated_at }}

---

## KPI 摘要

{% if kpi_cards %}
| 指标 | 值 | 环比变化 |
|------|-----|---------|
{% for kpi in kpi_cards %}
| {{ kpi.label }} | {{ kpi.value }} | {% if kpi.change is defined %}{{ "+" if kpi.change > 0 else "" }}{{ "%.1f"|format(kpi.change) }}%{% else %}--{% endif %} |
{% endfor %}
{% endif %}

## 详细数据

| {% for col in columns %}{{ col }} |{% endfor %}
|{% for col in columns %}-|{% endfor %}
{% for row in data %}
| {% for col in columns %}{{ row[col] if row[col] is not none else '-' }} |{% endfor %}
{% endfor %}

{% if analysis %}
## 环比分析

{% for para in analysis %}
- {{ para }}
{% endfor %}
{% endif %}

---

*由 ReportGen 自动生成*
"""

WEEKLY_MD_TEMPLATE = """# {{ title }}

> 周报期间：{{ date }} | {{ generated_at }}

## KPI 卡片

{% if kpi_cards %}
{% for kpi in kpi_cards %}
- **{{ kpi.label }}**: {{ kpi.value }} {% if kpi.trend is defined %}({{ "+" if kpi.trend >= 0 else "" }}{{ "%.1f"|format(kpi.trend) }}%){% endif %}
{% endfor %}
{% endif %}

## 详细数据

| {% for col in columns %}{{ col }} |{% endfor %}
|{% for col in columns %}-|{% endfor %}
{% for row in data %}
| {% for col in columns %}{{ row[col] if row[col] is not none else '-' }} |{% endfor %}
{% endfor %}

---

*由 ReportGen 自动生成*
"""

SUMMARY_MD_TEMPLATE = """# {{ title }}

> {{ date }} | {{ generated_at }}

## 关键指标

{% if metrics %}
| 指标 | 值 |
|------|-----|
{% for m in metrics %}
| {{ m.label }} | {{ m.value }} |
{% endfor %}
{% endif %}

## 报告摘要

{% if summary_text %}
{% for para in summary_text %}
{{ para }}

{% endfor %}
{% else %}
本报告基于 {{ data|length }} 条数据记录生成。
{% endif %}

---

*由 ReportGen 自动生成*
"""


# ──────────────────────────────────────────────
# 模板管理
# ──────────────────────────────────────────────

TEMPLATE_REGISTRY: Dict[str, Dict[str, str]] = {
    "monthly": {
        "html": MONTHLY_TEMPLATE,
        "markdown": MONTHLY_MD_TEMPLATE,
    },
    "weekly": {
        "html": WEEKLY_TEMPLATE,
        "markdown": WEEKLY_MD_TEMPLATE,
    },
    "summary": {
        "html": SUMMARY_TEMPLATE,
        "markdown": SUMMARY_MD_TEMPLATE,
    },
    "custom": {
        "html": CUSTOM_TEMPLATE,
    },
}

TEMPLATE_META: Dict[str, Dict[str, Any]] = {
    "monthly": {
        "name": "月度报告",
        "description": "月报模板 - 表格 + 柱状图 + 环比分析",
        "formats": ["html", "markdown"],
    },
    "weekly": {
        "name": "周报",
        "description": "周报模板 - KPI 卡片 + 趋势图",
        "formats": ["html", "markdown"],
    },
    "summary": {
        "name": "摘要报告",
        "description": "摘要报告 - 关键指标 + 文字总结",
        "formats": ["html", "markdown"],
    },
    "custom": {
        "name": "自定义模板",
        "description": "自定义模板（支持 Jinja2 模板字符串）",
        "formats": ["html"],
    },
}


@dataclass
class TemplateContext:
    """模板渲染上下文"""
    title: str = "报告"
    date: str = ""
    generated_at: str = ""
    data: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    kpi_cards: List[Dict[str, Any]] = field(default_factory=list)
    metrics: List[Dict[str, Any]] = field(default_factory=list)
    analysis: List[str] = field(default_factory=list)
    summary_text: List[str] = field(default_factory=list)
    chart_image: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转为模板渲染用的字典"""
        return {
            "title": self.title,
            "date": self.date,
            "generated_at": self.generated_at,
            "data": self.data,
            "columns": self.columns,
            "kpi_cards": self.kpi_cards,
            "metrics": self.metrics,
            "analysis": self.analysis,
            "summary_text": self.summary_text,
            "chart_image": self.chart_image,
            **self.extra,
        }


class ReportTemplate:
    """报告模板类"""

    def __init__(self, name: str, template_string: str):
        self.name = name
        self.template_string = template_string
        self._env = Environment(
            loader=BaseLoader(),
            autoescape=False,
        )

    def render(self, context: Dict[str, Any]) -> str:
        """
        渲染模板

        Args:
            context: 模板上下文字典

        Returns:
            渲染后的字符串
        """
        try:
            template = self._env.from_string(self.template_string)
            return template.render(**context)
        except Exception as e:
            raise RuntimeError(f"模板渲染失败 ('{self.name}'): {e}")

    def validate(self) -> bool:
        """验证模板语法是否正确"""
        try:
            self._env.from_string(self.template_string)
            return True
        except Exception:
            return False


class TemplateManager:
    """模板管理器"""

    def __init__(self):
        self._registry: Dict[str, Dict[str, ReportTemplate]] = {}
        self._load_presets()

    def _load_presets(self):
        """加载预置模板"""
        for name, formats in TEMPLATE_REGISTRY.items():
            self._registry[name] = {}
            for fmt, tpl_str in formats.items():
                self._registry[name][fmt] = ReportTemplate(f"{name}_{fmt}", tpl_str)

    def get_template(self, name: str, fmt: str = "html") -> ReportTemplate:
        """
        获取模板

        Args:
            name: 模板名称 (monthly / weekly / summary / custom)
            fmt: 输出格式 (html / markdown)

        Returns:
            ReportTemplate 实例

        Raises:
            ValueError: 模板不存在
        """
        # 如果是 custom 模板且传入了模板字符串，动态创建
        if name == "custom" and fmt == "html":
            return self._registry.get("custom", {}).get("html")

        name = name.lower()
        fmt = fmt.lower()

        if name not in self._registry:
            available = list(self._registry.keys())
            raise ValueError(f"未知模板 '{name}'，可用模板: {available}")

        if fmt not in self._registry[name]:
            available = list(self._registry[name].keys())
            raise ValueError(
                f"模板 '{name}' 不支持格式 '{fmt}'，支持格式: {available}"
            )

        return self._registry[name][fmt]

    def add_custom_template(
        self, name: str, template_string: str, fmt: str = "html"
    ) -> ReportTemplate:
        """
        添加自定义模板

        Args:
            name: 模板名称
            template_string: Jinja2 模板字符串
            fmt: 输出格式

        Returns:
            创建的 ReportTemplate 实例
        """
        if name not in self._registry:
            self._registry[name] = {}
        template = ReportTemplate(name, template_string)
        self._registry[name][fmt] = template
        return template

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用模板"""
        result = []
        for name in self._registry:
            meta = TEMPLATE_META.get(name, {})
            formats = list(self._registry[name].keys())
            result.append({
                "name": name,
                "display_name": meta.get("name", name),
                "description": meta.get("description", ""),
                "formats": formats,
            })
        return result
