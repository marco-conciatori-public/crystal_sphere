# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Crystal Sphere Auto-Scout.
# Build:  uv run pyinstaller crystal_sphere.spec --noconfirm
# Output: dist/Crystal Sphere.exe (single-file build)

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('assets/references', 'assets/references'),
    ],
    hiddenimports=['window', 'state', 'compose'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Crystal Sphere',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='assets/launcher_icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
