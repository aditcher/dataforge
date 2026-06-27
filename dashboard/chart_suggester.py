"""
DataForge Chart Suggester

Analyzes cleaned data and suggests optimal chart configurations.
Maps column types to appropriate Chart.js chart types.
"""

from typing import List, Dict, Any, Tuple, Optional
from collections import Counter


class ChartSuggester:
    """Auto-suggests charts based on data column types and content."""

    def __init__(self, schema_columns: List[Dict[str, Any]]):
        self.schema_columns = schema_columns
        self.column_roles = self._classify_columns()

    def _classify_columns(self) -> Dict[str, List[str]]:
        roles = {
            'date': [],
            'datetime': [],
            'categorical': [],
            'numeric': [],
            'boolean': [],
            'text': [],
        }

        for col in self.schema_columns:
            inferred = col['inferred_type']
            name = col['clean_name']

            if inferred == 'date':
                roles['date'].append(name)
            elif inferred == 'datetime':
                roles['datetime'].append(name)
            elif inferred in ['integer', 'float', 'decimal']:
                if not col['is_pk_candidate']:
                    roles['numeric'].append(name)
            elif inferred == 'boolean':
                roles['boolean'].append(name)
            elif inferred in ['varchar_short', 'varchar', 'text']:
                if col['unique_count'] <= 20 and col['total_values'] > 0:
                    roles['categorical'].append(name)
                else:
                    roles['text'].append(name)
            else:
                roles['text'].append(name)

        return roles

    def suggest_charts(self, max_suggestions: int = 4) -> List[Dict[str, Any]]:
        suggestions = []
        used_columns = set()

        # Priority 1: Time series
        if self.column_roles['date'] and self.column_roles['numeric']:
            date_col = self.column_roles['date'][0]
            metric_col = self.column_roles['numeric'][0]
            suggestions.append({
                'template': 'time_series',
                'title': f'{metric_col.replace("_", " ").title()} Over Time',
                'x_axis': date_col,
                'y_axis': [metric_col],
                'chart_type': 'line',
                'fill': False,
                'tension': 0.4,
            })
            used_columns.update([date_col, metric_col])

        # Priority 2: Top N ranking
        cat_cols = [c for c in self.column_roles['categorical'] if c not in used_columns]
        num_cols = [c for c in self.column_roles['numeric'] if c not in used_columns]

        if cat_cols and num_cols:
            cat_col = cat_cols[0]
            metric_col = num_cols[0]
            suggestions.append({
                'template': 'top_n',
                'title': f'{metric_col.replace("_", " ").title()} by {cat_col.replace("_", " ").title()}',
                'x_axis': cat_col,
                'y_axis': [metric_col],
                'chart_type': 'bar',
                'index_axis': 'y',
                'limit': 10,
            })
            used_columns.update([cat_col, metric_col])

        # Priority 3: Distribution
        remaining_nums = [c for c in self.column_roles['numeric'] if c not in used_columns]
        if remaining_nums:
            metric_col = remaining_nums[0]
            suggestions.append({
                'template': 'distribution',
                'title': f'{metric_col.replace("_", " ").title()} Distribution',
                'x_axis': metric_col,
                'y_axis': ['count'],
                'chart_type': 'bar',
                'histogram': True,
            })
            used_columns.add(metric_col)

        # Priority 4: Proportion
        remaining_cats = [c for c in self.column_roles['categorical'] if c not in used_columns]
        if remaining_cats:
            cat_col = remaining_cats[0]
            suggestions.append({
                'template': 'proportion',
                'title': f'{cat_col.replace("_", " ").title()} Breakdown',
                'x_axis': cat_col,
                'y_axis': ['count'],
                'chart_type': 'doughnut',
                'max_segments': 6,
            })

        # Priority 5: KPI cards
        all_nums = self.column_roles['numeric']
        if all_nums and len(suggestions) < max_suggestions:
            for num_col in all_nums[:2]:
                suggestions.append({
                    'template': 'kpi_card',
                    'title': num_col.replace('_', ' ').title(),
                    'metric': num_col,
                    'chart_type': 'kpi',
                })

        return suggestions[:max_suggestions]

    def get_filterable_columns(self) -> List[Dict[str, str]]:
        filters = []
        for col in self.schema_columns:
            inferred = col['inferred_type']
            name = col['clean_name']
            if inferred in ['date', 'datetime']:
                filters.append({'name': name, 'type': 'date_range'})
            elif inferred == 'boolean':
                filters.append({'name': name, 'type': 'toggle'})
            elif col['unique_count'] <= 50:
                filters.append({'name': name, 'type': 'dropdown'})
        return filters
