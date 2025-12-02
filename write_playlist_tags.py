#!/usr/bin/env uv run python
import json
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List

from mutagen.id3 import TALB

from tag_utils import tag_mp3

CACHE_DIR = Path.home() / "Music" / "soundcloud" / "CACHE"
PLAYLISTS_DIR = Path.home() / "Music" / "soundcloud" / "playlists"


def build_playlist_tag_map() -> Dict[str, str]:
    song_to_playlists: DefaultDict[str, List[str]] = defaultdict(list)
    for playlist_file in PLAYLISTS_DIR.glob("*.json"):
        try:
            with playlist_file.open("r", encoding="utf-8") as f:
                data: dict = json.load(f)
        except Exception as e:
            print(f"Error reading {playlist_file.name}: {e}")
            continue
        
        if data is None:
            print(f"Warning: {playlist_file.name} contains null data")
            continue
            
        # Handle different JSON formats explicitly
        if "youtube.com" in data.get("webpage_url", "") or "extractor" in data and "youtube" in data["extractor"].lower():
            # YouTube format: use title directly
            playlist_name: str = data.get("title", playlist_file.stem)
        elif "soundcloud.com" in data.get("webpage_url", "") or "extractor" in data and "soundcloud" in data["extractor"].lower():
            # SoundCloud format: use title directly  
            playlist_name: str = data.get("title", playlist_file.stem)
        else:
            # Fallback: use filename
            playlist_name: str = playlist_file.stem
            
        # Clean up playlist name for tagging (replace problematic characters)
        playlist_name = playlist_name.replace("/", "_").replace("\\", "_")
        
        for entry in data.get("entries", []):
            song_id: str = entry.get("id")
            if song_id:
                song_to_playlists[song_id].append(playlist_name)
    tag_map = {}
    for mp3_file in CACHE_DIR.glob("*.mp3"):
        name: str = mp3_file.name
        if "[id=" not in name:
            continue
        try:
            id_part: str = name.split("[id=")[1].split("]")[0]
        except Exception:
            continue
        playlists: List[str] = song_to_playlists.get(id_part, [])
        if not playlists:
            continue
        tag_map[mp3_file] = ", ".join(playlists)
    return tag_map


def write_playlist_tags(tag_map: Dict[Path, str]):
    updated = 0
    for mp3_file, tag in tag_map.items():
        tag_mp3(mp3_file, "TALB", TALB(encoding=3, text=tag), "Album", tag)
        updated += 1
    print(f"\nUpdated {updated} files.")


def main():
    tag_map = build_playlist_tag_map()
    write_playlist_tags(tag_map)


if __name__ == "__main__":
    main()
