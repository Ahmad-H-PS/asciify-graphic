# asciify-graphic 🎨✨

> Convert any image or video file into an ASCII code picture, rasterized graphic, or animation video with full-color rendering, audio preservation, and real-time terminal playback.

[![CI](https://github.com/Ahmad-H-PS/asciify-graphic/actions/workflows/ci.yml/badge.svg)](https://github.com/Ahmad-H-PS/asciify-graphic/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## ✨ Features

- **Any Image & Video Format**: Supports PNG, JPG, JPEG, WEBP, BMP, GIF, MP4, MKV, AVI, MOV, WebM, and more.
- **Direct URLs & YouTube Streaming**: Convert pictures and videos directly from web links, including YouTube, shorts, and video platforms.
- **Multiple Output Formats**:
  - **Rasterized Graphics**: Render high-definition ASCII graphics (`.png`, `.jpg`, `.webp`) using a pre-rendered vectorized font atlas.
  - **Animation Videos**: Render full-length ASCII animation videos (`.mp4`, `.mkv`, `.avi`, `.webm`) with **audio track preservation**.
  - **Animated GIFs**: Render compact, shareable ASCII animations (`.gif`).
  - **HTML Webpages**: Standalone `.html` files styled with monospace CSS and TrueColor RGB spans.
  - **ANSI Terminal Art**: 24-bit TrueColor ANSI terminal output (`.ans`, `.ansi`, or direct stdout).
  - **Plain Text**: Clean ASCII art text files (`.txt`).
- **Interactive Terminal Video Player**: Stream videos directly inside your terminal in real-time (`asciify play <video>`) with synchronized FPS and interactive controls (pause/resume with Space, quit with `q`).
- **Rich Character Sets & Ramps**:
  - `standard`: `@%#*+=-:. `
  - `detailed`: 70-character fine-grained luminance gradient
  - `blocks`: Unicode block shading elements `█▓▒░ `
  - `matrix`: Authentic Katakana and numeric character rain `ｦｱｳ...`
  - `binary`: Tech aesthetic `10 `
  - `dots`: Braille dot density `⣿⣶⣤⣀ `
  - *Custom*: Any custom character ramp specified on the CLI or API!
- **Color Modes**:
  - `color`: 24-bit RGB TrueColor matching source pixels
  - `grayscale`: Luminance-mapped monochrome shading
  - `matrix`: Iconic cyberpunk Matrix green phosphor glow
  - `amber`: Retro amber CRT monitor glow
  - `cyan`: Vivid neon cyan styling
  - `monochrome`: Custom foreground color on dark background
- **Visual Enhancements**:
  - Automatic aspect ratio correction (monospace character width-to-height ratio)
  - Sobel edge detection & contour enhancement (`--edge`)
  - Adjustable brightness, contrast, and gamma correction
  - Invert brightness ramp (`--invert`)

---

## 🚀 Installation

Clone the repository and install with `pip`:

```bash
git clone https://github.com/Ahmad-H-PS/asciify-graphic.git
cd asciify-graphic
pip install -e .
```

All video encoding and decoding dependencies (including FFmpeg) are bundled self-contained via `imageio-ffmpeg` and `opencv-python-headless`.

---

## 💻 CLI Usage

The tool installs the `asciify` (and alias `asciify-graphic`) command.

### 1. Smart Auto-Detection

`asciify` automatically detects whether your input is an image, video, direct URL, or YouTube link:

```bash
# Print image as ASCII to terminal (local or URL)
asciify photo.jpg
asciify https://example.com/logo.png

# Stream a YouTube video directly in your terminal in real-time!
asciify https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Convert a YouTube video to an ASCII animation video (audio preserved)
asciify https://www.youtube.com/watch?v=dQw4w9WgXcQ -o rickroll_ascii.mp4

# Save online image as ASCII PNG graphic
asciify https://picsum.photos/400/300 -o ascii_art.png
```

---

### 2. Image Conversion (`asciify image`)

```bash
# Print to terminal with auto-fitted width
asciify image photo.jpg

# Save as a high-resolution ASCII PNG graphic
asciify image photo.jpg -o ascii_art.png --width 120 --font-size 18

# Generate a standalone interactive HTML page
asciify image photo.jpg -o art.html --width 100

# Save plain text ASCII art
asciify image photo.jpg -o art.txt --width 80

# Classic Matrix green style
asciify image photo.jpg -o matrix.png -m matrix -c matrix

# Block shading with edge enhancement
asciify image photo.jpg -o blocks.png -c blocks --edge
```

**Common Image Options:**
- `-o, --output <path>`: Target output file (`.txt`, `.ans`, `.html`, `.png`, `.jpg`, `.webp`)
- `-w, --width <int>`: Number of ASCII columns (default: 100 or terminal width)
- `-H, --height <int>`: Number of ASCII rows (auto-computed from aspect ratio if omitted)
- `-c, --charset <name|string>`: Character set preset (`standard`, `detailed`, `blocks`, `matrix`, `binary`, `dots`, `minimal`) or custom string
- `-m, --color-mode <mode>`: `color`, `grayscale`, `matrix`, `amber`, `cyan`, `monochrome`, `none`
- `--edge`: Enable Sobel edge detection to highlight contours
- `--brightness <float>` / `--contrast <float>` / `--gamma <float>`: Image adjustments
- `--bg <color>` / `--fg <color>`: Background and foreground colors (`#000000`, `black`, `white`, etc.)
- `--font-size <int>`: Font size in pixels for rendered images (default: 16)
- `--font-path <path>`: Custom TTF/OTF monospace font file

---

### 3. Video Conversion (`asciify video`)

Convert any video into a rendered ASCII animation video or animated GIF:

```bash
# Convert video to MP4 animation (audio is preserved by default!)
asciify video clip.mp4 -o ascii_animation.mp4 --width 120

# Convert directly from a YouTube link (full video or preview)
asciify video "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o rickroll.mp4
asciify video "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o rickroll_preview.mp4 --max-frames 120

# Convert video to animated GIF
asciify video clip.mp4 -o animation.gif --width 80 --fps 15

# Matrix style video conversion
asciify video clip.mp4 -o matrix_clip.mp4 -m matrix -c matrix

# Skip frames for fast preview (process every 2nd frame)
asciify video clip.mp4 -o fast.mp4 --step 2

# Limit number of frames
asciify video clip.mp4 -o preview.mp4 --max-frames 60

# Export frame sequence to directory
asciify video clip.mp4 -o output_frames/
```

---

### 4. Live Terminal Video Player (`asciify play`)

Play any video directly inside your terminal in real-time:

```bash
# Play video in terminal (auto-fits terminal dimensions)
asciify play clip.mp4

# Play with Matrix styling in an infinite loop
asciify play clip.mp4 -m matrix -c matrix --loop

# Play with block shading
asciify play clip.mp4 -c blocks
```

**Player Controls:**
- `Space`: Pause / Resume
- `q` or `ESC`: Quit player

---

### 5. Inspect Media & Character Sets

```bash
# List all built-in character set ramps
asciify charsets

# Display resolution, framerate, and duration of media
asciify info clip.mp4
asciify info photo.jpg
```

---

## 🐍 Python Library API

You can also use `asciify` directly in your Python code:

### Image Conversion

```python
from asciify import AsciiConfig, AsciiConverter, AsciiRenderer, convert_image

# One-liner to convert and save (local file or direct image URL)
convert_image("https://example.com/photo.jpg", "output.png", width=120, color_mode="color")

# Advanced programmatic access
config = AsciiConfig(
    width=100,
    charset="detailed",
    color_mode="matrix",
    edge_detect=True,
    brightness=1.1,
)

converter = AsciiConverter(config)
frame = converter.convert_image("photo.jpg")
```

### Video Conversion & Playback

```python
from asciify import convert_video, play_video

# Convert video (local file or YouTube link) to MP4 animation with audio
convert_video(
    input_path="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    output_path="output_ascii.mp4",
    width=120,
    color_mode="color",
    keep_audio=True,
)

# Convert video to GIF
convert_video("input.mp4", "output_ascii.gif", width=80, fps=12)

# Stream video or YouTube link directly in terminal
play_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", color_mode="cyan", loop=False)
```

---

## ⚡ Performance Architecture

`asciify-graphic` is engineered for high throughput:
1. **Vectorized Character Mapping**: Grayscale luminance quantization and character lookups run in native C via NumPy arrays.
2. **Glyph Atlas Blitting**: Font glyph alpha masks are pre-rendered once into an atlas `(N, char_h, char_w, 1)`. Frame compositing operates via vectorized broadcast multiplication, achieving **~60+ FPS per CPU core** for HD frames.
3. **Run-Length Optimized ANSI**: Adjacent terminal characters sharing identical RGB colors are collapsed into single escape sequences, minimizing string overhead and maximizing terminal refresh rates.
4. **Self-Contained FFmpeg Muxing**: Direct H.264 video streaming and audio muxing without requiring external system package installations.
5. **Smart URL & YouTube Caching**: Direct images and YouTube streams are downloaded once to local cache with SHA-256 validation to avoid redundant downloads.

---

## 🧪 Testing

Run the test suite with `pytest`:

```bash
pytest -v
```

All 28 unit and integration tests verify image conversion, video rendering, audio muxing, glyph atlas rasterization, URL downloads, YouTube format merging, and CLI dispatch.

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
