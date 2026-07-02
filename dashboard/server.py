"""
DataForge Dashboard Server

Lightweight Flask server that serves interactive Chart.js dashboards
from cleaned data stored in DuckDB.
"""

import json
import threading
import webbrowser
import socket
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class DashboardServer:
    """Manages local HTTP server for interactive dashboards."""

    DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataForge Dashboard — {{ table_name }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #e0e0e0; }
        header { background: #16213e; padding: 16px 24px; display: flex; align-items: center; gap: 16px; }
        header h1 { font-size: 1.4rem; color: #4fc3f7; }
        header span { font-size: 0.85rem; color: #90a4ae; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(420px, 1fr)); gap: 20px; padding: 20px; }
        .card { background: #16213e; border-radius: 8px; padding: 20px; border: 1px solid #0f3460; }
        .card h3 { font-size: 0.95rem; color: #4fc3f7; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.05em; }
        .kpi-value { font-size: 2.2rem; font-weight: bold; color: #81d4fa; }
        .kpi-label { font-size: 0.8rem; color: #90a4ae; margin-top: 4px; }
        canvas { max-height: 280px; }
        .footer { text-align: center; padding: 16px; font-size: 0.75rem; color: #546e7a; }
    </style>
</head>
<body>
    <header>
        <h1>DataForge Dashboard</h1>
        <span>Table: <strong>{{ table_name }}</strong> &nbsp;|&nbsp; Generated: {{ generated_at }}</span>
    </header>
    <div class="dashboard" id="dashboard"></div>
    <div class="footer">Powered by DataForge v2.0 — Aaron Ditcher</div>
    <script>
        const charts = {{ charts_json | safe }};
        const dashboard = document.getElementById('dashboard');

        async function fetchData(config) {
            const r = await fetch('/api/data?config=' + encodeURIComponent(JSON.stringify(config)));
            return r.json();
        }

        async function renderCharts() {
            for (const chart of charts) {
                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = '<h3>' + chart.title + '</h3>';

                if (chart.chart_type === 'kpi') {
                    const data = await fetchData(chart);
                    card.innerHTML += '<div class="kpi-value">' + (data.total || 0).toLocaleString() + '</div>';
                    card.innerHTML += '<div class="kpi-label">Total &nbsp;|&nbsp; Avg: ' + (data.average || 0) + ' &nbsp;|&nbsp; Records: ' + (data.count || 0) + '</div>';
                } else {
                    const canvas = document.createElement('canvas');
                    card.appendChild(canvas);
                    const data = await fetchData(chart);
                    new Chart(canvas, {
                        type: chart.chart_type,
                        data: data,
                        options: {
                            responsive: true,
                            plugins: { legend: { labels: { color: '#e0e0e0' } } },
                            scales: chart.chart_type !== 'doughnut' ? {
                                x: { ticks: { color: '#90a4ae' }, grid: { color: '#0f3460' } },
                                y: { ticks: { color: '#90a4ae' }, grid: { color: '#0f3460' } }
                            } : {}
                        }
                    });
                }

                dashboard.appendChild(card);
            }
        }

        renderCharts();
    </script>
</body>
</html>"""

    def __init__(self, duckdb_manager, chart_suggester,
                 template_name: str = 'executive',
                 port: int = 0):
        self.duckdb = duckdb_manager
        self.suggester = chart_suggester
        self.template_name = template_name
        self.port = port
        self.server_thread: Optional[threading.Thread] = None

        try:
            from flask import Flask, jsonify, request, render_template_string
            self.flask = Flask
            self.jsonify = jsonify
            self.request = request
            self.render_template_string = render_template_string
            self._setup_app()
        except ImportError:
            raise ImportError("flask required. Install: pip install flask")

    def _setup_app(self):
        from flask import Flask, jsonify, request, render_template_string

        self.app = Flask(__name__)

        @self.app.route('/')
        def index():
            charts = self.suggester.suggest_charts(4)
            import json as _json
            return render_template_string(
                self.DASHBOARD_HTML,
                charts_json=_json.dumps(charts),
                table_name=self.duckdb.table_name or 'data',
                generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

        @self.app.route('/api/data')
        def get_chart_data():
            config_json = request.args.get('config', '{}')
            try:
                config = json.loads(config_json)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid config'}), 400
            data = self._generate_chart_data(config)
            return jsonify(data)

        @self.app.route('/api/filters/<column_name>')
        def get_filter_values(column_name):
            values = self.duckdb.get_categories(column_name, limit=100)
            return jsonify({'column': column_name, 'values': values})

        @self.app.route('/api/stats/<column_name>')
        def get_column_stats(column_name):
            stats = self.duckdb.get_column_stats(column_name)
            return jsonify(stats)

    def _generate_chart_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        chart_type = config.get('template', 'top_n')
        x_axis = config.get('x_axis', '')
        y_axis = config.get('y_axis', [])

        if chart_type == 'time_series':
            return self._time_series_data(x_axis, y_axis[0] if y_axis else '')
        elif chart_type == 'top_n':
            return self._top_n_data(x_axis, y_axis[0] if y_axis else '', config.get('limit', 10))
        elif chart_type == 'distribution':
            return self._distribution_data(x_axis)
        elif chart_type == 'proportion':
            return self._proportion_data(x_axis, config.get('max_segments', 6))
        elif chart_type == 'kpi_card':
            return self._kpi_data(config.get('metric', ''))
        else:
            return {'labels': [], 'datasets': []}

    def _time_series_data(self, date_col: str, metric_col: str) -> Dict[str, Any]:
        sql = f"""
            SELECT CAST("{date_col}" AS DATE) as period,
                   SUM(TRY_CAST("{metric_col}" AS DOUBLE)) as total
            FROM "{self.duckdb.table_name}"
            WHERE "{date_col}" IS NOT NULL AND "{metric_col}" IS NOT NULL
            GROUP BY CAST("{date_col}" AS DATE)
            ORDER BY period
        """
        try:
            rows = self.duckdb.query(sql)
        except Exception:
            return {'labels': [], 'datasets': []}

        labels = [str(r['period']) for r in rows if r.get('period')]
        values = [r.get('total', 0) for r in rows]

        return {
            'labels': labels,
            'datasets': [{
                'label': metric_col.replace('_', ' ').title(),
                'data': values,
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'fill': True,
                'tension': 0.4,
            }]
        }

    def _top_n_data(self, cat_col: str, metric_col: str, limit: int = 10) -> Dict[str, Any]:
        sql = f"""
            SELECT "{cat_col}" as category,
                   SUM(TRY_CAST("{metric_col}" AS DOUBLE)) as total
            FROM "{self.duckdb.table_name}"
            WHERE "{cat_col}" IS NOT NULL AND "{metric_col}" IS NOT NULL
            GROUP BY category ORDER BY total DESC LIMIT {limit}
        """
        rows = self.duckdb.query(sql)
        labels = [str(r['category']) for r in rows]
        values = [r.get('total', 0) for r in rows]
        colors = ['rgba(54,162,235,0.8)', 'rgba(255,99,132,0.8)', 'rgba(255,206,86,0.8)',
                  'rgba(75,192,192,0.8)', 'rgba(153,102,255,0.8)', 'rgba(255,159,64,0.8)']
        return {'labels': labels, 'datasets': [{'label': metric_col.replace('_', ' ').title(),
                'data': values, 'backgroundColor': colors[:len(values)]}]}

    def _distribution_data(self, metric_col: str) -> Dict[str, Any]:
        sql = f'SELECT TRY_CAST("{metric_col}" AS DOUBLE) as value FROM "{self.duckdb.table_name}" WHERE "{metric_col}" IS NOT NULL ORDER BY value'
        rows = self.duckdb.query(sql)
        values = [r['value'] for r in rows if r.get('value') is not None]
        if not values:
            return {'labels': [], 'datasets': []}
        min_val, max_val = min(values), max(values)
        bins = 10
        bin_width = (max_val - min_val) / bins if max_val != min_val else 1
        counts = [0] * bins
        for v in values:
            idx = min(int((v - min_val) / bin_width), bins - 1)
            counts[idx] += 1
        labels = [f"{min_val + i * bin_width:.1f}-{min_val + (i+1) * bin_width:.1f}" for i in range(bins)]
        return {'labels': labels, 'datasets': [{'label': 'Count', 'data': counts, 'backgroundColor': 'rgba(54,162,235,0.6)'}]}

    def _proportion_data(self, cat_col: str, max_segments: int = 6) -> Dict[str, Any]:
        sql = f'SELECT "{cat_col}" as category, COUNT(*) as count FROM "{self.duckdb.table_name}" WHERE "{cat_col}" IS NOT NULL GROUP BY "{cat_col}" ORDER BY count DESC LIMIT {max_segments}'
        try:
            rows = self.duckdb.query(sql)
        except Exception:
            return {'labels': [], 'datasets': [{'data': [], 'backgroundColor': []}]}
        labels = [str(r['category']) for r in rows]
        values = [r['count'] for r in rows]
        colors = ['rgba(54,162,235,0.8)', 'rgba(255,99,132,0.8)', 'rgba(255,206,86,0.8)',
                  'rgba(75,192,192,0.8)', 'rgba(153,102,255,0.8)', 'rgba(255,159,64,0.8)']
        return {'labels': labels, 'datasets': [{'data': values, 'backgroundColor': colors[:len(values)]}]}

    def _kpi_data(self, metric_col: str) -> Dict[str, Any]:
        sql = f"""
            SELECT COUNT(*) as total_rows,
                   SUM(TRY_CAST("{metric_col}" AS DOUBLE)) as total,
                   AVG(TRY_CAST("{metric_col}" AS DOUBLE)) as average,
                   MIN(TRY_CAST("{metric_col}" AS DOUBLE)) as minimum,
                   MAX(TRY_CAST("{metric_col}" AS DOUBLE)) as maximum
            FROM "{self.duckdb.table_name}" WHERE "{metric_col}" IS NOT NULL
        """
        rows = self.duckdb.query(sql)
        stats = rows[0] if rows else {}
        return {
            'metric': metric_col.replace('_', ' ').title(),
            'total': round(stats.get('total') or 0, 2),
            'average': round(stats.get('average') or 0, 2),
            'minimum': round(stats.get('minimum') or 0, 2),
            'maximum': round(stats.get('maximum') or 0, 2),
            'count': stats.get('total_rows', 0),
        }

    def start(self, open_browser: bool = True) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', 0))
        self.port = sock.getsockname()[1]
        sock.close()

        url = f"http://127.0.0.1:{self.port}"

        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        def run_server():
            self.app.run(host='127.0.0.1', port=self.port, debug=False, threaded=True)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        if open_browser:
            import time
            time.sleep(0.5)
            webbrowser.open(url)

        return url

    def stop(self):
        pass
