#!/usr/bin/env zsh
# Music-related functions extracted from .zshrc
# Source this file in your .zshrc with: source ~/Music/music_functions.zsh

# SoundCloud sync configuration
SC_PLAYLISTS=(
  # MINE
  "https://soundcloud.com/fraser-langton/sets/boogie"
  "https://soundcloud.com/fraser-langton/sets/bounce-inc"
  "https://soundcloud.com/fraser-langton/sets/bunene"
  "https://soundcloud.com/fraser-langton/sets/5am"
  "https://soundcloud.com/fraser-langton/sets/lucky-thursday"
  "https://soundcloud.com/fraser-langton/sets/sunset"
  "https://soundcloud.com/fraser-langton/sets/ethereal"
  "https://soundcloud.com/fraser-langton/sets/groovie"
  "https://soundcloud.com/fraser-langton/sets/sing"
  "https://soundcloud.com/fraser-langton/sets/ahhh-freak-shit"
  "https://soundcloud.com/fraser-langton/sets/house-md"
  "https://soundcloud.com/fraser-langton/sets/garage-party"

  # RECORDS
  # "https://soundcloud.com/t-amsterdam-dance-capital"
  # "https://soundcloud.com/polyamor-berlin"

  # OTHER
  # "https://soundcloud.com/andy-supre-829204750/sets/your-favourite-hard-rave"
  # "https://soundcloud.com/andy-supre-829204750/sets/your-favourite-rave"
  # "https://soundcloud.com/diarmuid-healy-281028151/sets/tunes-69"
  # "https://soundcloud.com/xpressaudio/sets/x-pressings-edit-series"
  # "https://soundcloud.com/davide-giorlando-73215247/sets/groovy-disco-and-r-b-mix-at-a"
  # "https://soundcloud.com/toddterje/sets/todd-terje-remixes"
  # "https://soundcloud.com/ladytronica/sets/dark-disco"
)
SC_BASE_DIR="/Users/fraser.langton/Music/soundcloud"
SC_CACHE_DIR="$SC_BASE_DIR/CACHE"
SC_PLAYLIST_DIR="$SC_BASE_DIR/playlists"
SC_ARCHIVE_FILE="$SC_CACHE_DIR/downloaded.txt"
SC_OUTPUT_TEMPLATE="[id=%(id)s] %(title)s.%(ext)s"

# Single playlist sync function
sc_sync() {
  url="${1:-https://soundcloud.com/fraser-langton/sets/tracks}"
  # Extract playlist name from URL (last part after /)
  playlist_name=$(basename "$url")
  base_dir="/Users/fraser.langton/Music/soundcloud"
  target_dir="$base_dir/$playlist_name"
  archive_file="$target_dir/downloaded.txt"
  mkdir -p "$target_dir"
  yt-dlp -x --audio-format mp3 --audio-quality 320k \
    -o "%(title)s.%(ext)s" \
    --add-metadata \
    --embed-thumbnail \
    --write-thumbnail \
    --download-archive "$archive_file" \
    --parse-metadata "id:%(id)s" \
    -P "$target_dir" \
    "$url"
}

