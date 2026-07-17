#!/usr/bin/env python3
"""
CLI 入口 - ReportGen 命令行工具

用法:
    python cli.py generate --template monthly --data sales.csv --format html --output report.html
    python cli.py generate --template weekly --data weekly.json --format pdf --output report.pdf
    python cli.py generate --data data.csv --format excel --output report.xlsx
    python cli.py list-templates
    python cli.py validate --data data.csv
    python cli.py schedule --config config.json
"""

import argparse
import json
import os
import sys
import subprocess
from datetime import datetime
from typing import Any, Dict, List, Optional


def ensure_reportgen_importable():
    """确保 reportgen 包可导入"""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)


ensure_reportgen_importable()

from reportgen import ReportEngine


# ──────────────────────────────────────────────
# 命令处理函数
# ──────────────────────────────────────────────

def cmd_generate(args: argparse.Namespace) -> None:
    """处理 generate 命令"""
    engine = ReportEngine()

    # 构建参数
    kwargs: Dict[str, Any] = {
        "template_name": args.template or "monthly",
        "data_source": args.data,
        "output_path": args.output,
        "fmt": args.format,
        "title": args.title,
        "date": args.date,
    }

    # 排序
    if args.sort_by:
        kwargs["sort_by"] = args.sort_by
        kwargs["sort_desc"] = args.sort_desc

    # 图表
    if args.chart_x and args.chart_y:
        kwargs["chart_x"] = args.chart_x
        kwargs["chart_y"] = args.chart_y

    # KPI 配置（从 JSON 文件读取）
    if args.kpi_config:
        with open(args.kpi_config, "r", encoding="utf-8") as f:
            kwargs["kpi_config"] = json.load(f)

    # 自定义模板
    if args.custom_template:
        with open(args.custom_template, "r", encoding="utf-8") as f:
            kwargs["custom_template"] = f.read()

    # 添加额外参数
    if args.extra:
        for extra in args.extra:
            if "=" in extra:
                key, value = extra.split("=", 1)
                kwargs[key] = value

    print(f"▶ 正在生成 {args.format.upper()} 报告...")
    print(f"  模板: {args.template or 'monthly'}")
    print(f"  数据: {args.data}")
    print(f"  输出: {args.output}")

    try:
        output = engine.generate(**kwargs)
        print(f"✓ 报告生成成功！")
        print(f"  输出文件: {os.path.abspath(output)}")
    except Exception as e:
        print(f"✗ 生成失败: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_list_templates(args: argparse.Namespace) -> None:  # noqa: ARG001
    """处理 list-templates 命令"""
    engine = ReportEngine()
    templates = engine.list_templates()

    print(f"可用模板（共 {len(templates)} 个）:\n")
    for tpl in templates:
        formats_str = ", ".join(tpl["formats"])
        print(f"  {tpl['name']:12s}  {tpl['display_name']}")
        print(f"              {tpl['description']}")
        print(f"              支持格式: {formats_str}")
        print()


def cmd_validate(args: argparse.Namespace) -> None:
    """处理 validate 命令"""
    engine = ReportEngine()

    print(f"▶ 验证数据源: {args.data}")
    result = engine.validate_data(args.data)

    if result.get("valid"):
        print(f"✓ 数据源验证通过")
        print(f"  行数: {result.get('row_count', 'N/A')}")
        print(f"  列数: {len(result.get('columns', []))}")
        print(f"  列名: {', '.join(result.get('columns', []))}")
    else:
        print(f"✗ 验证失败: {result.get('error', '未知错误')}", file=sys.stderr)
        sys.exit(1)


def cmd_schedule(args: argparse.Namespace) -> None:
    """处理 schedule 命令 - 定时生成（简化版：使用系统任务计划或 crontab）"""

    if not args.config:
        print("✗ 请指定配置文件路径", file=sys.stderr)
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    print("▶ 配置定时报告生成任务")
    print(f"  配置文件: {os.path.abspath(args.config)}")

    tasks = config.get("tasks", [])

    if not tasks:
        # 兼容单任务配置
        tasks = [config]

    script_path = os.path.abspath(__file__)

    for i, task in enumerate(tasks):
        template = task.get("template", "monthly")
        data_file = task.get("data", "")
        output_dir = task.get("output_dir", "./output")
        fmt = task.get("format", "html")
        schedule_time = task.get("schedule", "0 9 * * 1")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(
            output_dir, f"{template}_{date_str}.{fmt}"
        )

        # 构建命令
        cmd = (
            f'python "{script_path}" generate'
            f' --template {template}'
            f' --data "{data_file}"'
            f' --format {fmt}'
            f' --output "{output_file}"'
        )

        print(f"\n  任务 {i+1}: {template}")
        print(f"    数据: {data_file}")
        print(f"    输出: {output_file}")
        print(f"    调度: {schedule_time}")
        print(f"    命令: {cmd}")

        if args.run_now:
            print(f"    → 立即执行...")
            subprocess.run(cmd, shell=True, check=False)

    # === 跨平台定时任务 ===
    if args.install:
        print(f"\n▶ 安装定时任务（需要管理员权限）...")

        # 构建命令列表
        commands = []
        for i, task in enumerate(tasks):
            template = task.get("template", "monthly")
            data_file = task.get("data", "")
            output_dir = task.get("output_dir", "./output")
            fmt = task.get("format", "html")
            output_file = os.path.join(output_dir, f"{template}_$(date +%Y%m%d).{fmt}")
            commands.append(
                f'cd {os.path.dirname(script_path)} &&'
                f' python cli.py generate'
                f' --template {template} --data "{data_file}"'
                f' --format {fmt} --output "{output_file}"'
            )

        # 为不同平台创建调度
        if sys.platform == "win32":
            _install_windows_schedule(tasks, script_path)
        else:
            _install_crontab(tasks, script_path)

        print("✓ 定时任务安装完成")


def _install_windows_schedule(tasks: List[Dict[str, Any]], script_path: str):
    """Windows 任务计划程序安装"""
    for i, task in enumerate(tasks):
        template = task.get("template", "monthly")
        data_file = task.get("data", "")
        output_dir = os.path.abspath(task.get("output_dir", "./output"))
        fmt = task.get("format", "html")
        schedule_time = task.get("schedule", "0 9 * * 1")
        task_name = f"ReportGen_{template}_{i}"

        # 解析 cron 表达式（简化版）
        parts = schedule_time.split()
        if len(parts) >= 2:
            hour = parts[1]
            minute = parts[0]
            days_of_week = ""
            if len(parts) >= 5:
                dow = parts[4]
                dow_map = {
                    "0": "SUN", "1": "MON", "2": "TUE", "3": "WED",
                    "4": "THU", "5": "FRI", "6": "SAT",
                    "mon": "MON", "tue": "TUE", "wed": "WED",
                    "thu": "THU", "fri": "FRI", "sat": "SAT", "sun": "SUN",
                    "1-5": "MON,TUE,WED,THU,FRI",
                }
                days_of_week = dow_map.get(dow.lower(), dow)
        else:
            hour = "9"
            minute = "0"
            days_of_week = "MON"

        os.makedirs(output_dir, exist_ok=True)

        cmd_parts = [
            f'"python"',
            f'"{script_path}"',
            "generate",
            f'--template {template}',
            f'--data "{data_file}"',
            f'--format {fmt}',
            f'--output "{output_dir}\\{template}_$(Get-Date -Format yyyyMMdd).{fmt}"',
        ]
        command = " ".join(cmd_parts)

        schtask_cmd = (
            f'schtasks /Create /SC WEEKLY /D {days_of_week}'
            f' /TN "{task_name}" /TR "powershell.exe -Command \\"{command}\\""'
            f' /ST {hour.zfill(2)}:{minute.zfill(2)} /F'
        )
        try:
            subprocess.run(schtask_cmd, shell=True, check=True)
            print(f"  → Windows 任务已创建: {task_name}")
        except subprocess.CalledProcessError:
            print(f"  → 创建 Windows 任务失败: {task_name}（可能需要管理员权限）")


def _install_crontab(tasks: List[Dict[str, Any]], script_path: str):
    """Linux/macOS crontab 安装"""
    cron_lines = []
    for i, task in enumerate(tasks):
        template = task.get("template", "monthly")
        data_file = task.get("data", "")
        output_dir = task.get("output_dir", "./output")
        fmt = task.get("format", "html")
        schedule_time = task.get("schedule", "0 9 * * 1")
        output_file = os.path.join(output_dir, f"{template}_$(date +\\%Y\\%m\\%d).{fmt}")
        cron_lines.append(
            f"{schedule_time} cd {os.path.dirname(script_path)}"
            f" && python cli.py generate"
            f" --template {template} --data {data_file}"
            f" --format {fmt} --output {output_file}"
        )

    crontab_content = "\n".join(cron_lines) + "\n"
    # 写入临时文件
    tmpfile = "/tmp/reportgen_crontab"
    with open(tmpfile, "w") as f:
        f.write(crontab_content)
    subprocess.run(f"crontab {tmpfile}", shell=True, check=False)


# ──────────────────────────────────────────────
# 参数解析
# ──────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="reportgen",
        description="ReportGen - 实战级自动化报告生成系统",
        epilog="示例:\n"
        "  python cli.py generate --template monthly --data sales.csv --format html --output report.html\n"
        "  python cli.py list-templates\n"
        "  python cli.py validate --data data.csv\n"
        "  python cli.py schedule --config config.json --run-now",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── generate ──
    gen_parser = subparsers.add_parser("generate", help="生成报告")
    gen_parser.add_argument("--template", "-t", default="monthly",
                            help="模板名称 (monthly/weekly/summary/custom)")
    gen_parser.add_argument("--data", "-d", required=True,
                            help="数据源文件路径 (CSV/JSON)")
    gen_parser.add_argument("--format", "-f", default="html",
                            choices=["html", "pdf", "excel", "markdown", "json"],
                            help="输出格式")
    gen_parser.add_argument("--output", "-o", required=True,
                            help="输出文件路径")
    gen_parser.add_argument("--title", default="报告",
                            help="报告标题")
    gen_parser.add_argument("--date",
                            help="报告日期 (默认今天)")
    gen_parser.add_argument("--sort-by",
                            help="排序字段")
    gen_parser.add_argument("--sort-desc", action="store_true",
                            help="降序排序")
    gen_parser.add_argument("--chart-x",
                            help="图表 X 轴字段")
    gen_parser.add_argument("--chart-y",
                            help="图表 Y 轴字段")
    gen_parser.add_argument("--kpi-config",
                            help="KPI 配置 JSON 文件路径")
    gen_parser.add_argument("--custom-template",
                            help="自定义模板文件路径 (Jinja2)")
    gen_parser.add_argument("--extra", action="append",
                            help="额外参数, 如 key=value")

    # ── list-templates ──
    subparsers.add_parser("list-templates", help="列出可用模板")

    # ── validate ──
    val_parser = subparsers.add_parser("validate", help="验证数据源")
    val_parser.add_argument("--data", "-d", required=True,
                            help="数据源文件路径")

    # ── schedule ──
    sched_parser = subparsers.add_parser("schedule", help="定时生成报告")
    sched_parser.add_argument("--config", "-c", required=True,
                              help="配置文件路径 (JSON)")
    sched_parser.add_argument("--run-now", action="store_true",
                              help="立即执行一次")
    sched_parser.add_argument("--install", action="store_true",
                              help="安装定时任务")

    return parser


def main():
    """CLI 主入口"""
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "list-templates":
        cmd_list_templates(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "schedule":
        cmd_schedule(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
