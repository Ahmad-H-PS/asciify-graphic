"""Built-in character sets and ramp configurations for ASCII conversion."""

from typing import Dict

CHARSETS: Dict[str, str] = {
    # Dense to light ramps (assuming dark background by default)
    "standard": "@%#*+=-:. ",
    "detailed": "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. ",
    "minimal": "#*:. ",
    "blocks": "█▓▒░ ",
    "binary": "10 ",
    "dots": "⣿⣶⣤⣀ ",
    "matrix": "ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ9876543210 ",
    "ascii_simple": "#@&%?*+;:,. ",
    "slashes": "/\\|- ",
}

DEFAULT_CHARSET = "standard"


def get_charset(name_or_chars: str, invert: bool = False) -> str:
    """Get character set string by preset name or return custom string.
    
    If invert is True, reverses the character ramp.
    """
    chars = CHARSETS.get(name_or_chars.lower(), name_or_chars)
    if not chars:
        chars = CHARSETS[DEFAULT_CHARSET]
    return chars[::-1] if invert else chars