# Batch sync all playlists to cache and create JSON manifests
sc_sync_songs() {
  mkdir -p "$SC_CACHE_DIR"
  mkdir -p "$SC_PLAYLIST_DIR"

  for url in "${SC_PLAYLISTS[@]}"; do
    playlist_name=$(basename "$url")
    # playlist_dir="$SC_PLAYLIST_DIR/$playlist_name"
    # mkdir -p "$playlist_dir"

    # Dump playlist info as JSON
    echo "Creating JSON for playlist: $playlist_name"
    if yt-dlp --flat-playlist -J "$url" > "$SC_PLAYLIST_DIR/$playlist_name.json"; then
      echo "✓ Successfully created $playlist_name.json"
    else
      echo "✗ Failed to create $playlist_name.json (Error: $?)"
    fi

    # Download tracks to cache
    yt-dlp -x --audio-format mp3 --audio-quality 320k \
      -o "$SC_CACHE_DIR/$SC_OUTPUT_TEMPLATE" \
      --add-metadata \
      --embed-thumbnail \
      --write-thumbnail \
      --download-archive "$SC_ARCHIVE_FILE" \
      --parse-metadata "id:%(id)s" \
      "$url"

    # Delete MP3s longer than 30 minutes from CACHE
    find "$SC_CACHE_DIR" -type f -name "*.mp3" | while read -r mp3; do
      duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$mp3")
      # Only proceed if duration is a number
      if [[ $duration =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
        if (( $(echo "$duration > 1800" | bc -l) )); then
          echo "🗑️  Deleting $mp3 (duration: ${duration}s > 1800s)"
          rm -f "$mp3"
        fi
      fi
    done

    # Symlink all .mp3 files for this playlist from CACHE to playlist dir
    # if [ -f "$SC_PLAYLIST_DIR/$playlist_name.json" ]; then
    #   jq -r '.entries[].id' "$SC_PLAYLIST_DIR/$playlist_name.json" | while read -r id; do
    #     for mp3 in "$SC_CACHE_DIR"/"[id=$id]"*.mp3(N); do
    #       if [[ -f "$mp3" ]]; then
    #         ln -sf "$mp3" "$playlist_dir/$(basename "$mp3")"
    #       fi
    #     done
    #   done
    # fi
  done

  # Clean up photo files in CACHE and all playlist dirs
  find "$SC_CACHE_DIR" "$SC_PLAYLIST_DIR" -type f \( -iname '*.jpg' -o -iname '*.webp' -o -iname '*.png' \) -delete
}

# Run key detection on all songs in SoundCloud cache
sc_analyze_keys() {
  echo "🎵 Analyzing keys for all SoundCloud tracks..."
  
  # Check if our libKeyFinder CLI tool is available
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  keyfinder_tool="$script_dir/keyfinder_cli"
  if [[ ! -f "$keyfinder_tool" ]]; then
    echo "⚠️  KeyFinder CLI tool not found at: $keyfinder_tool"
    echo "   Make sure keyfinder_cli is available in the music-scripts directory"
    return 1
  fi
  
  # Create results file if it doesn't exist
  results_file="$SC_CACHE_DIR/key_analysis_results.txt"
  mkdir -p "$SC_CACHE_DIR"
  touch "$results_file"
  
  # Count total MP3 files
  total_files=$(find "$SC_CACHE_DIR" -name "*.mp3" -type f | wc -l | tr -d ' ')
  echo "📁 Found $total_files MP3 files in cache directory"
  
  if [[ $total_files -eq 0 ]]; then
    echo "❌ No MP3 files found in $SC_CACHE_DIR"
    echo "   Run 'sc_sync_all' first to download tracks"
    return 1
  fi
  
  # Process each MP3 file - using array to avoid subshell issues
  processed=0
  skipped=0
  failed=0
  
  # Create array of MP3 files
  mp3_files=()
  while IFS= read -r -d '' file; do
    mp3_files+=("$file")
  done < <(find "$SC_CACHE_DIR" -name "*.mp3" -type f -print0)
  
  for mp3_file in "${mp3_files[@]}"; do
    # Use relative path from SC_CACHE_DIR for uniqueness
    filename="${mp3_file#$SC_CACHE_DIR/}"
    
    # Check if this file has already been processed (exact match at start of line)
    if grep -Fxq "$filename|" <(cut -d'|' -f1 "$results_file" | sed 's/$/|/'); then
      echo "⏭️  Skipping already processed: $filename"
      ((skipped++))
      continue
    fi
    
    echo "🎼 Analyzing: $filename"
    
    # Run key detection
    if key_result=$("$keyfinder_tool" "$mp3_file" 2>/dev/null); then
      # Save result to file (no date)
      echo "$filename|$key_result" >> "$results_file"
      echo "    ✓ Key detected: $key_result"
      ((processed++))
    else
      echo "$filename|ERROR" >> "$results_file"
      echo "    ✗ Key detection failed"
      ((failed++))
    fi
    
    # Progress indicator
    current=$((processed + skipped + failed))
    if (( current % 10 == 0 )); then
      echo "📊 Progress: $current/$total_files files processed"
    fi
  done
  
  # De-duplicate results file (optional but recommended)
  sort -u -o "$results_file" "$results_file"
  
  # Final summary
  echo ""
  echo "🎯 Key Analysis Complete!"
  echo "========================"
  echo "📈 Processed: $processed files"
  echo "⏭️  Skipped: $skipped files (already analyzed)"
  echo "❌ Failed: $failed files"
  echo "📄 Results saved to: $results_file"
  echo ""
  echo "💡 View results with: sc_show_keys"
}

# Show key analysis results
sc_show_keys() {
  results_file="$SC_CACHE_DIR/key_analysis_results.txt"
  
  if [[ ! -f "$results_file" ]]; then
    echo "❌ No key analysis results found"
    echo "   Run 'sc_analyze_keys' first"
    return 1
  fi
  
  echo "🎯 SoundCloud Key Analysis Results:"
  echo "==================================="
  echo ""
  
  # Show summary stats
  total_analyzed=$(wc -l < "$results_file" | tr -d ' ')
  successful=$(grep -c -v "|ERROR|" "$results_file" || echo "0")
  errors=$(grep -c "|ERROR|" "$results_file" || echo "0")
  
  echo "📊 Summary:"
  echo "  Total analyzed: $total_analyzed"
  echo "  Successful: $successful"
  echo "  Errors: $errors"
  echo ""
  
  # Show results by key
  echo "🎼 Results by Key:"
  echo ""
  
  # Extract keys and count them
  grep -v "|ERROR|" "$results_file" | cut -d'|' -f2 | sort | uniq -c | sort -nr | while read -r count key; do
    printf "  %-8s: %2d tracks\n" "$key" "$count"
  done
  
  echo ""
  echo "📄 Full results file: $results_file"
  echo "💡 Search for specific key: grep '|Am|' '$results_file'"
}

# Find tracks by key
sc_find_key() {
  if [[ -z "$1" ]]; then
    echo "Usage: sc_find_key <key>"
    echo "Examples:"
    echo "  sc_find_key 'Am'     # Find A minor tracks"
    echo "  sc_find_key '(8A)'   # Find Camelot 8A tracks"
    echo "  sc_find_key 'C'      # Find C major tracks"
    return 1
  fi
  
  results_file="$SC_CACHE_DIR/key_analysis_results.txt"
  
  if [[ ! -f "$results_file" ]]; then
    echo "❌ No key analysis results found"
    echo "   Run 'sc_analyze_keys' first"
    return 1
  fi
  
  search_key="$1"
  echo "🔍 Searching for tracks in key: $search_key"
  echo "============================================="
  
  # Search for the key in results
  matches=$(grep "|.*$search_key.*|" "$results_file")
  
  if [[ -z "$matches" ]]; then
    echo "❌ No tracks found in key: $search_key"
    echo ""
    echo "Available keys:"
    grep -v "|ERROR|" "$results_file" | cut -d'|' -f2 | sort | uniq | head -10
  else
    echo "$matches" | while IFS='|' read -r filename key timestamp; do
      echo "🎵 $filename - $key"
    done
    
    count=$(echo "$matches" | wc -l | tr -d ' ')
    echo ""
    echo "Found $count tracks in key: $search_key"
  fi
}

# Write detected keys to MP3 ID3 tags for Serato
sc_write_keys_to_tags() {
  results_file="$SC_CACHE_DIR/key_analysis_results.txt"
  
  if [[ ! -f "$results_file" ]]; then
    echo "❌ No key analysis results found"
    echo "   Run 'sc_analyze_keys' first"
    return 1
  fi
  
  echo "🏷️  Writing key information to ID3 tags..."
  echo "=========================================="
  
  # Count successful results
  successful_results=$(grep -v "|ERROR|" "$results_file")
  total_successful=$(echo "$successful_results" | wc -l | tr -d ' ')
  
  if [[ $total_successful -eq 0 ]]; then
    echo "❌ No successful key detections found"
    return 1
  fi
  
  echo "📁 Found $total_successful tracks with detected keys"
  
  processed=0
  failed=0
  
  # Process each successful result
  echo "$successful_results" | while IFS='|' read -r filename key_result timestamp; do
    mp3_file="$SC_CACHE_DIR/$filename"
    
    if [[ ! -f "$mp3_file" ]]; then
      echo "⚠️  File not found: $filename"
      ((failed++))
      continue
    fi
    
    # Extract just the key part (remove Camelot notation)
    # e.g., "Am (8A)" -> "Am"
    key_only=$(echo "$key_result" | sed 's/ (.*)$//')
    
    # Extract Camelot notation and convert to lowercase
    # e.g., "Am (8A)" -> "8a"
    camelot_only=$(echo "$key_result" | sed -n 's/.*(\([^)]*\)).*/\1/p' | tr '[:upper:]' '[:lower:]')
    
    echo "🎵 Writing label '$camelot_only' and grouping '$key_only' to: $filename"
    
    # Write to Label and Grouping fields
    # TPUB = Publisher/Label (for Serato label field)
    # TIT1 = Content group description/Grouping
    if id3v2 --TPUB "$camelot_only" --TIT1 "$key_only" "$mp3_file" 2>/dev/null; then
      echo "    ✓ Successfully tagged"
      ((processed++))
    else
      echo "    ✗ Failed to write tag"
      ((failed++))
    fi
    
    # Progress indicator
    if (( (processed + failed) % 20 == 0 )); then
      echo "📊 Progress: $((processed + failed))/$total_successful files processed"
    fi
  done
  
  echo ""
  echo "🎯 ID3 Tag Writing Complete!"
  echo "============================"
  echo "✅ Successfully tagged: $processed files"
  echo "❌ Failed: $failed files"
  echo ""
  echo "📋 Next steps for Serato:"
  echo "  1. In Serato, add 'label' column to your view"
  echo "  2. Click 'Rescan ID3 Tags' button"  
  echo "  3. Your keys will appear in the Label column!"
}

# Delete a specific track by ID
sc_delete_song() {
  if [[ -z "$1" ]]; then
    echo "Usage: sc_delete_song <track_id>"
    return 1
  fi

  local track_id="$1"
  local deleted=0

  # Delete all matching MP3 files from cache
  for mp3 in "$SC_CACHE_DIR"/"[id=$track_id]"*.mp3(N); do
    if [[ -f "$mp3" ]]; then
      echo "🗑️  Deleting $mp3"
      rm -f "$mp3"
      ((deleted++))
    fi
  done

  if (( deleted == 0 )); then
    echo "⚠️  No MP3 files found for track ID: $track_id"
  fi

  # Remove the line from downloaded.txt
  if [[ -f "$SC_ARCHIVE_FILE" ]]; then
    grep -v " $track_id" "$SC_ARCHIVE_FILE" > "$SC_ARCHIVE_FILE.tmp" && mv "$SC_ARCHIVE_FILE.tmp" "$SC_ARCHIVE_FILE"
    echo "✅ Removed track ID $track_id from $SC_ARCHIVE_FILE"
  else
    echo "⚠️  Archive file not found: $SC_ARCHIVE_FILE"
  fi
}

# Main sync function that runs the full pipeline
sc_sync_all() {
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  sc_sync_songs
  sc_analyze_keys
  "$script_dir/write_key_tags.py"
  "$script_dir/write_playlist_tags.py"
  wait
}

echo "🎵 Music functions loaded! Available commands:"
echo "  sc_sync <url>           - Sync single playlist"
echo "  sc_sync_songs          - Sync all configured playlists"
echo "  sc_analyze_keys        - Analyze keys for all cached tracks"
echo "  sc_show_keys           - Show key analysis results"
echo "  sc_find_key <key>      - Find tracks by key"
echo "  sc_write_keys_to_tags  - Write keys to ID3 tags"
echo "  sc_delete_song <id>    - Delete track by ID"
echo "  sc_sync_all            - Run full sync pipeline"
