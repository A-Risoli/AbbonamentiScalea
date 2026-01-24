# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('matplotlib')


a = Analysis(
    [os.path.join(os.getcwd(), 'abbonamenti', 'main.py')],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['matplotlib.backends.backend_qtagg', 'PyQt6.sip'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AbbonamentiScalea',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
        icon=[os.path.join(os.getcwd(), 'assets', 'icon.ico')] if os.path.exists(os.path.join(os.getcwd(), 'assets', 'icon.ico')) else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AbbonamentiScalea',
)
