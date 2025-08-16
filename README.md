# Music Scripts

Scripts for SoundCloud sync, key analysis, and DJ software integration.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/fraser-langton/music-scripts.git
cd music-scripts
```

2. Install dependencies:
```bash
brew install yt-dlp ffmpeg id3v2 libkeyfinder libsndfile fftw
```

3. Build the keyfinder CLI tool:
```bash
make keyfinder_cli
```

4. Add to your shell (zsh):
```bash
echo 'source "$HOME/Music/music-scripts/music_functions.zsh"' >> ~/.zshrc
source ~/.zshrc
```

5. Configure your SoundCloud playlists by editing the `SC_PLAYLISTS` array in `music_functions.zsh`

## Usage

Run `sc_sync_all` to download, analyze keys, and tag your music.
