from setuptools import setup, find_packages

setup(
    name="asciify-graphic",
    version="1.2.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "numpy>=1.20",
        "pillow>=9.0",
        "opencv-python-headless>=4.5",
        "imageio>=2.20",
        "imageio-ffmpeg>=0.4",
        "click>=8.0",
        "rich>=12.0",
        "requests>=2.25",
        "yt-dlp>=2024.0.0",
    ],
    entry_points={
        "console_scripts": [
            "asciify = asciify.cli:main",
            "asciify-graphic = asciify.cli:main",
        ],
    },
)
