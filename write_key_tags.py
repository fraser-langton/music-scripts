#!/usr/bin/env uv run python
import os
import re

from mutagen.id3 import TIT1, TPUB, TPE1, ID3, ID3NoHeaderError

from tag_utils import tag_mp3

CACHE_DIR = os.path.expanduser("~/Music/soundcloud/CACHE")
RESULTS_FILE = os.path.join(CACHE_DIR, "key_analysis_results.txt")


def has_key_in_artist(artist_text: str) -> bool:
    """Check if artist text already contains a Camelot key in parentheses."""
    # Pattern to match Camelot keys like (5A), (10B), (1A), etc.
    camelot_pattern = r'\(\d+[AB]\)'
    return bool(re.search(camelot_pattern, artist_text))


def get_current_artist(mp3_path: str) -> str:
    """Get the current artist tag from the MP3 file."""
    try:
        audio = ID3(mp3_path)
        artist_tag = audio.get('TPE1')
        if artist_tag and artist_tag.text:
            return artist_tag.text[0]
        return ""
    except (ID3NoHeaderError, AttributeError, IndexError):
        return ""


def build_key_tag_map():
    tag_map = {}
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|ERROR" in line:
                continue
            parts = line.split("|")
            if len(parts) < 2:
                continue
            filename, key_result = parts[0], parts[1]
            mp3_path = os.path.join(CACHE_DIR, filename)
            if not os.path.isfile(mp3_path):
                continue
            key_only = key_result.split(" (")[0]
            camelot_only = ""
            if "(" in key_result and ")" in key_result:
                camelot_only = key_result.split("(")[-1].split(")")[0].lower()
            tag_map[mp3_path] = (key_only, camelot_only)
    return tag_map


def write_key_tags(tag_map):
    updated = 0
    for mp3_path, (key_only, camelot_only) in tag_map.items():
        # Write the existing tags (Label and Grouping)
        tag_mp3(
            mp3_path, "TPUB", TPUB(encoding=3, text=camelot_only), "Label", camelot_only
        )
        tag_mp3(mp3_path, "TIT1", TIT1(encoding=3, text=key_only), "Grouping", key_only)
        
        # Update artist tag with key if not already present
        current_artist = get_current_artist(mp3_path)
        if current_artist and not has_key_in_artist(current_artist):
            new_artist = f"{current_artist} ({camelot_only})"
            tag_mp3(mp3_path, "TPE1", TPE1(encoding=3, text=new_artist), "Artist", new_artist)
        
        updated += 1
    print(f"\nUpdated {updated} files.")


def main():
    tag_map = build_key_tag_map()
    write_key_tags(tag_map)


if __name__ == "__main__":
    main()
