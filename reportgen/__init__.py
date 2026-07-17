"""
ReportGen - 实战级自动化报告生成系统

多格式报告引擎，支持从数据到 HTML/PDF/Excel/Markdown 报告的自动生成。

核心模块:
    - engine.ReportEngine: 报告生成引擎主类
    - templates.TemplateManager: 模板管理器（月报/周报/摘要/自定义）
    - exporters: 多格式导出器（HTML/PDF/Excel/Markdown/JSON）
    - datasources: 数据源适配器（CSV/JSON/SQLite/Dict）
"""

from .engine import ReportEngine
from .templates import TemplateManager, ReportTemplate, TemplateContext, TEMPLATE_META
from .datasources import (
    DataSource,
    CSVDataSource,
    JSONDataSource,
    SQLiteDataSource,
    DictDataSource,
    create_datasource,
)
from .exporters import ExporterFactory

__version__ = "1.0.0"
__all__ = [
    "ReportEngine",
    "TemplateManager",
    "ReportTemplate",
    "TemplateContext",
    "TEMPLATE_META",
    "DataSource",
    "CSVDataSource",
    "JSONDataSource",
    "SQLiteDataSource",
    "DictDataSource",
    "create_datasource",
    "ExporterFactory",
]
