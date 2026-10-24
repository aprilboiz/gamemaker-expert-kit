"""
gm_lint.py - Static project validator and GML linter for GameMaker LTS.
Checks .yyp/.yy integrity, cross-resource references, fields the asset compiler requires,
object event files, deprecated APIs and common GML pitfalls.
It does not parse GML syntax: compile in GameMaker or with Igor (references/cli-igor.md) for that.
"""

import os
import re
import json
from typing import Any, Dict, List, Optional, Set

from gm_common import EVENT_FILE_PREFIX, decode_tiles, find_yyp, read_json_permissive, strip_code

# Fields the GameMaker asset compiler needs to load a room.
# GMRTileLayer x/y: a missing field fails with 'Field "x": expected' (reproduced with Igor, LTS 2026).
REQUIRED_LAYER_FIELDS = {
    "GMRTileLayer": ["x", "y", "tilesetId", "tiles"],
    "GMRInstanceLayer": ["instances"],
}
REQUIRED_INSTANCE_FIELDS = ["objectId", "x", "y", "inheritCode"]

# (rule id, severity, regex, message) applied to each GML line with comments stripped
GML_LINE_RULES = [
    ("DEPRECATED_ROOM_SPEED", "warning", re.compile(r"\broom_speed\b"),
     "'room_speed' is deprecated. Use 'game_get_speed(gamespeed_fps)'."),
    ("DEPRECATED_INSTANCE_CREATE", "error", re.compile(r"\binstance_create\s*\("),
     "'instance_create' was removed. Use 'instance_create_layer' or 'instance_create_depth'."),
    ("LEGACY_ARGUMENT", "warning", re.compile(r"\bargument(\d+|\s*\[)"),
     "Legacy 'argumentN'/'argument[i]'. Declare named parameters: function f(a, b = 0) { ... }."),
    ("BUILTIN_GLOBAL_ASSIGNMENT", "warning", re.compile(r"(?<![.\w])(health|score|lives)\s*(=(?!=)|\+=|-=)"),
     "'health', 'score' and 'lives' are built-in GLOBAL variables shared by every instance. Use your own instance variable (e.g. hp)."),
    ("DOUBLE_MOVEMENT", "warning", re.compile(r"\b[xy]\s*\+=\s*[hv]speed\b"),
     "'hspeed'/'vspeed' are built-in: GameMaker already moves the instance by them each step, so this moves it twice. Use your own hsp/vsp variables."),
]


