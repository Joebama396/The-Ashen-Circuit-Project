# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['game.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/characters/party_overworld_hd_v2.png', 'assets/characters'), ('assets/characters/party_battle_ready_hd_v1.png', 'assets/characters'), ('assets/characters/party_combat_bodies_hd_v1.png', 'assets/characters'), ('assets/characters/party_combat_arms_hd_v1.png', 'assets/characters'), ('assets/audio/battle_theme_1.mp3', 'assets/audio'), ('assets/audio/menu_theme.mp3', 'assets/audio')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='ashen-circuit',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
