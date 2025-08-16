#!/usr/bin/env python3
import os

from mutagen.id3 import TIT1, TPUB

from tag_utils import tag_mp3

CACHE_DIR = os.path.expanduser("~/Music/soundcloud/CACHE")
RESULTS_FILE = os.path.join(CACHE_DIR, "key_analysis_results.txt")


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
        tag_mp3(
            mp3_path, "TPUB", TPUB(encoding=3, text=camelot_only), "Label", camelot_only
        )
        tag_mp3(mp3_path, "TIT1", TIT1(encoding=3, text=key_only), "Grouping", key_only)
        updated += 1
    print(f"\nUpdated {updated} files.")


def main():
    tag_map = build_key_tag_map()
    write_key_tags(tag_map)


if __name__ == "__main__":
    main()