class GMLinter:
    def __init__(self, project_path: str):
        self.project_path = os.path.abspath(project_path)
        self.yyp_path, self.project_dir = find_yyp(self.project_path)
        self.errors: List[Dict[str, str]] = []
        self.warnings: List[Dict[str, str]] = []
        self.info: List[Dict[str, str]] = []
        self.registered: Dict[str, Set[str]] = {}

    def _read_json(self, path: str) -> Any:
        return read_json_permissive(path)

    def _add(self, severity: str, rule: str, file: str, message: str) -> None:
        bucket = {"error": self.errors, "warning": self.warnings, "info": self.info}[severity]
        bucket.append({"type": rule, "file": file, "message": message})

    def _rel(self, path: str) -> str:
        return os.path.relpath(path, self.project_dir).replace(os.sep, "/")

    def lint_all(self) -> Dict[str, Any]:
        """Runs all linter suites."""
        self.errors, self.warnings, self.info = [], [], []
        self.registered = {}

        yyp_data = self.check_yyp_integrity()
        if yyp_data is not None:
            self.check_room_order(yyp_data)
            self.check_objects()
            self.check_rooms()
            self.check_tilesets()
        self.check_gml_code()

        return {
            "passed": len(self.errors) == 0,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info
        }

    # ---- helpers -------------------------------------------------------

    def _check_ref(self, ref: Any, kind: str, file: str, what: str) -> None:
        """Validates a {"name", "path"} reference to a registered resource of `kind`."""
        if ref is None:
            return
        if not isinstance(ref, dict) or "name" not in ref:
            self._add("error", "MALFORMED_REFERENCE", file, f"{what} is not a {{name, path}} reference: {ref!r}")
            return
        name = ref.get("name")
        expected_path = f"{kind}/{name}/{name}.yy"
        if name not in self.registered.get(kind, set()):
            self._add("error", "MISSING_REFERENCE", file, f"{what} points to {kind[:-1]} '{name}', which is not registered in .yyp")
        elif ref.get("path") != expected_path:
            self._add("error", "BAD_REFERENCE_PATH", file, f"{what} path '{ref.get('path')}' should be '{expected_path}'")

    def _asset_files(self, kind: str):
        """Yields (name, yy_path) for every registered resource of `kind` that exists on disk."""
        for name in sorted(self.registered.get(kind, set())):
            yy = os.path.join(self.project_dir, kind, name, f"{name}.yy")
            if os.path.exists(yy):
                yield name, yy

    def _load(self, path: str, rule: str) -> Optional[Dict[str, Any]]:
        try:
            return self._read_json(path)
        except Exception as e:
            self._add("error", rule, self._rel(path), f"Failed to parse JSON: {e}")
            return None

    # ---- suites --------------------------------------------------------

    def check_yyp_integrity(self) -> Optional[Dict[str, Any]]:
        """Verifies that all files registered in .yyp exist on disk, and finds unregistered assets."""
        try:
            yyp_data = self._read_json(self.yyp_path)
        except Exception as e:
            self._add("error", "YYP_PARSE_ERROR", os.path.basename(self.yyp_path), f"Failed to parse .yyp: {e}")
            return None

        for field, expected in (("resourceType", "GMProject"), ("resourceVersion", None)):
            if field not in yyp_data:
                self._add("error", "MISSING_PROJECT_FIELD", os.path.basename(self.yyp_path),
                          f"The .yyp is missing '{field}' (GameMaker refuses to load the project)")
            elif expected and yyp_data[field] != expected:
                self._add("error", "BAD_PROJECT_FIELD", os.path.basename(self.yyp_path),
                          f"'{field}' is '{yyp_data[field]}', expected '{expected}'")

        registered_paths = set()
        seen_names = set()
        for r in yyp_data.get("resources", []):
            rel_path = r.get("id", {}).get("path", "")
            res_name = r.get("id", {}).get("name", "")
            if not rel_path:
                continue
            if res_name in seen_names:
                self._add("error", "DUPLICATE_RESOURCE", rel_path, f"Resource name '{res_name}' is registered more than once")
            seen_names.add(res_name)
            registered_paths.add(rel_path)
            kind = rel_path.split("/", 1)[0]
            self.registered.setdefault(kind, set()).add(res_name)
            if not os.path.exists(os.path.join(self.project_dir, rel_path.replace("/", os.sep))):
                self._add("error", "MISSING_RESOURCE_FILE", rel_path,
                          f"Resource '{res_name}' is declared in .yyp but file is missing on disk: {rel_path}")

        for asset_dir in ["objects", "sprites", "tilesets", "rooms", "scripts", "sounds"]:
            folder = os.path.join(self.project_dir, asset_dir)
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                rel_yy = f"{asset_dir}/{name}/{name}.yy"
                if os.path.exists(os.path.join(folder, name, f"{name}.yy")) and rel_yy not in registered_paths:
                    self._add("warning", "ORPHANED_ASSET", rel_yy, f"Asset '{name}' exists on disk but is not registered in .yyp")
        return yyp_data

    def check_room_order(self, yyp_data: Dict[str, Any]) -> None:
        """Every room should appear exactly once in RoomOrderNodes; the first one is the start room."""
        ordered = []
        for node in yyp_data.get("RoomOrderNodes", []):
            ref = node.get("roomId")
            self._check_ref(ref, "rooms", os.path.basename(self.yyp_path), "RoomOrderNodes entry")
            if isinstance(ref, dict):
                ordered.append(ref.get("name"))
        rooms = self.registered.get("rooms", set())
        if rooms and not ordered:
            self._add("error", "EMPTY_ROOM_ORDER", os.path.basename(self.yyp_path), "RoomOrderNodes is empty: the game has no start room")
        for name in sorted(rooms - set(ordered)):
            self._add("warning", "ROOM_NOT_IN_ORDER", f"rooms/{name}/{name}.yy",
                      f"Room '{name}' is missing from RoomOrderNodes (unreachable via room_goto_next)")

    def check_objects(self) -> None:
        """Validates object sprite/parent/collision references and event files."""
        for name, yy in self._asset_files("objects"):
            data = self._load(yy, "OBJECT_PARSE_ERROR")
            if data is None:
                continue
            rel = self._rel(yy)
            self._check_ref(data.get("spriteId"), "sprites", rel, "spriteId")
            self._check_ref(data.get("spriteMaskId"), "sprites", rel, "spriteMaskId")
            self._check_ref(data.get("parentObjectId"), "objects", rel, "parentObjectId")

            expected_files = set()
            for ev in data.get("eventList", []):
                etype, enum = ev.get("eventType"), ev.get("eventNum")
                prefix = EVENT_FILE_PREFIX.get(etype)
                if prefix is None:
                    self._add("warning", "UNKNOWN_EVENT_TYPE", rel, f"Unknown eventType {etype}")
                    continue
                if etype == 4:
                    coll = ev.get("collisionObjectId")
                    if coll is None:
                        self._add("error", "MISSING_COLLISION_OBJECT", rel, "Collision event without collisionObjectId")
                        continue
                    self._check_ref(coll, "objects", rel, "collisionObjectId")
                    if not isinstance(coll, dict):
                        continue  # reported as MALFORMED_REFERENCE
                    fname = f"Collision_{coll.get('name')}.gml"
                else:
                    fname = f"{prefix}_{enum}.gml"
                expected_files.add(fname)
                if not os.path.exists(os.path.join(os.path.dirname(yy), fname)):
                    self._add("error", "MISSING_EVENT_FILE", rel, f"Event ({etype}, {enum}) has no code file {fname}")

            for f in os.listdir(os.path.dirname(yy)):
                if f.endswith(".gml") and f not in expected_files:
                    self._add("warning", "ORPHANED_EVENT_FILE", f"objects/{name}/{f}",
                              f"'{f}' is not referenced by any event of '{name}' and will never run")

    def check_rooms(self) -> None:
        """Validates room layers, instances (GMRInstance v4, inheritCode) and their references."""
        for rname, ryy in self._asset_files("rooms"):
            rdata = self._load(ryy, "ROOM_PARSE_ERROR")
            if rdata is None:
                continue
            rel = self._rel(ryy)
            instance_names = set()
            self._check_layers(rdata.get("layers", []), rname, rel, instance_names)

            for entry in rdata.get("instanceCreationOrder", []):
                if entry.get("name") not in instance_names:
                    self._add("error", "BAD_CREATION_ORDER", rel,
                              f"instanceCreationOrder lists '{entry.get('name')}', which is not an instance in this room")

    def _check_layers(self, layers: List[Dict[str, Any]], rname: str, rel: str, instance_names: Set[str]) -> None:
        names = set()
        for layer in layers:
            ltype = layer.get("resourceType")
            lname = layer.get("name", "unnamed")
            if lname in names:
                self._add("error", "DUPLICATE_LAYER", rel, f"Room '{rname}' has more than one layer named '{lname}'")
            names.add(lname)

            for field in REQUIRED_LAYER_FIELDS.get(ltype, []):
                if field not in layer:
                    self._add("error", "MISSING_LAYER_FIELD", rel,
                              f"{ltype} '{lname}' is missing required field '{field}' (the IDE/compiler will refuse to load the room)")

            if ltype == "GMRTileLayer":
                block = layer.get("tiles") or {}
                cols, rows = block.get("SerialiseWidth", 0), block.get("SerialiseHeight", 0)
                if not isinstance(cols, int) or not isinstance(rows, int) or cols <= 0 or rows <= 0:
                    self._add("error", "EMPTY_TILEMAP", rel,
                              f"Tile layer '{lname}' is {cols}x{rows}: tilemap_get/tilemap_set fail at runtime with 'tilemap element corrupted'")
                else:
                    try:
                        size_ok = len(decode_tiles(block)) == cols * rows
                        problem = f"does not match its {cols}x{rows} size"
                    except ValueError as e:
                        size_ok, problem = False, f"is malformed: {e}"
                    if not size_ok:
                        self._add("error", "BAD_TILE_DATA", rel, f"Tile layer '{lname}' data {problem}")
                if layer.get("tilesetId") is None:
                    self._add("warning", "TILE_LAYER_WITHOUT_TILESET", rel, f"Tile layer '{lname}' has no tileset")
                self._check_ref(layer.get("tilesetId"), "tilesets", rel, f"Tile layer '{lname}' tilesetId")
            elif ltype == "GMRBackgroundLayer":
                self._check_ref(layer.get("spriteId"), "sprites", rel, f"Background layer '{lname}' spriteId")
            elif ltype == "GMRInstanceLayer":
                for inst in layer.get("instances", []):
                    iname = inst.get("name", "unnamed")
                    instance_names.add(iname)
                    if inst.get("$GMRInstance") != "v4":
                        self._add("warning", "OBSOLETE_INSTANCE_SCHEMA", rel,
                                  f"Instance '{iname}' has schema '{inst.get('$GMRInstance')}' instead of 'v4'")
                    for field in REQUIRED_INSTANCE_FIELDS:
                        if field not in inst:
                            self._add("error", "MISSING_INSTANCE_FIELD", rel,
                                      f"Instance '{iname}' in room '{rname}' is missing mandatory '{field}' field")
                    self._check_ref(inst.get("objectId"), "objects", rel, f"Instance '{iname}' objectId")

            self._check_layers(layer.get("layers", []), rname, rel, instance_names)

    def check_tilesets(self) -> None:
        for name, yy in self._asset_files("tilesets"):
            data = self._load(yy, "TILESET_PARSE_ERROR")
            if data is None:
                continue
            if data.get("spriteId") is None:
                self._add("error", "TILESET_WITHOUT_SPRITE", self._rel(yy), f"Tileset '{name}' has no sprite")
            if not os.path.exists(os.path.join(os.path.dirname(yy), "output_tileset.png")):
                self._add("error", "MISSING_TILESET_TEXTURE", self._rel(yy),
                          f"Tileset '{name}' has no output_tileset.png: its tiles collide but are never drawn. "
                          "Open the tileset in the IDE and save it to regenerate the image.")
            self._check_ref(data.get("spriteId"), "sprites", self._rel(yy), "spriteId")

    def check_gml_code(self) -> None:
        """Scans all GML files for deprecations, audio buffer violations, and anti-patterns."""
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if not f.endswith(".gml"):
                    continue

                full_gml = os.path.join(root, f)
                rel_gml = self._rel(full_gml)
                with open(full_gml, "r", encoding="utf-8", errors="ignore") as g:
                    content = g.read()
                code = strip_code(content)
                uses_buffer_grow = "buffer_grow" in code
                # health/score/lives declared as locals or parameters are not the built-in globals
                local_names = set(re.findall(r"\bvar\s+(health|score|lives)\b", code))
                local_names |= set(re.findall(r"\bfunction\b[^{]*?[(,]\s*(health|score|lives)\b", code))

                for line_idx, line in enumerate(code.splitlines(), 1):
                    loc = f"{rel_gml}:{line_idx}"
                    for rule, severity, pattern, message in GML_LINE_RULES:
                        m = pattern.search(line)
                        if m and not (rule == "BUILTIN_GLOBAL_ASSIGNMENT" and m.group(1) in local_names):
                            self._add(severity, rule, loc, message)

                    if "audio_create_buffer_sound" in line and uses_buffer_grow:
                        self._add("warning", "AUDIO_BUFFER_GROW_RISK", loc,
                                  "audio_create_buffer_sound needs a 'buffer_fixed' buffer; this file also uses 'buffer_grow'.")

                    if f in ("Draw_64.gml", "Draw_74.gml", "Draw_75.gml") and re.search(r"\bmouse_[xy]\b", line):
                        self._add("warning", "GUI_MOUSE_COORDINATE_MISMATCH", loc,
                                  "'mouse_x'/'mouse_y' are room coordinates. In Draw GUI use 'device_mouse_x_to_gui(0)'.")


def run_lint(project_path: str) -> Dict[str, Any]:
    linter = GMLinter(project_path)
    return linter.lint_all()


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    res = run_lint(path)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["passed"] else 1)
