# PyInstaller spec for StarPing
# Build: pyinstaller starping.spec
# Produces: dist/StarPing/ (folder with StarPing.exe + deps)

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# collect_all pulls the Node.js driver binaries + package files that
# collect_data_files alone misses. This is the root-cause fix for
# "clicking login does nothing" on the frozen build.
pw_bin, pw_data, pw_hidden = collect_all('playwright')
keyring_hidden = collect_submodules('keyring.backends')

import os as _os

# Bundle Chromium directly if it was installed to ./bundled_browsers/ by the
# CI step (PLAYWRIGHT_BROWSERS_PATH=./bundled_browsers python -m playwright install chromium).
# At runtime, launcher.py sets PLAYWRIGHT_BROWSERS_PATH to <_MEIPASS>/ms-playwright.
_chromium_bundle = []
if _os.path.isdir('bundled_browsers'):
    _chromium_bundle = [('bundled_browsers', 'ms-playwright')]

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[*pw_bin],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        *pw_data,
        *_chromium_bundle,
    ],
    hiddenimports=[
        'app',
        'recruiter',
        'recruiter.db',
        'recruiter.paths',
        'recruiter.browser',
        'recruiter.auth',
        'recruiter.scraper',
        'recruiter.sender',
        'recruiter.discover',
        *pw_hidden,
        *keyring_hidden,
    ],
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
    [],
    exclude_binaries=True,
    name='StarPing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='static/favicon.ico' if __import__('os').path.exists('static/favicon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='StarPing',
)
