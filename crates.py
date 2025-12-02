#!/usr/bin/env python3
"""
Script to create a new Serato crate from a music directory using cratedigger.
"""

import sys
from pathlib import Path


from cratedigger.serato.crate import SeratoCrate


def create_crate_from_tracks(track_paths: list[str], crate_name: str, serato_dir: str = None):
    """
    Create a Serato crate from a list of track paths.

    Args:
        track_paths: List of file paths to music files
        crate_name: Name for the crate
        serato_dir: Path to _Serato_ directory (optional)
    """
    
    print(f"Creating crate: {crate_name}")
    print(f"Tracks: {len(track_paths)}")
    
    # Create SeratoCrate
    crate = SeratoCrate()
    # Use 'sync' as the parent crate and the provided name as the subcrate
    crate.crate_name = f"sync{SeratoCrate.delimiter}{crate_name}"
    
    # Convert relative paths to absolute paths
    absolute_track_paths = []
    for track_path in track_paths:
        track_path_obj = Path(track_path)
        if not track_path_obj.is_absolute():
            # Make relative to current working directory
            absolute_track_paths.append(str(track_path_obj.resolve()))
        else:
            absolute_track_paths.append(track_path)
    
    crate.tracks = absolute_track_paths
    
    # Set default columns (these are what Serato shows in the crate view)
    crate.columns = ['song', 'artist', 'album', 'bpm', 'label', 'grouping']
    
    # Determine Serato directory
    if serato_dir:
        serato_path = Path(serato_dir)
        if not serato_path.exists():
            print(f"Error: Serato directory does not exist: {serato_path}")
            return False
        crates_path = serato_path / "Subcrates"
    else:
        # Use default Serato directory
        crates_path = Path.home() / "Music" / "_Serato_" / "Subcrates"
    
    print(f"Writing crate to: {crates_path}")
    
    # Write the crate
    crate.write_crate(str(crates_path))
    
    print("✓ Crate created successfully!")
    return True




if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create Serato crates from track list"
    )
    parser.add_argument("--tracks", nargs="+", help="List of track file paths")
    parser.add_argument("--crate-name", required=True, help="Name for the crate")
    parser.add_argument("--serato-dir", help="Path to _Serato_ directory (optional)")

    args = parser.parse_args()

    print("Serato Crate Creator")
    print("=" * 50)

    if not args.tracks:
        print("Error: No tracks provided. Use --tracks to specify track files.")
        exit(1)

    success = create_crate_from_tracks(args.tracks, args.crate_name, args.serato_dir)

    if success:
        print("\n✓ Crate creation completed successfully!")
        print("You can now open Serato and see your new crates.")
    else:
        print("\n✗ Crate creation failed.")
