#!/usr/bin/env python3
"""
This script
- reads all the songs in SONGS_DIR
- creates a dict[playlist_name: list[song_path]] of songs by playlist where playlist is read from the album tag comma delimited
    eg, song "soundcloud/CACHE/[id=9VgodugIFsI] Mr Breaker (Extended Mix).mp3" has album tag "bounce inc, tech support, lucky thursday"
    this song should be added to the "bounce inc", "tech support", and "lucky thursday" playlists
- then creates a Rekordbox playlist for each playlist

uses the same logic as sync-crates.py but outputs to Rekordbox format
"""

from collections import defaultdict
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import DefaultDict, Dict, List
from mutagen import File


SONGS_DIR = Path("~/Music/soundcloud/CACHE").expanduser()
REKORDBOX_DIR = Path("~/Music/rekordbox").expanduser()
PlaylistName = str
SongPath = Path

# Blacklist of tags to exclude
BLACKLISTED_TAGS = {
    "ahhh-freak-shit",
    "Todd Terje remixes",
    "New Prog",
    "housey stuff",
    "Dark Disco - EBM _ Electro _ Industrial _ Techno _ Italo Disco _ Vocals _ Punk _ Berlin Style",
    "Reginald's Downfall",
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


def create_m3u_playlists(playlist_to_songs: Dict[PlaylistName, List[SongPath]]) -> None:
    """
    Create M3U playlist files that Rekordbox can import.
    
    Args:
        playlist_to_songs: Dictionary mapping playlist names to track paths
    """
    # Ensure output directory exists
    REKORDBOX_DIR.mkdir(parents=True, exist_ok=True)
    
    for playlist_name, track_paths in playlist_to_songs.items():
        # Create M3U file
        m3u_file = REKORDBOX_DIR / f"{playlist_name}.m3u"
        
        with open(m3u_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for track_path in track_paths:
                f.write(f"{track_path.absolute()}\n")
        
        print(f"Created M3U playlist: {playlist_name} ({len(track_paths)} tracks)")
    
    print(f"\n✓ Created {len(playlist_to_songs)} M3U playlists!")
    print("Import these .m3u files into Rekordbox using File → Import → Playlist")


def sync_rekordbox_playlists():
    """Create M3U playlists from music files."""
    playlist_to_songs = build_playlist_song_map()
    
    print(f"Found {len(playlist_to_songs)} playlists to create")
    print(f"Output directory: {REKORDBOX_DIR}")
    
    # Create M3U playlist files
    create_m3u_playlists(playlist_to_songs)


if __name__ == "__main__":
    sync_rekordbox_playlists()

