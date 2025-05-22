<div align="center">

# File Converter Built-In

A lightweight Windows utility that converts between various image, audio, and video formats using PIL and FFmpeg. This tool integrates with Windows Explorer to provide easy file format conversion via right-click context menu.

</div>

## Features

- **Multiple Format Support**:
  - **Images**: jpg, jpeg, png, bmp, gif, webp, tiff, ico
  - **Audio**: mp3, wav, ogg, m4a, flac, aac
  - **Video**: mp4, avi, mkv, mov, wmv, flv, webm, gif

- **Simple Interface**: Convert files directly from Windows Explorer context menu
- **Batch Processing**: Convert multiple files simultaneously
- **Special Handling**:
  - Smart ICO conversion with multiple sizes (16×16 to 256×256)
  - Optimized GIF creation from videos with duration limits
  - Quality-preserving codec selections for different formats

## Installation

### Option 1: Standalone Executable (Recommended)

1. Download the standalone executable from the [Releases page](https://github.com/OMetaVR/Extension-master/releases)
2. Run the executable directly - no installation needed
3. The converter will integrate with your Windows context menu automatically
4. Right-click on supported files to see the conversion options

That's it!

### Option 2: Build from Source

If you prefer to build from source with all dependencies bundled:

1. Follow the [Building from Source](Building%20from%20Source.md) guide for instructions on compiling your own build
2. This gives you more control over the installation but requires development tools, as well as allows you to ensure nothing nefarious is going on

## Usage

### Context Menu (Recommended)

1. Right-click on a supported file in Windows Explorer
2. Select "Convert to..." from the context menu
3. Choose your desired output format
4. The converted file will appear in the same directory

### Command Line

The converter can also be used via command line:

```
python file_converter.py file1.jpg file2.png -f webp
```

Options:
- `-f, --format`: Specify the output format
- `--max-gif-duration`: Set maximum duration for video to GIF conversion (default: 15s)

## Requirements

- Windows 10 or higher
- FFmpeg (bundled with the installer)
- Python 3.6+ (bundled in the standalone version)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [FFmpeg](https://ffmpeg.org/) for audio and video processing
- [Pillow](https://python-pillow.org/) for image processing
- [PyInstaller](https://www.pyinstaller.org/) for creating the standalone executable

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 
