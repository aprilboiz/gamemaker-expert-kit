import json
import os

import pytest

from gm_common import (
    GMError,
    find_yyp,
    read_json_permissive,
    safe_join,
    strip_trailing_commas,
    validate_asset_name,
    validate_event_filename,
    write_json_atomic,
)


def test_strip_trailing_commas_keeps_string_contents():
    raw = '{"a": [1, 2,], "s": "x, }", "t": "y,]",}'
    assert json.loads(strip_trailing_commas(raw)) == {"a": [1, 2], "s": "x, }", "t": "y,]"}


def test_strip_trailing_commas_handles_escaped_quotes():
    raw = '{"s": "say \\"hi\\", }",}'
    assert json.loads(strip_trailing_commas(raw)) == {"s": 'say "hi", }'}


def test_read_json_permissive_accepts_bom_and_trailing_commas(tmp_path):
    p = tmp_path / "a.yy"
    p.write_bytes(b'\xef\xbb\xbf{"x": 1,}')
    assert read_json_permissive(str(p)) == {"x": 1}


def test_write_json_atomic_leaves_no_temp_files(tmp_path):
    p = tmp_path / "sub" / "a.json"
    write_json_atomic(str(p), {"x": 1})
    assert json.loads(p.read_text()) == {"x": 1}
    assert os.listdir(p.parent) == ["a.json"]


@pytest.mark.parametrize("name", ["obj_player", "_x", "Room1", "spr_A9"])
def test_valid_asset_names(name):
    assert validate_asset_name(name) == name


@pytest.mark.parametrize("name", ["../x", "a/b", "a\\b", "1abc", "", "a b", "obj-1", None, 5])
def test_invalid_asset_names(name):
    with pytest.raises(GMError):
        validate_asset_name(name)


@pytest.mark.parametrize("name", ["../Create_0.gml", "Create_0.txt", "Create.gml", "a/Create_0.gml"])
def test_invalid_event_filenames(name):
    with pytest.raises(GMError):
        validate_event_filename(name)


def test_safe_join_blocks_escape(tmp_path):
    assert safe_join(str(tmp_path), "scripts", "a").startswith(str(tmp_path.resolve()))
    with pytest.raises(GMError):
        safe_join(str(tmp_path), "scripts", "..", "..", "x")


def test_find_yyp_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_yyp(str(tmp_path))
    (tmp_path / "a.yyp").write_text("{}")
    (tmp_path / "b.yyp").write_text("{}")
    with pytest.raises(GMError):
        find_yyp(str(tmp_path))
    assert find_yyp(str(tmp_path / "a.yyp"))[0].endswith("a.yyp")
