# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = []
datas += collect_data_files('matplotlib')


block_cipher = None


a = Analysis(
    ['C:\\Users\\risol\\Documents\\GitHub\\AbbonamentiScalea\\abbonamenti\\main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['matplotlib.backends.backend_qt5agg', 'PyQt5.sip', 'backports', 'backports.tarfile'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['_pyinstaller_hooks_contrib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    icon=['C:\\Users\\risol\\Documents\\GitHub\\AbbonamentiScalea\\assets\\icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AbbonamentiScalea',
)
