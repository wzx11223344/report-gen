"""
报告生成引擎

ReportEngine 管理报告生命周期：数据处理 → 模板渲染 → 图表生成 → 多格式导出。
"""

import base64
import io
import os
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .datasources import DataSource, create_datasource
from .templates import TemplateManager, TemplateContext
from .exporters import ExporterFactory


class ReportEngine:
    """报告生成引擎"""

    def __init__(self):
        self.template_manager = TemplateManager()
        self.exporter_factory = ExporterFactory()

    # ── 数据预处理 ──

    @staticmethod
    def preprocess(
        data: List[Dict[str, Any]],
        sort_by: Optional[str] = None,
        sort_desc: bool = False,
        filter_fn: Optional[callable] = None,
        aggregate: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
     数据预处理：排序、过滤、聚合

        Args:
            data: 原始数据
            sort_by: 排序字段名
            sort_desc: 是否降序
            filter_fn: 过滤函数，接收行字典返回 bool
            aggregate: 聚合配置，如 {"字段": "sum|avg|count|min|max"}

        Returns:
            处理后的数据
        """
        result = data

        # 过滤
        if filter_fn is not None:
            result = [row for row in result if filter_fn(row)]

        # 排序
        if sort_by is not None:
            result = sorted(
                result,
                key=lambda row: _safe_sort_key(row.get(sort_by)),
                reverse=sort_desc,
            )

        # 聚合
        if aggregate is not None:
            aggregated = {}
            for field, method in aggregate.items():
                values = [
                    row.get(field)
                    for row in result
                    if isinstance(row.get(field), (int, float))
                ]
                if not values:
                    aggregated[field] = None
                    continue
                method_lower = method.lower()
                if method_lower == "sum":
                    aggregated[field] = sum(values)
                elif method_lower == "avg" or method_lower == "mean":
                    aggregated[field] = statistics.mean(values)
                elif method_lower == "count":
                    aggregated[field] = len(values)
                elif method_lower == "min":
                    aggregated[field] = min(values)
                elif method_lower == "max":
                    aggregated[field] = max(values)
                else:
                    aggregated[field] = statistics.mean(values)
            return [aggregated]

        return result

    # ── KPI 计算 ──

    @staticmethod
    def compute_kpi_cards(
        data: List[Dict[str, Any]],
        config: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        根据配置计算 KPI 卡片数据

        Args:
            data: 数据行列表
            config: KPI 配置列表，每项含 label / field / method
                    示例: [{"label": "总收入", "field": "amount", "method": "sum"}]

        Returns:
            KPI 卡片列表
        """
        cards = []
        for cfg in config:
            label = cfg.get("label", cfg.get("field", ""))
            field = cfg.get("field")
            method = cfg.get("method", "count")
            values = [
                row.get(field)
                for row in data
                if isinstance(row.get(field), (int, float))
            ]

            if not values:
                cards.append({"label": label, "value": "N/A"})
                continue

            method_lower = method.lower()
            if method_lower == "sum":
                value = sum(values)
            elif method_lower == "avg" or method_lower == "mean":
                value = round(statistics.mean(values), 2)
            elif method_lower == "count":
                value = len(values)
            elif method_lower == "min":
                value = min(values)
            elif method_lower == "max":
                value = max(values)
            elif method_lower == "median":
                value = statistics.median(values)
            else:
                value = round(statistics.mean(values), 2)

            # 数值格式化
            if isinstance(value, float):
                if abs(value) >= 1e8:
                    display = f"{value / 1e8:.2f}亿"
                elif abs(value) >= 1e4:
                    display = f"{value / 1e4:.2f}万"
                else:
                    display = f"{value:,.2f}"
            else:
                display = f"{value:,}"

            cards.append({"label": label, "value": display})
        return cards

    # ── 环比分析 ──

    @staticmethod
    def compute_mom_analysis(data: List[Dict[str, Any]], value_field: str) -> List[str]:
        """
        计算环比分析文本

        Args:
            data: 数据行列表（已排序）
            value_field: 数值字段名

        Returns:
            分析文本列表
        """
        values = [
            row.get(value_field)
            for row in data
            if isinstance(row.get(value_field), (int, float))
        ]

        if len(values) < 2:
            return ["数据不足，无法进行环比分析。"]

        analyses = []
        total = sum(values)
        avg_val = statistics.mean(values)
        max_val = max(values)
        min_val = min(values)

        analyses.append(
            f"本期{value_field}总值 {total:,.2f}，"
            f"平均 {avg_val:,.2f}，"
            f"最高 {max_val:,.2f}，"
            f"最低 {min_val:,.2f}。"
        )

        # 环比变化
        if len(values) >= 2:
            changes = []
            for i in range(1, len(values)):
                prev = values[i - 1]
                curr = values[i]
                if prev != 0:
                    change = (curr - prev) / prev * 100
                    changes.append(change)

            if changes:
                avg_change = statistics.mean(changes)
                if avg_change > 0:
                    analyses.append(
                        f"环比整体呈上升趋势，平均增长 {avg_change:.1f}%。"
                    )
                elif avg_change < 0:
                    analyses.append(
                        f"环比整体呈下降趋势，平均下降 {abs(avg_change):.1f}%。"
                    )
                else:
                    analyses.append("环比整体持平。")

                # 最大波动
                max_change = max(changes, key=abs)
                max_idx = changes.index(max_change) + 1
                direction = "增长" if max_change > 0 else "下降"
                analyses.append(
                    f"第 {max_idx} 期波动最大，环比 {direction} {abs(max_change):.1f}%。"
                )

        return analyses

    # ── 图表生成 ──

    @staticmethod
    def generate_chart(
        data: List[Dict[str, Any]],
        x_field: str,
        y_field: str,
        chart_type: str = "bar",
        title: str = "趋势图",
        figsize: tuple = (8, 4),
    ) -> str:
        """
        使用 matplotlib 生成图表并返回 base64 编码

        Args:
            data: 数据
            x_field: X 轴字段名
            y_field: Y 轴字段名
            chart_type: 图表类型 (bar / line)
            title: 图表标题
            figsize: 图表尺寸

        Returns:
            base64 编码的 PNG 图片字符串
        """
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False

            x_values = [str(row.get(x_field, "")) for row in data]
            y_values = [
                row.get(y_field, 0) if isinstance(row.get(y_field), (int, float)) else 0
                for row in data
            ]

            fig, ax = plt.subplots(figsize=figsize)

            if chart_type == "line":
                ax.plot(x_values, y_values, marker="o", linewidth=2, color="#4472C4")
                ax.fill_between(
                    range(len(x_values)),
                    y_values,
                    alpha=0.1,
                    color="#4472C4",
                )
            else:
                colors = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5"]
                bars = ax.bar(
                    x_values,
                    y_values,
                    color=[colors[i % len(colors)] for i in range(len(x_values))],
                    edgecolor="white",
                    linewidth=0.5,
                )
                # 在柱状图上加数值标签
                for bar, val in zip(bars, y_values):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(y_values) * 0.01,
                        f"{val:,.0f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        color="#666",
                    )

            ax.set_title(title, fontsize=14, pad=12)
            ax.set_xlabel(x_field, fontsize=10)
            ax.set_ylabel(y_field, fontsize=10)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(axis="x", rotation=30)

            # 将图表转为 base64
            buf = io.BytesIO()
            plt.tight_layout()
            fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)
            return base64.b64encode(buf.read()).decode("utf-8")

        except ImportError:
            return ""
        except Exception:
            return ""

    # ── 主生成流程 ──

    def generate(
        self,
        template_name: str,
        data_source: Union[str, List[Dict[str, Any]], DataSource],
        output_path: str,
        fmt: str = "html",
        title: str = "报告",
        date: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_desc: bool = False,
        filter_fn: Optional[callable] = None,
        chart_x: Optional[str] = None,
        chart_y: Optional[str] = None,
        kpi_config: Optional[List[Dict[str, Any]]] = None,
        custom_template: Optional[str] = None,
        **kwargs,
    ) -> str:
        """
        生成报告

        Args:
            template_name: 模板名称
            data_source: 数据源（文件路径 / 字典列表 / DataSource 实例）
            output_path: 输出文件路径
            fmt: 输出格式 (html / pdf / excel / markdown / json)
            title: 报告标题
            date: 报告日期，默认今天
            sort_by: 排序字段
            sort_desc: 是否降序
            filter_fn: 过滤函数
            chart_x: 图表 X 轴字段
            chart_y: 图表 Y 轴字段
            kpi_config: KPI 配置
            custom_template: 自定义模板字符串（当 template_name 为 custom 时使用）
            **kwargs: 额外参数

        Returns:
            输出文件的绝对路径

        Raises:
            ValueError: 参数错误
            RuntimeError: 生成失败
        """
        # ── 1. 加载数据 ──
        if isinstance(data_source, DataSource):
            ds = data_source
        else:
            ds = create_datasource(data_source)

        raw_data = ds.read()
        if not raw_data:
            raise ValueError("数据源为空，无法生成报告")

        # ── 2. 数据预处理 ──
        processed_data = self.preprocess(
            raw_data,
            sort_by=sort_by,
            sort_desc=sort_desc,
            filter_fn=filter_fn,
        )

        # ── 3. 准备上下文 ──
        columns = list(processed_data[0].keys()) if processed_data else []
        now = datetime.now()
        date_str = date or now.strftime("%Y年%m月")
        generated_at = now.strftime("%Y-%m-%d %H:%M:%S")

        ctx = TemplateContext(
            title=title,
            date=date_str,
            generated_at=generated_at,
            data=processed_data,
            columns=columns,
        )

        # ── 4. KPI 卡片 ──
        if kpi_config:
            kpi_cards = self.compute_kpi_cards(raw_data, kpi_config)
            ctx.kpi_cards = kpi_cards
            ctx.metrics = [
                {"label": k["label"], "value": k["value"]} for k in kpi_cards
            ]

        # ── 5. 图表 ──
        if chart_x and chart_y:
            chart_image = self.generate_chart(
                processed_data,
                x_field=chart_x,
                y_field=chart_y,
                title=f"{title} - {chart_y}趋势",
            )
            ctx.chart_image = chart_image

        # ── 6. 分析 ──
        if fmt in ("html", "markdown") and chart_y:
            analysis = self.compute_mom_analysis(processed_data, chart_y)
            ctx.analysis = analysis
            ctx.summary_text = analysis

        # ── 7. 渲染模板 ──
        if fmt == "json":
            # JSON 格式不走模板渲染
            exporter = self.exporter_factory.create("json")
            metadata = {
                "title": title,
                "date": date_str,
                "generated_at": generated_at,
                "template": template_name,
                "row_count": len(processed_data),
            }
            return exporter.export(processed_data, output_path, metadata=metadata)

        # Markdown 格式用 markdown 模板
        template_fmt = "markdown" if fmt == "markdown" else "html"

        if template_name == "custom" and custom_template:
            self.template_manager.add_custom_template(
                "custom", custom_template, fmt=template_fmt
            )

        template = self.template_manager.get_template(template_name, template_fmt)
        rendered = template.render(ctx.to_dict())

        # ── 8. 导出 ──
        if fmt == "html":
            exporter = self.exporter_factory.create("html")
            return exporter.export(rendered, output_path)

        elif fmt == "pdf":
            exporter = self.exporter_factory.create("pdf")
            return exporter.export(rendered, output_path)

        elif fmt == "excel":
            exporter = self.exporter_factory.create("excel")
            return exporter.export(
                processed_data,
                output_path,
                columns=columns,
                title=title,
                chart_image=ctx.chart_image,
            )

        elif fmt == "markdown":
            exporter = self.exporter_factory.create("markdown")
            return exporter.export(rendered, output_path)

        else:
            raise ValueError(f"不支持的输出格式: {fmt}")

    # ── 工具方法 ──

    def validate_data(self, data_source: Union[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        验证数据源并返回摘要

        Args:
            data_source: 数据源

        Returns:
            数据摘要字典
        """
        if isinstance(data_source, DataSource):
            ds = data_source
        else:
            ds = create_datasource(data_source)

        if not ds.validate():
            return {"valid": False, "error": "数据源验证失败"}

        try:
            summary = ds.get_summary()
            summary["valid"] = True
            return summary
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有可用模板"""
        return self.template_manager.list_templates()


def _safe_sort_key(value: Any) -> Any:
    """安全的排序键提取"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.lower()
    return value
