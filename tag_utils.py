import os
from pathlib import Path
from typing import Union

from mutagen.id3 import ID3, Frame, ID3NoHeaderError


def tag_mp3(
    mp3_path: Union[str, Path], tag_name: str, tag_frame: Frame, label: str, value: str
) -> bool:
    """
    Tag an MP3 file with the given tag name and frame, preserving all other tags.
    Prints a consistent update message.
    Returns True if successful, False otherwise.
    """
    try:
        audio = ID3(mp3_path)
    except ID3NoHeaderError:
        audio = ID3()
    audio.setall(tag_name, [tag_frame])
    audio.save(mp3_path)
    print(f"Updated {os.path.basename(str(mp3_path))}: {label}={value}")
    return True
