"""Validator tests on the committed fixture project; they need neither GameMaker nor any extension."""

import json
import os
import subprocess
import sys

from gm_common import read_json_permissive, write_json_atomic
from gm_lint import run_lint

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _types(result, bucket="errors"):
    return {e["type"] for e in result[bucket]}


def _edit(project, rel, fn):
    path = os.path.join(project, rel)
    data = read_json_permissive(path)
    fn(data)
    write_json_atomic(path, data)


def _layers(room, kind):
    return [l for l in room["layers"] if l["resourceType"] == kind]


def test_fixture_is_clean(fixture_project):
    result = run_lint(fixture_project)
    assert result["passed"] and result["warning_count"] == 0, result


def test_tile_layer_without_xy(fixture_project):
    def drop(room):
        for l in _layers(room, "GMRTileLayer"):
            del l["x"], l["y"]
    _edit(fixture_project, "rooms/Room1/Room1.yy", drop)
    assert "MISSING_LAYER_FIELD" in _types(run_lint(fixture_project))


def test_zero_size_tilemap(fixture_project):
    def zero(room):
        for l in _layers(room, "GMRTileLayer"):
            l["tiles"] = {"SerialiseWidth": 0, "SerialiseHeight": 0, "TileSerialiseData": []}
    _edit(fixture_project, "rooms/Room1/Room1.yy", zero)
    assert "EMPTY_TILEMAP" in _types(run_lint(fixture_project))


def test_instance_of_unregistered_object(fixture_project):
    def ghost(room):
        inst = _layers(room, "GMRInstanceLayer")[0]["instances"][0]
        inst["objectId"] = {"name": "obj_ghost", "path": "objects/obj_ghost/obj_ghost.yy"}
    _edit(fixture_project, "rooms/Room1/Room1.yy", ghost)
    assert "MISSING_REFERENCE" in _types(run_lint(fixture_project))


def test_missing_yyp_fields(fixture_project):
    _edit(fixture_project, "Minimal.yyp", lambda y: y.pop("resourceType"))
    assert "MISSING_PROJECT_FIELD" in _types(run_lint(fixture_project))


def test_missing_tileset_texture(fixture_project):
    os.remove(os.path.join(fixture_project, "tilesets", "ts_main", "output_tileset.png"))
    assert "MISSING_TILESET_TEXTURE" in _types(run_lint(fixture_project))


def test_event_files(fixture_project):
    folder = os.path.join(fixture_project, "objects", "obj_player")
    os.remove(os.path.join(folder, "Create_0.gml"))
    with open(os.path.join(folder, "Draw_0.gml"), "w") as f:
        f.write("draw_self();")
    result = run_lint(fixture_project)
    assert "MISSING_EVENT_FILE" in _types(result)
    assert "ORPHANED_EVENT_FILE" in _types(result, "warnings")


def test_collision_with_unregistered_object(fixture_project):
    def retarget(obj):
        for e in obj["eventList"]:
            if e["eventType"] == 4:
                e["collisionObjectId"] = {"name": "obj_gone", "path": "objects/obj_gone/obj_gone.yy"}
    _edit(fixture_project, "objects/obj_player/obj_player.yy", retarget)
    assert "MISSING_REFERENCE" in _types(run_lint(fixture_project))


def test_gml_rules_ignore_strings_and_comments(fixture_project):
    code = "\n".join([
        "health = 10;",
        "if (health == 10) {}",
        "x += hspeed;",
        "var a = argument0;",
        "spd = room_speed;",
        "// instance_create(0, 0, obj);",
        'show_debug_message("score = 1");',
    ])
    with open(os.path.join(fixture_project, "objects", "obj_player", "Create_0.gml"), "w") as f:
        f.write(code)
    result = run_lint(fixture_project)
    found = sorted((w["type"], w["file"].rsplit(":", 1)[1]) for w in result["warnings"])
    assert found == [("BUILTIN_GLOBAL_ASSIGNMENT", "1"), ("DEPRECATED_ROOM_SPEED", "5"),
                     ("DOUBLE_MOVEMENT", "3"), ("LEGACY_ARGUMENT", "4")]


def test_cli(fixture_project):
    lint = subprocess.run([sys.executable, os.path.join(KIT, "scripts", "gm_lint.py"), fixture_project],
                          capture_output=True, text=True)
    assert lint.returncode == 0 and json.loads(lint.stdout)["passed"]
    info = subprocess.run([sys.executable, os.path.join(KIT, "scripts", "gm_project.py"), fixture_project],
                          capture_output=True, text=True)
    assert json.loads(info.stdout)["room_order"] == ["Room1"]


def test_asset_inspector(tmp_path, sheet):
    from gm_asset_inspector import inspect_assets
    from PIL import Image
    Image.new("RGBA", (128, 32), (255, 0, 0, 255)).save(tmp_path / "hero_run.png")
    result = inspect_assets(str(tmp_path))
    assert result["filmstrip_animations"]["hero_run.png"]["frame_count"] == 4
    assert "run" in result["detected_tags"]["movement"]


def test_review_regressions(fixture_project):
    code = "\n".join([
        "/* room_speed */",                 # block comment: no warning
        '@"C:\\"; spd = room_speed;',       # verbatim string with a backslash: warning still found
        "var score = 0;",                   # local, not the built-in global
        "function f(lives = 3) {}",          # parameter, not the built-in global
    ])
    with open(os.path.join(fixture_project, "objects", "obj_player", "Create_0.gml"), "w") as f:
        f.write(code)

    def bad_refs(obj):
        obj["eventList"].append({"$GMEvent": "v1", "eventType": 4, "eventNum": 0, "collisionObjectId": "obj_wall"})
    _edit(fixture_project, "objects/obj_player/obj_player.yy", bad_refs)

    def bad_tiles(room):
        for l in _layers(room, "GMRTileLayer"):
            l["tiles"]["TileCompressedData"] = [-3]
    _edit(fixture_project, "rooms/Room1/Room1.yy", bad_tiles)

    result = run_lint(fixture_project)
    warnings = sorted((w["type"], w["file"].rsplit(":", 1)[1]) for w in result["warnings"])
    assert warnings == [("DEPRECATED_ROOM_SPEED", "2")], warnings
    assert {"MALFORMED_REFERENCE", "BAD_TILE_DATA"} <= _types(result)
