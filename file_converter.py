import sys
import time
import argparse
from pathlib import Path
from PIL import Image
from typing import List, Set, Dict, Optional, Tuple
import threading
import logging
import ffmpeg
import tempfile
import os
import shutil
import subprocess
import json
import msvcrt
import atexit

if os.name == 'nt':
    from subprocess import CREATE_NO_WINDOW

FFMPEG_BIN = ""
FFPROBE_BIN = ""

def get_ffmpeg_binary_path() -> Tuple[str, str]:
    global FFMPEG_BIN, FFPROBE_BIN
    
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
        
        temp_dir = sys._MEIPASS if hasattr(sys, '_MEIPASS') else base_dir
        
        ffmpeg_bin = os.path.join(temp_dir, 'ffmpeg.exe')
        ffprobe_bin = os.path.join(temp_dir, 'ffprobe.exe')
        
        if os.path.exists(ffmpeg_bin) and os.path.exists(ffprobe_bin):
            FFMPEG_BIN = ffmpeg_bin
            FFPROBE_BIN = ffprobe_bin
            
            ffmpeg._run.DEFAULT_FFMPEG_PATH = ffmpeg_bin
            ffmpeg._run.DEFAULT_FFPROBE_PATH = ffprobe_bin
            
            logging.info(f"Using bundled ffmpeg binaries from PyInstaller temp dir: {ffmpeg_bin}")
            return ffmpeg_bin, ffprobe_bin
    
    try:
        if os.name == 'nt':
            ffmpeg_bin = shutil.which('ffmpeg.exe')
            ffprobe_bin = shutil.which('ffprobe.exe')
        else:
            ffmpeg_bin = shutil.which('ffmpeg')
            ffprobe_bin = shutil.which('ffprobe')
            
        if ffmpeg_bin and ffprobe_bin:
            FFMPEG_BIN = ffmpeg_bin
            FFPROBE_BIN = ffprobe_bin
            logging.info(f"Using ffmpeg binaries from PATH: {ffmpeg_bin}")
            return ffmpeg_bin, ffprobe_bin
        else:
            logging.error("FFmpeg binaries not found in PATH or bundled package")
            return "", ""
    except Exception as e:
        logging.error(f"Error finding ffmpeg: {str(e)}")
        return "", ""

# FFMPEG headless function
def run_subprocess_hidden(cmd, **kwargs):
    if os.name == 'nt':
        kwargs['creationflags'] = CREATE_NO_WINDOW
    
    return subprocess.run(cmd, **kwargs)

