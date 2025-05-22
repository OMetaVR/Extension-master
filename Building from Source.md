# Building File Converter from Source

This guide will walk you through the process of building the File Converter utility from source code.

## Prerequisites

- Windows 10 or higher
- Git (to clone the repository)
- Python 3.6 or higher
- pip (Python package manager)
- Visual Studio Build Tools (for some dependencies)

## Step 1: Clone the Repository

```bash
git clone https://github.com/OMetaVR/Extension-master.git
cd "Extension-master"
```

## Step 2: Set Up a Virtual Environment (Recommended)

```bash
python -m venv venv
venv\Scripts\activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all the required Python packages, including:
- Pillow (PIL) for image processing
- ffmpeg-python for media conversion
- PyInstaller for creating the executable

## Step 4: Verify FFmpeg Installation

The converter requires FFmpeg for audio and video processing. You have two options:

### Option A: Use System FFmpeg

1. Download FFmpeg from the [official website](https://ffmpeg.org/download.html)
2. Add it to your system PATH
3. Allow the program to automatically detect the PATH entry and use that

this option can save around 100MB on the file size thanks to no FFmpeg binaries, but 150MB is still not a lot.

### Option B: Bundle FFmpeg with Your Build

FFmpeg binaries are not included in the repository. To bundle them with your executable:

1. Download FFmpeg binaries from the [official website](https://ffmpeg.org/download.html)
2. Place `ffmpeg.exe` and `ffprobe.exe` in a notable directory as your script
3. When running the build_standalone.bat file, specify the directory of the FFmpeg binaries you installed
3. When building with PyInstaller, these will be automatically included in the bundle

## Step 5: Test the Converter

Before building the standalone executable, test the converter:

```bash
python file_converter.py test_image.jpg -f png
```

Replace `test_image.jpg` with an actual file to convert.

## Step 6: Build the Standalone Executable

You can either alter the FileConverter.spec for your own means, or if you just want to get build things quickly with FFmpeg binaries, run the build_standalone.bat file.

This will create a standalone executable in the `dist` folder.

## Step 7: Create Windows Context Menu Integration

If you want to create the Windows Explorer integration:

```bash
python registry_manager.py --install
```

you can also remove them:

```bash
python registry_manager.py --remove
```

This will add the necessary registry entries for right-click context menu integration.

## Troubleshooting

### Common Issues

1. **Missing Dependencies**:
   - Error: `ModuleNotFoundError`
   - Solution: Make sure all requirements are installed with `pip install -r requirements.txt`

2. **FFmpeg Not Found**:
   - Error: `FFmpeg binaries not found`
   - Solution: Ensure FFmpeg is installed and in your PATH, or use the bundled version

3. **PyInstaller Issues**:
   - Error: `PyInstaller not working correctly`
   - Solution: Try `pip install --upgrade pyinstaller` and run the build command again

### Getting Help

If you encounter issues not covered here, please open an issue on the GitHub repository.