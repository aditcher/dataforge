# -*- mode: python ; coding: utf-8 -*-
import os
block_cipher = None
a = Analysis(['main.py'], pathex=['.'], binaries=[],
    datas=[], hiddenimports=['ttkbootstrap','ttkbootstrap.themes',
    'ttkbootstrap.dialogs','ttkbootstrap.scrolled','ttkbootstrap.constants',
    'openpyxl','pandas','duckdb','flask','jinja2','werkzeug','chardet',
    'dateutil','core.schema_engine','core.cleaner','core.project_manager',
    'utils.file_handler','utils.formatted_exporter','bi.powerbi_exporter',
    'bi.m_code_generator','db.duckdb_manager','dashboard.server',
    'dashboard.chart_suggester'],
    hookspath=[], runtime_hooks=[], excludes=[], cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='DataForge',
    debug=False, strip=False, upx=True, console=False,
    icon='DataForge.ico' if os.path.exists('DataForge.ico') else None)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False,
    upx=True, name='DataForge')
app = BUNDLE(coll, name='DataForge.app',
    icon='DataForge.icns' if os.path.exists('DataForge.icns') else None,
    bundle_identifier='com.aditcher.dataforge',
    info_plist={'CFBundleName':'DataForge','CFBundleVersion':'2.0.0',
    'NSHighResolutionCapable':True,'LSMinimumSystemVersion':'10.14.0'})
