#!/usr/bin/env python3
"""
This script
- reads all the songs in SONGS_DIR
- creates a dict[playlist_name: list[song_path]] of songs by playlist where playlist is read from the album tag comma delimited
    eg, song "soundcloud/CACHE/[id=9VgodugIFsI] Mr Breaker (Extended Mix).mp3" has album tag "bounce inc, tech support, lucky thursday"
    this song should be added to the "bounce inc", "tech support", and "lucky thursday" playlists
- then creates a crate create_crate_from_tracks(track_paths: list[str], playlist_name: str) for each playlist

uses crates.create_crate_from_tracks
"""

from collections import defaultdict
import json
from pathlib import Path
from typing import DefaultDict, Dict, List
from mutagen import File
from crates import create_crate_from_tracks


SONGS_DIR = Path("~/Music/soundcloud/CACHE").expanduser()
PlaylistName = str
SongPath = Path

# Blacklist of tags to exclude
BLACKLISTED_TAGS = {
    "ahhh-freak-shit",
    "Todd Terje remixes",
    "New Prog",
    "housey stuff",
    "Dark Disco - EBM _ Electro _ Industrial _ Techno _ Italo Disco _ Vocals _ Punk _ Berlin Style",
    "Reginald\u2019s Downfall",
    "X-PRESSINGS Edit Series. By XPRESS",
    "Groovy Disco and R&B Mix at a New York Basement Party | Tinzo",
    "hard groove",
    "Tunes 69",
    "lighter techno",
}


def build_playlist_song_map() -> Dict[PlaylistName, List[SongPath]]:
    playlist_to_songs: DefaultDict[PlaylistName, List[SongPath]] = defaultdict(list)

    for song_file in SONGS_DIR.iterdir():
        if song_file.is_file() and song_file.suffix.lower() in [
            ".mp3",
            ".wav",
            ".flac",
            ".aif",
            ".m4a",
            ".ogg",
        ]:
            # Skip files with characters outside BMP (e.g. emojis) as they break Serato crate format
            if any(ord(c) > 0xFFFF for c in song_file.name):
                print(f"Skipping file with problematic characters: {song_file.name}")
                continue

            # Get album tag from file metadata
            try:
                audio_file = File(song_file)
                album_tag = audio_file.get("TALB", [""])[0] if audio_file else ""
            except Exception as e:
                print(f"  Error reading tags: {e}")
                album_tag = ""

            if album_tag:
                playlists: List[str] = [
                    p.strip() for p in album_tag.split(",") if p.strip()
                ]
                for playlist in playlists:
                    if playlist not in BLACKLISTED_TAGS:
                        playlist_to_songs[playlist].append(song_file)
    return dict(playlist_to_songs)


def sync_crates():
    playlist_to_songs = build_playlist_song_map()
    for playlist in sorted(playlist_to_songs.keys()):
        songs = playlist_to_songs[playlist]
        create_crate_from_tracks([str(song) for song in songs], playlist)


if __name__ == "__main__":
    sync_crates()
    print("✓ All crates created successfully!")
