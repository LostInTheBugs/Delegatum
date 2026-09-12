# -*- mode: python ; coding: utf-8 -*-
# Delegatum Desktop — spec PyInstaller (onedir, sans console).
# Build : pyinstaller --clean --noconfirm desktop/delegatum.spec  (depuis la racine du dépôt)
#
# onedir et non onefile : le mode onefile s'auto-extrait dans %TEMP% puis se
# relance, un comportement qui déclenche les heuristiques de Windows Defender
# (vécu sur Patrimony Desktop : « Behavior:Win32/DefenseEvasion.A!ml » — faux
# positif). Le mode dossier n'extrait rien : beaucoup moins de détections.

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))  # racine du dépôt, absolue
BACKEND = os.path.join(ROOT, 'backend')

# --- Version info Windows (générée depuis VERSION à chaque build) ----------
_ver = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()
_nums = tuple(([int(x) for x in _ver.split('.')] + [0, 0, 0, 0])[:4])
_vi = os.path.join(SPECPATH, 'version_info.txt')
with open(_vi, 'w', encoding='utf-8') as f:
    f.write(f'''VSVersionInfo(
  ffi=FixedFileInfo(filevers={_nums}, prodvers={_nums}, mask=0x3f, flags=0x0,
    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'LostInTheBugs'),
      StringStruct('FileDescription', 'Delegatum - staff delegation management (Luxembourg)'),
      StringStruct('FileVersion', '{_ver}'),
      StringStruct('InternalName', 'Delegatum'),
      StringStruct('LegalCopyright', 'MIT License - github.com/LostInTheBugs/Delegatum'),
      StringStruct('OriginalFilename', 'Delegatum.exe'),
      StringStruct('ProductName', 'Delegatum'),
      StringStruct('ProductVersion', '{_ver}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])])
''')

a = Analysis(
    ['launcher.py'],
    pathex=[BACKEND],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'frontend', 'dist'), 'static'),  # UI servie par le backend (SD_STATIC_DIR)
        (os.path.join(ROOT, 'VERSION'), '.'),
    ],
    hiddenimports=[
        # uvicorn importe ses implémentations dynamiquement
        'uvicorn.logging',
        'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.loops.asyncio',
        'uvicorn.protocols', 'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan', 'uvicorn.lifespan.on',
        # fenêtre native (pywebview : plateforme choisie au runtime)
        'webview',
        'webview.platforms.winforms', 'webview.platforms.edgechromium',
        'webview.platforms.gtk', 'webview.platforms.cocoa',
        # QR code MFA : sous-modules images chargés dynamiquement
        'qrcode.image.pil', 'qrcode.image.png',
        # package applicatif (imports statiques, listés par sûreté)
        'app', 'app.routes', 'app.services.email_service', 'app.core.spa',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Desktop = SQLite uniquement : psycopg2 (et ses DLL libpq) inutile ici.
    excludes=['psycopg2', 'psycopg2_binary'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Delegatum',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='delegatum.ico',
    version=_vi,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Delegatum',
)
