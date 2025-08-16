# Music Scripts

Scripts for SoundCloud sync, key analysis, and DJ software integration.

## Quick Start

1. **Clone and setup**:
```bash
git clone https://github.com/fraser-langton/music-scripts.git
cd music-scripts
```

2. **Install dependencies**:
```bash
brew install yt-dlp ffmpeg id3v2 libkeyfinder libsndfile fftw
```

3. **Add to shell**:
```bash
echo 'source "$HOME/Music/music-scripts/music_functions.zsh"' >> ~/.zshrc
source ~/.zshrc
```

4. **Run the sync**:
```bash
sc_sync_all
```

### Optional: Build keyfinder_cli yourself
If you want to build the keyfinder CLI from source instead of using the included binary:
```bash
make keyfinder_cli
```

## Configuration

### SoundCloud Playlists
Edit the `SC_PLAYLISTS` array in `music_functions.zsh` to add your playlist URLs:
```bash
SC_PLAYLISTS=(
    "https://soundcloud.com/user/sets/playlist1"
    "https://soundcloud.com/user/sets/playlist2"
)
```

### Cache Directory
By default, music is cached in `~/Music/soundcloud/CACHE/`. Change `SC_CACHE_DIR` to use a different location.

### Key Analysis Settings
- Modify `KEYFINDER_CLI` path if you install keyfinder elsewhere
- Adjust `BATCH_SIZE` for key analysis performance

## Available Functions

### Core Functions
- `sc_sync_all` - Complete sync: download, analyze keys, and tag
- `sc_sync_playlists` - Download music from configured playlists
- `sc_analyze_keys` - Analyze musical keys for cached files
- `sc_write_keys_to_tags` - Write key data to MP3 ID3 tags

### Utility Functions
- `sc_show_stats` - Display cache statistics
- `sc_clean_cache` - Clean up cache directory
- `sc_list_playlists` - Show configured playlists
