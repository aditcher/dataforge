# DataForge v2.0 — Power BI Edition

> **Unified data intake, cleaning, schema generation, and Power BI export platform.**  
> Built by [Aaron Ditcher](https://github.com/aditcher) · [linkedin.com/in/aaronditcher](https://linkedin.com/in/aaronditcher)

![Build](https://github.com/aditcher/dataforge/actions/workflows/build.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What It Does

DataForge takes any Excel or CSV file and runs it through a full data engineering pipeline in seconds — no cloud, no subscription, no SQL server required.

| Stage | What Happens |
|-------|-------------|
| **Ingest** | Load `.xlsx`, `.xls`, or `.csv` — multi-sheet Excel supported |
| **Clean** | Auto-detect and fix nulls, whitespace, date formats, duplicates, company names |
| **Schema** | Infer column types, detect PKs/FKs, generate production DDL |
| **Export** | DDL + DML SQL, staged CSV, Power BI M Code, MERGE SQL, styled Excel workbook |
| **Visualize** | One-click Chart.js dashboard via embedded Flask + DuckDB server |

---

## Features

- **5 SQL Dialects** — Snowflake, SQL Server (T-SQL), MySQL, PostgreSQL, Oracle
- **Automated Data Cleaning** — 6-step pipeline with full audit log
- **Power BI Export** — staged CSV, Power Query M code (`.pq`), MERGE SQL, README
- **Data Dictionary** — auto-generated, exportable as `.xlsx` or `.csv`
- **Column Name Map** — original → SQL-safe clean name mapping
- **Live Dashboard** — auto-suggested Chart.js charts (time series, bar, doughnut, KPI cards) powered by DuckDB
- **Project Save/Load** — persist sessions to `~/.dataforge/`
- **Cross-Platform** — macOS DMG and Windows installer via GitHub Actions

---

## Downloads

| Platform | Download |
|----------|----------|
| macOS (10.14+) | [DataForge-mac.dmg](https://github.com/aditcher/dataforge/releases/latest) |
| Windows (10/11 64-bit) | [DataForge-windows-setup.exe](https://github.com/aditcher/dataforge/releases/latest) |

> **macOS first launch:** Right-click → Open to bypass Gatekeeper.

---

## Run from Source

```bash
git clone https://github.com/aditcher/dataforge.git
cd dataforge
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**Requirements:** Python 3.11+, pip

---

## Project Structure

```
dataforge/
├── main.py                      # Entry point
├── requirements.txt
├── core/
│   ├── schema_engine.py         # Type inference + DDL generation (5 dialects)
│   ├── cleaner.py               # 6-step cleaning pipeline + audit log
│   └── project_manager.py       # Session persistence
├── utils/
│   ├── file_handler.py          # Excel + CSV reader (multi-sheet)
│   └── formatted_exporter.py    # Styled 4-sheet Excel export
├── bi/
│   ├── powerbi_exporter.py      # Full Power BI artifact bundle
│   └── m_code_generator.py      # Power Query M code generator
├── db/
│   └── duckdb_manager.py        # In-memory DuckDB for dashboard queries
├── dashboard/
│   ├── server.py                # Flask + Chart.js dashboard server
│   └── chart_suggester.py       # Auto chart recommendation engine
└── gui/
    └── app.py                   # ttkbootstrap GUI (darkly theme)
```

---

## Power BI Export Bundle

Clicking **Power BI Export** generates a timestamped folder in `~/Downloads/` containing:

| File | Purpose |
|------|---------|
| `{table}_staged.csv` | Cleaned, renamed data — import directly into Power BI |
| `{table}_query.pq` | Power Query M code — paste into Advanced Editor |
| `{table}_merge.sql` | MERGE/UPSERT SQL for target database load |
| `{table}_audit.json` | Full cleaning audit trail |
| `README.md` | Usage instructions |

---

## Dashboard

After generating DDL, click **Launch Dashboard** to open an auto-built Chart.js dashboard in your browser. DataForge analyzes your column types and auto-suggests:

- **Time Series** — date + numeric columns
- **Top N Bar** — categorical + numeric columns  
- **Distribution** — histogram of numeric values
- **Doughnut** — categorical breakdowns
- **KPI Cards** — sum, average, min, max

Powered by an embedded Flask server + DuckDB in-memory query engine. No setup required.

---

## Built With

- [ttkbootstrap](https://ttkbootstrap.readthedocs.io/) — modern tkinter theming
- [DuckDB](https://duckdb.org/) — in-process analytical database
- [Flask](https://flask.palletsprojects.com/) — lightweight dashboard server
- [Chart.js](https://www.chartjs.org/) — interactive browser charts
- [openpyxl](https://openpyxl.readthedocs.io/) — Excel I/O
- [PyInstaller](https://pyinstaller.org/) — cross-platform packaging

---

## Related Projects

- [excel-to-ddl](https://github.com/aditcher/excel-to-ddl) — the foundation this tool builds on
- [plex-trailer-pipeline](https://github.com/aditcher/plex-trailer-pipeline) — YouTube → Plex trailer automation
- [Dashboard Portfolio](https://aditcher.github.io/Dashboard) — interactive BI dashboard portfolio

---

## Author

**Aaron Ditcher** — Senior Data & Analytics Professional  
13+ years across enterprise data, BI, ETL, and SQL across Snowflake, Power BI, Tableau, and more.

[GitHub](https://github.com/aditcher) · [LinkedIn](https://linkedin.com/in/aaronditcher)
