# report-gen

**Data-driven report engine** — generate professional PDF / HTML / Excel reports from structured data with a template system.

## Features

- 📊 **Multi-format export** — PDF, HTML, Excel via a unified exporter API
- 🔌 **Pluggable data sources** — CSV, JSON, SQL (via `datasources.py`)
- 🎨 **Template engine** — Jinja2-style templating for report layouts
- ⚙️ **CLI** — `cli.py` for one-command batch generation
- 🧪 **CI ready** — GitHub Actions workflow included

## Install

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from reportgen.engine import ReportEngine
from reportgen.exporters import PDFExporter

engine = ReportEngine(template="quarterly.html", data="data.csv")
engine.render(PDFExporter("output.pdf"))
```

Or via CLI:

```bash
python cli.py --config examples/sample_config.json
```

## Project Structure

```
reportgen/
  datasources.py   # data loaders (csv/json/sql)
  engine.py        # rendering core
  templates.py     # template registry
  exporters.py     # PDF / HTML / Excel writers
examples/          # sample config + data
tests/             # pytest suite
```

## Tests

```bash
pytest tests/
```

## License

MIT
