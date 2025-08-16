#!/usr/bin/env python3
"""
Song Information Extractor
Extracts artist, title, remix info, and other metadata from song filenames
using comprehensive regex patterns and compares with existing ID3 tags.
"""

import re
import os
import glob
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

try:
    from mutagen import File
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    print("⚠️  mutagen library not available. Install with: pip install mutagen")
    print("   ID3 tag comparison will be skipped.")

@dataclass
class SongInfo:
    """Container for extracted song information"""
    artist: Optional[str] = None
    title: Optional[str] = None
    remix: Optional[str] = None
    record_label: Optional[str] = None
    featuring: Optional[str] = None
    soundcloud_id: Optional[str] = None
    version: Optional[str] = None
    confidence: float = 0.0
    original_filename: str = ""
    pattern_used: str = ""
    
    # ID3 tag information
    id3_artist: Optional[str] = None
    id3_title: Optional[str] = None
    id3_album: Optional[str] = None
    id3_year: Optional[str] = None
    id3_genre: Optional[str] = None

class SongInfoExtractor:
    def __init__(self):
        # Define regex patterns in order of specificity
        self.patterns = [
            # 1. SoundCloud ID patterns (most specific)
            {
                'pattern': r'^\[id=(\d+)\]\s*(.+?)\s*[-–—]\s*(.+?)(?:\s*\[(.+?)\])?\s*$',
                'name': 'SoundCloud ID with Artist-Title-Brackets',
                'groups': ['soundcloud_id', 'artist', 'title', 'remix'],
                'confidence': 0.95
            },
            {
                'pattern': r'^\[id=(\d+)\]\s*(.+?)(?:\s*\((.+?)\))?\s*$',
                'name': 'SoundCloud ID with Title-Parentheses',
                'groups': ['soundcloud_id', 'title', 'version'],
                'confidence': 0.9
            },
            
            # 2. Featuring artist patterns
            {
                'pattern': r'^(.+?)\s*(?:feat\.?|ft\.?|featuring)\s*(.+?)\s*[-–—]\s*(.+?)(?:\s*\[(.+?)\])?\s*$',
                'name': 'Artist feat. Artist - Title with Brackets',
                'groups': ['artist', 'featuring', 'title', 'remix'],
                'confidence': 0.85
            },
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*(?:feat\.?|ft\.?|featuring)\s*(.+?)(?:\s*\[(.+?)\])?\s*$',
                'name': 'Artist - Title feat. Artist with Brackets',
                'groups': ['artist', 'title', 'featuring', 'remix'],
                'confidence': 0.85
            },
            
            # 3. Standard Artist - Title with brackets/parentheses
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*\[(.+?)\]\s*$',
                'name': 'Artist - Title [Remix/Label]',
                'groups': ['artist', 'title', 'remix'],
                'confidence': 0.8
            },
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*\((.+?)\)\s*$',
                'name': 'Artist - Title (Version)',
                'groups': ['artist', 'title', 'version'],
                'confidence': 0.8
            },
            
            # 4. Complex multi-part patterns
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*\((.+?)\s+Remix\)\s*\[(.+?)\]\s*$',
                'name': 'Artist - Title (Artist Remix) [Label]',
                'groups': ['artist', 'title', 'remix', 'record_label'],
                'confidence': 0.85
            },
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*\((.+?)\)\s*\[(.+?)\]\s*$',
                'name': 'Artist - Title (Version) [Label]',
                'groups': ['artist', 'title', 'version', 'record_label'],
                'confidence': 0.8
            },
            
            # 5. Premiere/Exclusive patterns
            {
                'pattern': r'^(?:Premiere|PREMIERE|Premiere：)\s*(.+?)\s*[-–—]\s*(.+?)(?:\s*\((.+?)\))?\s*$',
                'name': 'Premiere: Artist - Title (Version)',
                'groups': ['artist', 'title', 'version'],
                'confidence': 0.75
            },
            
            # 6. Free download patterns
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*\[Free\s+(?:DL|Download)\]\s*$',
                'name': 'Artist - Title [Free DL]',
                'groups': ['artist', 'title'],
                'confidence': 0.7
            },
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*\(FREE\s+(?:DL|Download)\)\s*$',
                'name': 'Artist - Title (FREE DL)',
                'groups': ['artist', 'title'],
                'confidence': 0.7
            },
            
            # 7. Extended mix patterns
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*\(Extended\s+(?:Mix|Version)\)\s*$',
                'name': 'Artist - Title (Extended Mix)',
                'groups': ['artist', 'title'],
                'confidence': 0.75
            },
            
            # 8. Mashup patterns
            {
                'pattern': r'^(.+?)\s+Mashup\s*\[(.+?)\s*[-–—]\s*(.+?)\]\s*$',
                'name': 'Artist Mashup [Track1 - Track2]',
                'groups': ['artist', 'title', 'remix'],
                'confidence': 0.7
            },
            
            # 9. Preview/Out Now patterns
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*\(Preview\)\s*\(Taken from (.+?)\)\s*\(Out Now\)\s*$',
                'name': 'Artist - Title (Preview)(Taken from Label)(Out Now)',
                'groups': ['artist', 'title', 'record_label'],
                'confidence': 0.65
            },
            
            # 10. Simple Artist - Title (fallback)
            {
                'pattern': r'^(.+?)\s*[-–—]\s*(.+?)\s*$',
                'name': 'Artist - Title',
                'groups': ['artist', 'title'],
                'confidence': 0.6
            },
            
            # 11. Title-only fallback (lowest confidence)
            {
                'pattern': r'^([^-\n]+?)\s*$',
                'name': 'Title Only',
                'groups': ['title'],
                'confidence': 0.3
            }
        ]
        
        # Compile all patterns
        for p in self.patterns:
            p['compiled'] = re.compile(p['pattern'], re.IGNORECASE | re.MULTILINE)
    
    def clean_filename(self, filename: str) -> str:
        """Clean filename by removing extension and normalizing"""
        # Remove file extension
        name = os.path.splitext(filename)[0]
        # Normalize multiple spaces
        name = re.sub(r'\s+', ' ', name)
        # Trim whitespace
        name = name.strip()
        return name
    
    def read_id3_tags(self, filepath: str) -> Dict[str, str]:
        """Read ID3 tags from MP3 file"""
        if not MUTAGEN_AVAILABLE:
            return {}
        
        try:
            # Try EasyID3 first (more common)
            audio = EasyID3(filepath)
            if audio:
                return {
                    'artist': audio.get('artist', [None])[0],
                    'title': audio.get('title', [None])[0],
                    'album': audio.get('album', [None])[0],
                    'date': audio.get('date', [None])[0],
                    'genre': audio.get('genre', [None])[0]
                }
            
            # Fallback to ID3
            audio = ID3(filepath)
            if audio:
                return {
                    'artist': str(audio.get('TPE1', [''])[0]) if 'TPE1' in audio else None,
                    'title': str(audio.get('TIT2', [''])[0]) if 'TIT2' in audio else None,
                    'album': str(audio.get('TALB', [''])[0]) if 'TALB' in audio else None,
                    'date': str(audio.get('TDRC', [''])[0]) if 'TDRC' in audio else None,
                    'genre': str(audio.get('TCON', [''])[0]) if 'TCON' in audio else None
                }
            
            # Try generic File
            audio = File(filepath)
            if audio and hasattr(audio, 'tags'):
                tags = audio.tags
                return {
                    'artist': str(tags.get('artist', [''])[0]) if 'artist' in tags else None,
                    'title': str(tags.get('title', [''])[0]) if 'title' in tags else None,
                    'album': str(tags.get('album', [''])[0]) if 'album' in tags else None,
                    'date': str(tags.get('date', [''])[0]) if 'date' in tags else None,
                    'genre': str(tags.get('genre', [''])[0]) if 'genre' in tags else None
                }
                
        except Exception as e:
            pass
        
        return {}
    
    def extract_info(self, filename: str, filepath: str = None) -> SongInfo:
        """Extract song information from filename and ID3 tags"""
        clean_name = self.clean_filename(filename)
        song_info = SongInfo(original_filename=filename)
        
        # Try each pattern in order
        for pattern_info in self.patterns:
            match = pattern_info['compiled'].match(clean_name)
            if match:
                song_info.pattern_used = pattern_info['name']
                song_info.confidence = pattern_info['confidence']
                
                # Extract groups based on pattern definition
                groups = match.groups()
                for i, group_name in enumerate(pattern_info['groups']):
                    if i < len(groups) and groups[i]:
                        value = groups[i].strip()
                        if hasattr(song_info, group_name):
                            setattr(song_info, group_name, value)
                
                break
        
        # Read ID3 tags if filepath provided
        if filepath and MUTAGEN_AVAILABLE:
            id3_tags = self.read_id3_tags(filepath)
            song_info.id3_artist = id3_tags.get('artist')
            song_info.id3_title = id3_tags.get('title')
            song_info.id3_album = id3_tags.get('album')
            song_info.id3_year = id3_tags.get('date')
            song_info.id3_genre = id3_tags.get('genre')
        
        return song_info
    
    def extract_from_directory(self, directory_path: str) -> List[SongInfo]:
        """Extract song information from all files in a directory"""
        results = []
        
        # Find all audio files
        audio_extensions = ['*.mp3', '*.wav', '*.flac', '*.m4a', '*.aac', '*.ogg']
        files = []
        for ext in audio_extensions:
            files.extend(glob.glob(os.path.join(directory_path, ext)))
        
        print(f"Found {len(files)} audio files in {directory_path}")
        print("=" * 80)
        
        for filename in sorted(files):
            song_info = self.extract_info(os.path.basename(filename), filename)
            results.append(song_info)
            
            # Print results
            print(f"📁 {song_info.original_filename}")
            print(f"   Pattern: {song_info.pattern_used} (confidence: {song_info.confidence:.2f})")
            
            if song_info.artist:
                print(f"   🎤 Artist (filename): {song_info.artist}")
            if song_info.title:
                print(f"   🎵 Title (filename): {song_info.title}")
            if song_info.remix:
                print(f"   🔄 Remix: {song_info.remix}")
            if song_info.record_label:
                print(f"   🏷️  Label: {song_info.record_label}")
            if song_info.featuring:
                print(f"   👥 Featuring: {song_info.featuring}")
            if song_info.soundcloud_id:
                print(f"   🆔 SoundCloud ID: {song_info.soundcloud_id}")
            if song_info.version:
                print(f"   📝 Version: {song_info.version}")
            
            # Print ID3 tag comparison
            if song_info.id3_artist or song_info.id3_title:
                print(f"   📋 ID3 Tags:")
                if song_info.id3_artist:
                    print(f"      🎤 Artist (ID3): {song_info.id3_artist}")
                if song_info.id3_title:
                    print(f"      🎵 Title (ID3): {song_info.id3_title}")
                if song_info.id3_album:
                    print(f"      💿 Album: {song_info.id3_album}")
                if song_info.id3_year:
                    print(f"      📅 Year: {song_info.id3_year}")
                if song_info.id3_genre:
                    print(f"      🎼 Genre: {song_info.id3_genre}")
                
                # Show comparison
                if song_info.artist and song_info.id3_artist:
                    artist_match = song_info.artist.lower() == song_info.id3_artist.lower()
                    print(f"      ✅ Artist match: {'Yes' if artist_match else 'No'}")
                if song_info.title and song_info.id3_title:
                    title_match = song_info.title.lower() == song_info.id3_title.lower()
                    print(f"      ✅ Title match: {'Yes' if title_match else 'No'}")
            
            print()
        
        return results
    
    def print_statistics(self, results: List[SongInfo]):
        """Print extraction statistics"""
        total = len(results)
        successful = sum(1 for r in results if r.confidence > 0.5)
        high_confidence = sum(1 for r in results if r.confidence > 0.8)
        medium_confidence = sum(1 for r in results if 0.5 < r.confidence <= 0.8)
        low_confidence = sum(1 for r in results if r.confidence <= 0.5)
        
        print("📊 EXTRACTION STATISTICS")
        print("=" * 50)
        print(f"Total files processed: {total}")
        print(f"Successful extractions (>0.5 confidence): {successful} ({successful/total*100:.1f}%)")
        print(f"High confidence (>0.8): {high_confidence} ({high_confidence/total*100:.1f}%)")
        print(f"Medium confidence (0.5-0.8): {medium_confidence} ({medium_confidence/total*100:.1f}%)")
        print(f"Low confidence (≤0.5): {low_confidence} ({low_confidence/total*100:.1f}%)")
        
        # Pattern usage statistics
        pattern_counts = {}
        for result in results:
            pattern = result.pattern_used
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        print("\n🔍 PATTERN USAGE:")
        for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {pattern}: {count} files")
        
        # ID3 tag statistics
        if MUTAGEN_AVAILABLE:
            files_with_id3 = sum(1 for r in results if r.id3_artist or r.id3_title)
            artist_matches = sum(1 for r in results if r.artist and r.id3_artist and 
                               r.artist.lower() == r.id3_artist.lower())
            title_matches = sum(1 for r in results if r.title and r.id3_title and 
                              r.title.lower() == r.id3_title.lower())
            
            print(f"\n🏷️  ID3 TAG STATISTICS:")
            print(f"   Files with ID3 tags: {files_with_id3} ({files_with_id3/total*100:.1f}%)")
            if files_with_id3 > 0:
                print(f"   Artist matches: {artist_matches} ({artist_matches/files_with_id3*100:.1f}%)")
                print(f"   Title matches: {title_matches} ({title_matches/files_with_id3*100:.1f}%)")

def main():
    extractor = SongInfoExtractor()
    
    # Process the CACHE directory
    cache_dir = "soundcloud/CACHE"
    if os.path.exists(cache_dir):
        print(f"🎵 Processing files in {cache_dir}")
        results = extractor.extract_from_directory(cache_dir)
        extractor.print_statistics(results)
    else:
        print(f"❌ Directory {cache_dir} not found!")

if __name__ == "__main__":
    main() 