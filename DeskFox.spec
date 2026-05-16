# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo,
    StringTable, StringStruct, VarFileInfo, VarStruct
)

version = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 2, 0, 0),
        prodvers=(1, 2, 0, 0),
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable('040904B0', [
                StringStruct('CompanyName', 'Yodeesy'),
                StringStruct('FileDescription', 'DeskFox Desktop Pet'),
                StringStruct('FileVersion', '1.2.0'),
                StringStruct('InternalName', 'DeskFox'),
                StringStruct('OriginalFilename', 'DeskFox.exe'),
                StringStruct('ProductName', 'DeskFox'),
                StringStruct('ProductVersion', '1.2.0'),
            ])
        ]),
        VarFileInfo([
            VarStruct('Translation', [1033, 1200])
        ])
    ]
)

a = Analysis(
    ['src/app/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('src/config', 'src/config'),
    ],
    hiddenimports=[
        'acrylic_utils',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

upx_exclude = [
    "tcl86t.dll",
    "tk86t.dll",
    "python3.dll",
    "user32.dll",
    "gdi32.dll"
]

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DeskFox',
    icon='assets/icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    onefile=True,
    version=version,
)
