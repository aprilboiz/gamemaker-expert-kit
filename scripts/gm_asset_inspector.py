"""
gm_asset_inspector.py - Objective Structural Asset & Metadata Extractor for Game Development.

Pure 'Sensor' tool: Fast, deterministic, and 100% factual.
Scans asset directories, inspects image dimensions, computes animation filmstrip cells,
detects tile grids, and categorizes assets by folder taxonomy and action tags.
Contains ZERO hardcoded game genres or subjective scoring—outputs clean structured facts
for the AI model to reason over.
"""

import os
import re
from typing import Any, Dict
from PIL import Image

def inspect_assets(folder_path: str) -> Dict[str, Any]:
    """
    Performs deterministic inspection on an asset folder and returns a structured inventory.
    """
    folder_path = os.path.abspath(folder_path)
    if not os.path.exists(folder_path):
        return {"error": f"Path does not exist: {folder_path}"}

    # 1. Collect genuine media files (skip system/hidden files and __MACOSX)
    image_files = []
    audio_files = []
    font_files = []

    for root, _, files in os.walk(folder_path):
        if "__MACOSX" in root or ".git" in root or ".svn" in root:
            continue
        for f in files:
            if f.startswith("."):
                continue
            ext = os.path.splitext(f)[1].lower()
            p = os.path.join(root, f)
            if ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                image_files.append(p)
            elif ext in [".wav", ".ogg", ".mp3"]:
                audio_files.append(p)
            elif ext in [".ttf", ".otf"]:
                font_files.append(p)

    if not image_files:
        return {
            "folder": folder_path,
            "error": "No image files found in folder.",
            "total_images": 0,
            "total_audio": len(audio_files)
        }

    # 2. Structural extraction
    inventory = {
        "folder_name": os.path.basename(folder_path),
        "total_images": len(image_files),
        "total_audio": len(audio_files),
        "total_fonts": len(font_files),
        "character_archetypes": set(),
        "filmstrip_animations": {},
        "discrete_animations": {},
        "environment_tilesets": [],
        "single_sprites": [],
        "detected_grid_factors": set(),
        "detected_tags": {
            "combat": set(),
            "movement": set(),
            "environment": set(),
            "ui": set(),
            "items": set()
        }
    }

    tag_dictionaries = {
        "combat": ["attack", "bite", "hurt", "hit", "dead", "die", "death", "scream", "eating", "slash", "shoot", "blood", "damage"],
        "movement": ["idle", "walk", "run", "jump", "fall", "moving", "slide", "dash", "swim", "fly", "climb"],
        "environment": ["wall", "floor", "door", "stairs", "water", "grass", "dirt", "road", "street", "tileset", "terrain", "rock", "tree"],
        "ui": ["button", "btn", "icon", "bar", "hud", "card", "trophy", "badge", "heart", "coin", "score", "menu"],
        "items": ["chest", "key", "torch", "candle", "potion", "sword", "shield", "trap", "lever", "crop", "seed", "plant", "crate"]
    }

    # Discrete animation sequence tracker (e.g. run_01.png, run_02.png)
    discrete_tracker = {}

    for p in image_files:
        fname = os.path.basename(p)
        base_name = os.path.splitext(fname)[0]
        rel_path = os.path.relpath(p, folder_path).replace("\\", "/")
        parent_dir = os.path.basename(os.path.dirname(p))

        # Folder taxonomy archetype tracking
        if parent_dir and parent_dir.lower() not in ["png", "psd", "sprites", "images", "assets", "other assets", "tiled_files"]:
            inventory["character_archetypes"].add(parent_dir)

        # Keyword tag categorization
        lower_name = fname.lower()
        for cat, keywords in tag_dictionaries.items():
            for kw in keywords:
                if kw in lower_name:
                    inventory["detected_tags"][cat].add(kw)

        # Read image dimensions
        try:
            with Image.open(p) as im:
                w, h = im.size

                # Filmstrip Detection: w > h and w % h == 0 (e.g. 768x96 = 8 frames of 96x96)
                if h >= 12 and w > h and w % h == 0 and (w // h) <= 32:
                    frame_count = w // h
                    frame_size = h
                    inventory["filmstrip_animations"][rel_path] = {
                        "frame_count": frame_count,
                        "cell_size": f"{frame_size}x{frame_size}",
                        "total_dims": f"{w}x{h}"
                    }
                    inventory["detected_grid_factors"].add(frame_size)

                # Vertical Filmstrip Detection: h > w and h % w == 0
                elif w >= 12 and h > w and h % w == 0 and (h // w) <= 32:
                    frame_count = h // w
                    frame_size = w
                    inventory["filmstrip_animations"][rel_path] = {
                        "frame_count": frame_count,
                        "cell_size": f"{frame_size}x{frame_size}",
                        "total_dims": f"{w}x{h}",
                        "orientation": "vertical"
                    }
                    inventory["detected_grid_factors"].add(frame_size)

                # Large Spritesheets / Tilesets (>= 128 in either dim, or square tileset)
                elif w >= 128 or h >= 128:
                    common_grids = [8, 16, 24, 32, 48, 64, 80, 96, 128]
                    matching_grids = [g for g in common_grids if w % g == 0 and h % g == 0]
                    for g in matching_grids:
                        inventory["detected_grid_factors"].add(g)
                    inventory["environment_tilesets"].append({
                        "file": rel_path,
                        "dims": f"{w}x{h}",
                        "matching_tile_sizes": matching_grids
                    })

                # Single Sprites / Props
                else:
                    inventory["single_sprites"].append({
                        "file": rel_path,
                        "dims": f"{w}x{h}"
                    })

                # Check for numbered frames (discrete sequences)
                m = re.match(r'^(.*?)[_-]?(\d+)$', base_name)
                if m:
                    prefix = m.group(1).rstrip("_-")
                    discrete_tracker.setdefault(prefix, []).append(fname)

        except Exception:
            continue

    # Clean discrete sequences (keep sets with >= 2 frames)
    for prefix, frames in discrete_tracker.items():
        if len(frames) >= 2:
            inventory["discrete_animations"][prefix] = {
                "frame_count": len(frames),
                "samples": sorted(frames)[:4]
            }

    # Format sets into sorted lists for JSON serialization
    inventory["character_archetypes"] = sorted(list(inventory["character_archetypes"]))
    inventory["detected_grid_factors"] = sorted(list(inventory["detected_grid_factors"]))
    for cat in inventory["detected_tags"]:
        inventory["detected_tags"][cat] = sorted(list(inventory["detected_tags"][cat]))

    # Compute high-level asset availability flags
    inventory["asset_readiness"] = {
        "has_filmstrip_animations": len(inventory["filmstrip_animations"]) > 0,
        "has_discrete_animations": len(inventory["discrete_animations"]) > 0,
        "has_character_classes": len(inventory["character_archetypes"]) > 0,
        "has_locomotion": len(inventory["detected_tags"]["movement"]) > 0,
        "has_combat": len(inventory["detected_tags"]["combat"]) > 0,
        "has_environment_tiles": len(inventory["environment_tilesets"]) > 0 or len(inventory["detected_tags"]["environment"]) > 0,
        "has_ui": len(inventory["detected_tags"]["ui"]) > 0,
        "has_audio": inventory["total_audio"] > 0
    }

    return inventory

# Backward compatibility alias
def analyze_asset_folder(folder_path: str) -> Dict[str, Any]:
    return inspect_assets(folder_path)

if __name__ == "__main__":
    import sys
    import json
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    res = inspect_assets(path)
    print(json.dumps(res, indent=2))