def run_ffmpeg_command(ffmpeg_bin, input_path, output_path, extra_args=None, capture_output=True):
    if not ffmpeg_bin:
        raise ValueError("FFmpeg binary not found or not working")
        
    cmd = [
        ffmpeg_bin,
        "-i", str(input_path.resolve()),
    ]
    
    if extra_args:
        cmd.extend(extra_args)
    
    cmd.extend([
        "-y",  # overwrite output
        "-loglevel", "error",
        "-hide_banner",
        str(output_path.resolve())
    ])
    
    if capture_output:
        result = run_subprocess_hidden(
            cmd,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        result = run_subprocess_hidden(cmd)
    
    if result.returncode != 0 and capture_output:
        raise Exception(f"FFmpeg error: {result.stderr}")
    
    return result

# ffprobe function
def run_ffprobe_command(ffprobe_bin, input_path, probe_args, capture_output=True):
    if not ffprobe_bin:
        raise ValueError("FFprobe binary not found or not working")
        
    cmd = [
        ffprobe_bin,
        "-v", "error",
    ]
    
    cmd.extend(probe_args)
    
    cmd.append(str(input_path.resolve()))
    
    if capture_output:
        result = run_subprocess_hidden(
            cmd,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        result = run_subprocess_hidden(cmd)
    
    if result.returncode != 0 and capture_output:
        raise Exception(f"FFprobe error: {result.stderr}")
    
    return result

class FileLock:
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.file_handle = None

    def acquire(self):
        try:
            self.file_handle = open(self.lock_file, 'a+')
            msvcrt.locking(self.file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except IOError:
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None
            return False

    def release(self):
        if self.file_handle:
            msvcrt.locking(self.file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            self.file_handle.close()
            self.file_handle = None

class FileConverter:
    def __init__(self, batch_wait_time: float = 0.1, max_gif_duration: float = 30.0): # max gif duration, this comment is here for you dot, this line limits how long the gif can be from a video, incase you wanna change it
        self.batch_wait_time = batch_wait_time
        self.max_gif_duration = max_gif_duration
        self.pending_files: Set[tuple[Path, str]] = set()
        self.processing_lock = threading.Lock()
        self.batch_timer = None
        self.ffmpeg_bin, self.ffprobe_bin = get_ffmpeg_binary_path()
        
        if not self.ffmpeg_bin or not self.ffprobe_bin:
            logging.error("FFmpeg binaries not found. Media conversion may not work.")
        else:
            try:
                result = run_subprocess_hidden(
                    [self.ffmpeg_bin, "-version"], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode == 0:
                    logging.info(f"FFmpeg verified working: {result.stdout.splitlines()[0] if result.stdout else 'OK'}")
                else:
                    logging.error(f"FFmpeg verification failed: {result.stderr}")
            except Exception as e:
                logging.error(f"Error verifying ffmpeg: {str(e)}")
        
        self.temp_dir = Path(tempfile.gettempdir()) / "file_converter"
        self.temp_dir.mkdir(exist_ok=True)
        self.lock_file = self.temp_dir / "converter.lock"
        self.file_lock = FileLock(str(self.lock_file))
        
        atexit.register(self._cleanup)
        
        # file formats
        self.image_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.ico'}
        self.audio_formats = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
        self.video_formats = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
        
        self.image_format_mapping = {
            'jpg': 'JPEG',
            'jpeg': 'JPEG',
            'png': 'PNG',
            'bmp': 'BMP',
            'gif': 'GIF',
            'webp': 'WEBP',
            'tiff': 'TIFF',
            'ico': 'ICO'
        }
        
        self.ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        self.audio_format_mapping = {
            'mp3': 'mp3',
            'wav': 'wav',
            'ogg': 'ogg',
            'm4a': 'm4a',
            'flac': 'flac',
            'aac': 'aac'
        }
        
        self.video_format_mapping = {
            'mp4': 'mp4',
            'avi': 'avi',
            'mkv': 'mkv',
            'mov': 'mov',
            'wmv': 'wmv',
            'flv': 'flv',
            'webm': 'webm',
            'gif': 'gif'
        }
        
        self.supported_formats = self.image_formats | self.audio_formats | self.video_formats
        self.default_format = 'png'
        self.default_audio_format = 'mp3'
        self.default_video_format = 'mp4'

    def _cleanup(self):
        self.file_lock.release()

    def add_file(self, file_path: Path, output_format: str = None) -> None:
        with self.processing_lock:
            if file_path.suffix.lower() in self.supported_formats:
                self.pending_files.add((file_path, output_format))
                logging.info(f"Added file to batch: {file_path} (Output format: {output_format})")
                
                if self.batch_timer:
                    self.batch_timer.cancel()
                self.batch_timer = threading.Timer(self.batch_wait_time, self.process_batch)
                self.batch_timer.start()
            else:
                logging.warning(f"Unsupported file format: {file_path}")

    def process_batch(self) -> None:
        with self.processing_lock:
            if not self.pending_files:
                return

            logging.info(f"Processing batch of {len(self.pending_files)} files")
            files_to_process = self.pending_files.copy()
            self.pending_files.clear()

            success_count = 0
            fail_count = 0

            for file_path, format_override in files_to_process:
                try:
                    self.convert_file(file_path, format_override)
                    success_count += 1
                except Exception as e:
                    logging.error(f"Error converting {file_path}: {str(e)}")
                    fail_count += 1

            if success_count > 0:
                logging.info(f"Successfully converted {success_count} files")
            if fail_count > 0:
                logging.warning(f"Failed to convert {fail_count} files")

    def convert_file(self, file_path: Path, output_format: str = None) -> None:
        try:
            input_format = file_path.suffix.lower()[1:]
            
            if not output_format:
                if file_path.suffix.lower() in self.image_formats:
                    output_format = self.default_format
                elif file_path.suffix.lower() in self.audio_formats:
                    output_format = self.default_audio_format
                elif file_path.suffix.lower() in self.video_formats:
                    output_format = self.default_video_format
            
            output_format = output_format.lower()
            output_path = file_path.with_suffix(f'.{output_format}')
            
            if input_format == output_format:
                logging.info(f"Skipping {file_path} - already in desired format")
                return
            
            if file_path.suffix.lower() in self.image_formats:
                if output_format not in self.image_format_mapping:
                    raise ValueError(f"Unsupported image output format: {output_format}")
                self._convert_image(file_path, output_path, output_format)
            
            elif file_path.suffix.lower() in self.audio_formats:
                if output_format not in self.audio_format_mapping:
                    raise ValueError(f"Unsupported audio output format: {output_format}")
                self._convert_audio(file_path, output_path, output_format)
            
            elif file_path.suffix.lower() in self.video_formats:
                if output_format not in self.video_format_mapping:
                    raise ValueError(f"Unsupported video output format: {output_format}")
                self._convert_video(file_path, output_path, output_format)
            
            else:
                raise ValueError(f"Unsupported input format: {input_format}")
                
        except Exception as e:
            logging.error(f"Failed to convert {file_path}: {str(e)}")
            raise

        #if else statements make the world go round

    def _convert_image(self, input_path: Path, output_path: Path, output_format: str) -> None:
        pil_format = self.image_format_mapping[output_format]
        with Image.open(input_path) as img:
            if pil_format == 'ICO':
                images = []
                
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                for size in self.ico_sizes:
                    resized = img.resize(size, Image.Resampling.LANCZOS)
                    images.append(resized)
                
                img.save(output_path, format=pil_format, sizes=[(i.width, i.height) for i in images])
                
                for resized in images:
                    resized.close()
            else:
                if pil_format == 'JPEG' and img.mode in ('RGBA', 'LA'):
                    img = img.convert('RGB')
                
                img.save(output_path, format=pil_format)
            
            logging.info(f"Converted {input_path} to {output_path}")

    def _convert_audio(self, input_path: Path, output_path: Path, output_format: str) -> None:
        try:
            result = run_ffmpeg_command(self.ffmpeg_bin, input_path, output_path)
            logging.info(f"Converted {input_path} to {output_path}")
        except Exception as e:
            logging.error(f"Error in audio conversion: {str(e)}")
            raise

    def _get_video_duration(self, input_path: Path) -> float:
        try:
            probe_args = ["-show_entries", "format=duration", "-of", "json"]
            result = run_ffprobe_command(self.ffprobe_bin, input_path, probe_args)
            
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            return duration
        except Exception as e:
            logging.error(f"Error getting video duration: {str(e)}")
            raise

    def _convert_video_to_gif(self, input_path: Path, output_path: Path) -> None:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                palette_path = os.path.join(temp_dir, 'palette.png')
                
                palette_args = [
                    "-vf", "fps=10,scale=480:-1:flags=lanczos,palettegen"
                ]
                run_ffmpeg_command(self.ffmpeg_bin, input_path, Path(palette_path), palette_args)
                
                gif_args = [
                    "-i", palette_path,
                    "-filter_complex", "fps=10,scale=480:-1:flags=lanczos[x];[x][1:v]paletteuse"
                ]
                run_ffmpeg_command(self.ffmpeg_bin, input_path, output_path, gif_args)
                
                logging.info(f"Converted {input_path} to GIF: {output_path}")
        except Exception as e:
            logging.error(f"Error converting video to GIF: {str(e)}")
            raise

    def _convert_video(self, input_path: Path, output_path: Path, output_format: str) -> None:
        try:
            if output_format == 'gif':
                duration = self._get_video_duration(input_path)
                if duration > self.max_gif_duration:
                    raise ValueError(
                        f"Video duration ({duration:.1f}s) exceeds maximum allowed for GIF conversion "
                        f"({self.max_gif_duration}s)"
                    )
                self._convert_video_to_gif(input_path, output_path)
                return

            extra_args = []
            
            if output_format in ['mp4', 'mov']:
                extra_args.extend([
                    "-c:v", "libx264",    # H.264 video codec
                    "-c:a", "aac",        # AAC audio codec
                    "-preset", "medium",  # Encoding preset
                    "-crf", "23"          # Constant Rate Factor
                ])
            elif output_format == 'webm':
                extra_args.extend([
                    "-c:v", "libvpx-vp9", # VP9 video codec
                    "-c:a", "libopus",    # Opus audio codec
                    "-crf", "30",         # Quality factor
                    "-b:v", "0"           # Variable bitrate
                ])
            
            run_ffmpeg_command(self.ffmpeg_bin, input_path, output_path, extra_args)
            logging.info(f"Converted {input_path} to {output_path}")
        except Exception as e:
            logging.error(f"Error in video conversion: {str(e)}")
            raise

def parse_args():
    parser = argparse.ArgumentParser(description='Convert media files to different formats')
    parser.add_argument('files', nargs='+', help='Files to convert')
    parser.add_argument('-f', '--format', help='Output format (e.g., jpg, png, mp3, wav, mp4, webm, gif)')
    parser.add_argument('--max-gif-duration', type=float, default=15.0, help='Maximum duration (in seconds) for video to GIF conversion') # you can also change the gif duration via this, incase you didn't make up your mind when reading the last comment lmaooo
    return parser.parse_args()

def main():
    args = parse_args()
    converter = FileConverter(max_gif_duration=args.max_gif_duration)
    
    for file_path in args.files:
        converter.add_file(Path(file_path), args.format)
    
    time.sleep(0.2)

if __name__ == "__main__":
    main() 