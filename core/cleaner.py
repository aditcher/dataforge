"""
DataForge Data Cleaner

Automated data cleaning engine with audit logging.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict


class DataCleaner:
    """Cleans and standardizes tabular data with full audit trail."""

    NULL_STRINGS = {'na', 'n/a', 'null', 'none', 'nan', 'undefined', ''}

    COMPANY_SUFFIXES = [
        ' inc', ' inc.', ' llc', ' llc.', ' ltd', ' ltd.',
        ' corp', ' corp.', ' corporation', ' company', ' co', ' co.',
        ' plc', ' gmbh', ' sa', ' ag', ' bv', ' lp', ' l.p.',
    ]

    DATE_FORMATS = [
        ('%m/%d/%Y', 'YYYY-MM-DD'),
        ('%d/%m/%Y', 'YYYY-MM-DD'),
        ('%m.%d.%Y', 'YYYY-MM-DD'),
        ('%d.%m.%Y', 'YYYY-MM-DD'),
        ('%Y-%m-%d', 'YYYY-MM-DD'),
        ('%m/%d/%y', 'YYYY-MM-DD'),
        ('%d/%m/%y', 'YYYY-MM-DD'),
        ('%Y/%m/%d', 'YYYY-MM-DD'),
        ('%m-%d-%Y', 'YYYY-MM-DD'),
        ('%d-%m-%Y', 'YYYY-MM-DD'),
    ]

    DATETIME_FORMATS = [
        ('%Y-%m-%d %H:%M', 'YYYY-MM-DD HH:MM'),
        ('%Y-%m-%d %H:%M:%S', 'YYYY-MM-DD HH:MM:SS'),
        ('%m/%d/%Y %H:%M', 'YYYY-MM-DD HH:MM'),
        ('%d/%m/%Y %H:%M', 'YYYY-MM-DD HH:MM'),
    ]

    def __init__(self):
        self.audit_log: List[Dict[str, Any]] = []
        self.cleaning_rules: List[Dict[str, Any]] = []
        self.original_rows: List[List[Any]] = []
        self.cleaned_rows: List[List[Any]] = []
        self.headers: List[str] = []

    def clean(self, headers: List[str], rows: List[List[Any]],
              rules: Optional[Dict[str, Any]] = None) -> List[List[Any]]:
        self.headers = headers
        self.original_rows = [list(row) for row in rows]
        self.cleaned_rows = [list(row) for row in rows]
        self.audit_log = []
        self.cleaning_rules = []

        if rules is None:
            rules = self._auto_detect_rules(headers, rows)

        self._step_remove_duplicates()
        self._step_strip_whitespace()
        self._step_standardize_nulls()
        self._step_standardize_dates()
        self._step_normalize_names()
        self._step_fix_categorical_zeros()

        return self.cleaned_rows

    def _auto_detect_rules(self, headers: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
        rules = {
            'remove_duplicates': True,
            'strip_whitespace': True,
            'standardize_nulls': True,
            'standardize_dates': True,
            'normalize_names': False,
            'fix_categorical_zeros': True,
        }
        name_patterns = ['name', 'company', 'organization', 'business', 'vendor', 'supplier']
        for header in headers:
            if any(pattern in header.lower() for pattern in name_patterns):
                rules['normalize_names'] = True
                break
        return rules

    def _step_remove_duplicates(self):
        original_count = len(self.cleaned_rows)
        seen = set()
        unique_rows = []
        duplicates_removed = 0

        for row in self.cleaned_rows:
            row_tuple = tuple(str(v) if v is not None else '' for v in row)
            if row_tuple not in seen:
                seen.add(row_tuple)
                unique_rows.append(row)
            else:
                duplicates_removed += 1

        self.cleaned_rows = unique_rows

        if duplicates_removed > 0:
            self._log_action(
                action='remove_duplicates',
                description=f'Removed {duplicates_removed} exact duplicate rows',
                rows_affected=duplicates_removed,
                before_value=original_count,
                after_value=len(self.cleaned_rows)
            )

    def _step_strip_whitespace(self):
        changes = 0
        for row_idx, row in enumerate(self.cleaned_rows):
            for col_idx, value in enumerate(row):
                if isinstance(value, str):
                    stripped = value.strip()
                    if stripped != value:
                        self.cleaned_rows[row_idx][col_idx] = stripped
                        changes += 1
        if changes > 0:
            self._log_action(
                action='strip_whitespace',
                description=f'Stripped whitespace from {changes} cells',
                rows_affected=changes
            )

    def _step_standardize_nulls(self):
        changes = 0
        for row_idx, row in enumerate(self.cleaned_rows):
            for col_idx, value in enumerate(row):
                if isinstance(value, str):
                    if value.strip().lower() in self.NULL_STRINGS:
                        self.cleaned_rows[row_idx][col_idx] = None
                        changes += 1
        if changes > 0:
            self._log_action(
                action='standardize_nulls',
                description=f'Converted {changes} null placeholders to NULL',
                rows_affected=changes
            )

    def _step_standardize_dates(self):
        changes = 0
        for col_idx, header in enumerate(self.headers):
            date_pattern = re.compile(r'date|time|day|month|year', re.IGNORECASE)
            if not date_pattern.search(header):
                continue
            for row_idx, row in enumerate(self.cleaned_rows):
                value = row[col_idx]
                if value is None or not isinstance(value, str):
                    continue
                value = value.strip()
                for fmt, target_fmt in self.DATE_FORMATS:
                    try:
                        parsed = datetime.strptime(value, fmt)
                        self.cleaned_rows[row_idx][col_idx] = parsed.strftime('%Y-%m-%d')
                        changes += 1
                        break
                    except ValueError:
                        continue
                if self.cleaned_rows[row_idx][col_idx] == value:
                    for fmt, target_fmt in self.DATETIME_FORMATS:
                        try:
                            parsed = datetime.strptime(value, fmt)
                            self.cleaned_rows[row_idx][col_idx] = parsed.strftime('%Y-%m-%d %H:%M')
                            changes += 1
                            break
                        except ValueError:
                            continue
        if changes > 0:
            self._log_action(
                action='standardize_dates',
                description=f'Standardized {changes} date values to YYYY-MM-DD',
                rows_affected=changes
            )

    def _step_normalize_names(self):
        changes = 0
        name_patterns = re.compile(r'name|company|organization|business|vendor|supplier', re.IGNORECASE)
        for col_idx, header in enumerate(self.headers):
            if not name_patterns.search(header):
                continue
            for row_idx, row in enumerate(self.cleaned_rows):
                value = row[col_idx]
                if value is None or not isinstance(value, str):
                    continue
                original = value
                value = value.strip()
                lower_val = value.lower()
                for suffix in self.COMPANY_SUFFIXES:
                    if lower_val.endswith(suffix):
                        value = value[:-len(suffix)].strip()
                        lower_val = value.lower()
                value = value.title()
                if value != original:
                    self.cleaned_rows[row_idx][col_idx] = value
                    changes += 1
        if changes > 0:
            self._log_action(
                action='normalize_names',
                description=f'Normalized {changes} name/company values',
                rows_affected=changes
            )

    def _step_fix_categorical_zeros(self):
        categorical_patterns = re.compile(
            r'color|size|style|type|category|status|gender|role|department',
            re.IGNORECASE
        )
        changes = 0
        for col_idx, header in enumerate(self.headers):
            if not categorical_patterns.search(header):
                continue
            for row_idx, row in enumerate(self.cleaned_rows):
                value = row[col_idx]
                if value == 0 or value == '0' or value == 0.0:
                    self.cleaned_rows[row_idx][col_idx] = None
                    changes += 1
        if changes > 0:
            self._log_action(
                action='fix_categorical_zeros',
                description=f'Converted {changes} zero placeholders to NULL in categorical columns',
                rows_affected=changes
            )

    def _log_action(self, action: str, description: str,
                    rows_affected: int = 0, before_value: Any = None,
                    after_value: Any = None):
        self.audit_log.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'description': description,
            'rows_affected': rows_affected,
            'before_value': before_value,
            'after_value': after_value,
        })

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return self.audit_log

    def get_cleaning_summary(self) -> Dict[str, Any]:
        return {
            'original_row_count': len(self.original_rows),
            'cleaned_row_count': len(self.cleaned_rows),
            'rows_removed': len(self.original_rows) - len(self.cleaned_rows),
            'total_changes': sum(entry.get('rows_affected', 0) for entry in self.audit_log),
            'operations_performed': len(self.audit_log),
            'operations': [entry['action'] for entry in self.audit_log],
        }

    def get_preview(self, n: int = 50) -> List[List[Any]]:
        return self.cleaned_rows[:n]

    def get_staged_csv_rows(self) -> Tuple[List[str], List[List[str]]]:
        csv_rows = []
        for row in self.cleaned_rows:
            csv_row = ['' if v is None else str(v) for v in row]
            csv_rows.append(csv_row)
        return self.headers, csv_rows
