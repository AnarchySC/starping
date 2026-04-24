# PyInstaller spec for StarPing
# Build: pyinstaller starping.spec
# Produces: dist/StarPing/ (folder with StarPing.exe + deps)

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

playwright_datas = collect_data_files('playwright', include_py_files=False)
keyring_hidden = collect_submodules('keyring.backends')

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        *playwright_datas,
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
