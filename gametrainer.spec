# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ["track_game.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("config", "config"),
        ("middleware", "middleware"),
        ("hardware_tools", "hardware_tools"),
        ("docs", "docs"),
    ],
    hiddenimports=[
        "cv2",
        "numpy",
        "pygame",
        "pandas",
        "sqlite3",
        "json",
        "middleware.capture.game_tracker",
        "middleware.analysis.replay_engine",
        "middleware.simulation.replay_viewer",
    ] + collect_submodules("middleware") + collect_submodules("hardware_tools"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="gametrainer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
