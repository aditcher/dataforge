"""
DataForge Schema Engine

Ingests Excel/CSV files, infers column types, and generates
production-ready DDL across 5 SQL dialects.

Built on the foundation of excel-to-ddl v1.1.0.
"""

import re
import csv
import io
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from collections import Counter


class SchemaEngine:
    """
    Analyzes tabular data and generates schema definitions.

    Supports 5 SQL dialects:
    - snowflake
    - sqlserver (T-SQL)
    - mysql
    - postgresql
    - oracle
    """

    DIALECTS = {
        'snowflake': {
            'integer': 'INTEGER',
            'float': 'FLOAT',
            'decimal': 'DECIMAL(18,4)',
            'boolean': 'BOOLEAN',
            'date': 'DATE',
            'datetime': 'TIMESTAMP_NTZ',
            'varchar_short': 'VARCHAR(50)',
            'varchar': 'VARCHAR(255)',
            'text': 'VARCHAR(16777216)',
            'variant': 'VARIANT',
        },
        'sqlserver': {
            'integer': 'INT',
            'float': 'FLOAT',
            'decimal': 'DECIMAL(18,4)',
            'boolean': 'BIT',
            'date': 'DATE',
            'datetime': 'DATETIME2',
            'varchar_short': 'NVARCHAR(50)',
            'varchar': 'NVARCHAR(255)',
            'text': 'NVARCHAR(MAX)',
            'variant': 'NVARCHAR(MAX)',
        },
        'mysql': {
            'integer': 'INT',
            'float': 'FLOAT',
            'decimal': 'DECIMAL(18,4)',
            'boolean': 'TINYINT(1)',
            'date': 'DATE',
            'datetime': 'DATETIME',
            'varchar_short': 'VARCHAR(50)',
            'varchar': 'VARCHAR(255)',
            'text': 'LONGTEXT',
            'variant': 'JSON',
        },
        'postgresql': {
            'integer': 'INTEGER',
            'float': 'DOUBLE PRECISION',
            'decimal': 'NUMERIC(18,4)',
            'boolean': 'BOOLEAN',
            'date': 'DATE',
            'datetime': 'TIMESTAMP',
            'varchar_short': 'VARCHAR(50)',
            'varchar': 'VARCHAR(255)',
            'text': 'TEXT',
            'variant': 'JSONB',
        },
        'oracle': {
            'integer': 'NUMBER(10)',
            'float': 'BINARY_FLOAT',
            'decimal': 'NUMBER(18,4)',
            'boolean': 'NUMBER(1)',
            'date': 'DATE',
            'datetime': 'TIMESTAMP',
            'varchar_short': 'VARCHAR2(50)',
            'varchar': 'VARCHAR2(255)',
            'text': 'CLOB',
            'variant': 'CLOB',
        },
    }

    DATE_PATTERNS = [
        (r'^\d{4}-\d{2}-\d{2}$', '%Y-%m-%d', 'date'),
        (r'^\d{2}/\d{2}/\d{4}$', '%m/%d/%Y', 'date'),
        (r'^\d{2}\.\d{2}\.\d{4}$', '%d.%m.%Y', 'date'),
        (r'^\d{2}/\d{2}/\d{2}$', '%m/%d/%y', 'date'),
        (r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', '%Y-%m-%d %H:%M', 'datetime'),
        (r'^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$', '%m/%d/%Y %H:%M', 'datetime'),
        (r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$', '%Y-%m-%dT%H:%M:%S', 'datetime'),
    ]

    BOOL_TRUE = {'true', 'yes', '1', 't', 'y'}
    BOOL_FALSE = {'false', 'no', '0', 'f', 'n'}

    def __init__(self, dialect: str = 'snowflake'):
        if dialect not in self.DIALECTS:
            raise ValueError(f"Unsupported dialect: {dialect}. Use: {list(self.DIALECTS.keys())}")
        self.dialect = dialect
        self.type_map = self.DIALECTS[dialect]
        self.columns: List[Dict[str, Any]] = []
        self.row_count = 0
        self.column_count = 0

    def analyze(self, headers: List[str], rows: List[List[Any]]) -> 'SchemaEngine':
        self.row_count = len(rows)
        self.column_count = len(headers)
        self.columns = []

        for col_idx, header in enumerate(headers):
            col_data = [str(row[col_idx]) if row[col_idx] is not None else ''
                        for row in rows if col_idx < len(row)]
            col_info = self._analyze_column(header, col_data)
            self.columns.append(col_info)

        return self

    def _analyze_column(self, header: str, values: List[str]) -> Dict[str, Any]:
        clean_name = self._clean_column_name(header)
        non_empty = [v.strip() for v in values if v.strip()]
        total = len(values)
        non_empty_count = len(non_empty)
        null_count = total - non_empty_count
        null_pct = (null_count / total * 100) if total > 0 else 0

        inferred_type, type_details = self._infer_type(non_empty)
        is_pk_candidate = self._is_pk_candidate(clean_name, non_empty)
        is_fk_hint = self._is_fk_hint(clean_name)
        type_diversity = self._count_type_diversity(non_empty)
        is_mixed = type_diversity >= 3 and len(non_empty) > 10

        if is_mixed:
            inferred_type = 'variant'

        return {
            'original_name': header,
            'clean_name': clean_name,
            'inferred_type': inferred_type,
            'sql_type': self.type_map.get(inferred_type, self.type_map['text']),
            'total_values': total,
            'null_count': null_count,
            'null_pct': round(null_pct, 2),
            'unique_count': len(set(non_empty)),
            'is_pk_candidate': is_pk_candidate,
            'is_fk_hint': is_fk_hint,
            'is_mixed': is_mixed,
            'type_diversity': type_diversity,
            'max_length': max(len(v) for v in non_empty) if non_empty else 0,
            'sample_values': non_empty[:5] if non_empty else [],
        }

    def _clean_column_name(self, name: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        clean = re.sub(r'_+', '_', clean)
        clean = clean.strip('_').lower()
        if not clean or clean[0].isdigit():
            clean = 'col_' + clean
        return clean

    def _infer_type(self, values: List[str]) -> Tuple[str, Dict]:
        if not values:
            return 'varchar', {}

        bool_count = sum(1 for v in values if v.lower() in self.BOOL_TRUE or v.lower() in self.BOOL_FALSE)
        if bool_count == len(values):
            return 'boolean', {'domain': ['true', 'false']}

        int_count = 0
        for v in values:
            try:
                int(v.replace(',', ''))
                int_count += 1
            except ValueError:
                pass

        if int_count == len(values):
            return 'integer', {'min': min(int(v.replace(',', '')) for v in values),
                               'max': max(int(v.replace(',', '')) for v in values)}

        float_count = 0
        for v in values:
            try:
                float(v.replace(',', '').replace('$', ''))
                float_count += 1
            except ValueError:
                pass

        if float_count == len(values):
            all_int = all(float(v.replace(',', '').replace('$', '')).is_integer() for v in values)
            if all_int:
                return 'integer', {}
            has_decimal = any('.' in v for v in values)
            if has_decimal:
                return 'decimal', {}
            return 'float', {}

        for pattern, fmt, dtype in self.DATE_PATTERNS:
            match_count = sum(1 for v in values if re.match(pattern, v.strip()))
            if match_count == len(values):
                return dtype, {'format': fmt}

        max_len = max(len(v) for v in values) if values else 0
        if max_len <= 50:
            return 'varchar_short', {'max_length': max_len}
        elif max_len <= 255:
            return 'varchar', {'max_length': max_len}
        else:
            return 'text', {'max_length': max_len}

    def _count_type_diversity(self, values: List[str]) -> int:
        types_found = set()
        for v in values[:100]:
            v = v.strip()
            if not v:
                continue
            if v.lower() in self.BOOL_TRUE or v.lower() in self.BOOL_FALSE:
                types_found.add('bool')
                continue
            try:
                int(v.replace(',', ''))
                types_found.add('int')
                continue
            except ValueError:
                pass
            try:
                float(v.replace(',', '').replace('$', ''))
                types_found.add('float')
                continue
            except ValueError:
                pass
            is_date = False
            for pattern, fmt, dtype in self.DATE_PATTERNS:
                if re.match(pattern, v):
                    types_found.add('date')
                    is_date = True
                    break
            if not is_date:
                types_found.add('string')
        return len(types_found)

    def _is_pk_candidate(self, clean_name: str, values: List[str]) -> bool:
        if not values:
            return False
        pk_patterns = ['id', 'key', 'code', 'num', 'no', 'uuid', 'guid']
        name_hints = any(pattern in clean_name for pattern in pk_patterns)
        unique_ratio = len(set(values)) / len(values) if values else 0
        return name_hints and unique_ratio > 0.95

    def _is_fk_hint(self, clean_name: str) -> bool:
        fk_patterns = ['_id', '_key', '_code', '_ref', '_fk']
        return any(clean_name.endswith(pattern) for pattern in fk_patterns)

    def generate_ddl(self, table_name: str, nullable: bool = True) -> str:
        if not self.columns:
            raise ValueError("No columns analyzed. Call analyze() first.")

        lines = [f"-- DDL generated by DataForge v2.0.0-alpha",
                 f"-- Dialect: {self.dialect}",
                 f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                 "",
                 f"CREATE TABLE {table_name} ("]

        col_defs = []
        for col in self.columns:
            null_str = "NULL" if nullable else "NOT NULL"
            if col['is_pk_candidate']:
                null_str = "NOT NULL"
            col_def = f"    {col['clean_name']:30} {col['sql_type']:25} {null_str}"
            col_def += f"  -- was: '{col['original_name']}'"
            col_defs.append(col_def)

        pk_cols = [c['clean_name'] for c in self.columns if c['is_pk_candidate']]
        if pk_cols:
            col_defs.append(f"    CONSTRAINT pk_{table_name} PRIMARY KEY ({', '.join(pk_cols)})")

        for i, col_def in enumerate(col_defs):
            if i < len(col_defs) - 1:
                lines.append(col_def + ",")
            else:
                lines.append(col_def)

        lines.append(");")
        return "\n".join(lines)

    def generate_data_dictionary(self) -> List[Dict]:
        return [
            {
                'column_name': col['clean_name'],
                'original_name': col['original_name'],
                'data_type': col['sql_type'],
                'inferred_type': col['inferred_type'],
                'nullable': col['null_pct'] > 0,
                'null_percentage': col['null_pct'],
                'unique_values': col['unique_count'],
                'is_primary_key': col['is_pk_candidate'],
                'is_foreign_key_hint': col['is_fk_hint'],
                'is_mixed_types': col['is_mixed'],
                'max_length': col['max_length'],
                'sample_values': ', '.join(col['sample_values'][:3]),
                'description': '',
            }
            for col in self.columns
        ]

    def get_column_name_map(self) -> Dict[str, str]:
        return {col['original_name']: col['clean_name'] for col in self.columns}

    def get_quality_summary(self) -> Dict[str, Any]:
        return {
            'total_rows': self.row_count,
            'total_columns': self.column_count,
            'total_cells': self.row_count * self.column_count,
            'total_nulls': sum(c['null_count'] for c in self.columns),
            'null_percentage': round(
                sum(c['null_count'] for c in self.columns) /
                (self.row_count * self.column_count) * 100, 2
            ) if self.row_count > 0 else 0,
            'columns_with_nulls': sum(1 for c in self.columns if c['null_count'] > 0),
            'pk_candidates': [c['clean_name'] for c in self.columns if c['is_pk_candidate']],
            'fk_hints': [c['clean_name'] for c in self.columns if c['is_fk_hint']],
            'mixed_type_columns': [c['clean_name'] for c in self.columns if c['is_mixed']],
        }
