# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Define the ffmpeg binaries location - adjust to your actual path where ffmpeg is installed
# These should be the paths to ffmpeg.exe and ffprobe.exe on your development machine
import os
ffmpeg_path = os.environ.get('FFMPEG_PATH', r'C:\ffmpeg\bin')  # Default path, adjust as needed

# Check if ffmpeg exists at the provided path
if not os.path.exists(os.path.join(ffmpeg_path, 'ffmpeg.exe')) or not os.path.exists(os.path.join(ffmpeg_path, 'ffprobe.exe')):
    raise ValueError(f"FFmpeg binaries not found at {ffmpeg_path}. Please set FFMPEG_PATH environment variable correctly.")

# Icon and assets for the application
datas = [
    ('assets/menuitem.ico', 'assets'),
    ('assets/style.qss', 'assets'),
    ('assets/checkmark.svg', 'assets'),
    ('assets/dropdown.svg', 'assets'),
    ('assets/menuitem.png', 'assets'),
    # Add ffmpeg binaries directly to the root of the PyInstaller temp directory
    (os.path.join(ffmpeg_path, 'ffmpeg.exe'), '.'),
    (os.path.join(ffmpeg_path, 'ffprobe.exe'), '.')
]

a = Analysis(
    ['unified_converter.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # GUI dependencies
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui',
        # Import file converter dependencies
        'PIL', 'PIL._imagingtk', 'PIL._tkinter_finder',
        # Media processing
        'ffmpeg-python', 'ffmpeg',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FileConverter-Standalone',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI mode
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/menuitem.ico',  # Icon for the application
) 