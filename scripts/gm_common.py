"""
gm_common.py - Shared helpers for GameMaker project tooling.
Permissive JSON reading, atomic writes, project discovery, and name/path validation.
"""

import os
import re
import json
import tempfile
from typing import Any, Dict, List, Tuple

__version__ = "1.0.0"

ASSET_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
EVENT_FILE_RE = re.compile(r"^[A-Za-z]+_[A-Za-z0-9_]+\.gml$")

# eventType -> file name prefix used by the GameMaker IDE
EVENT_FILE_PREFIX = {
    0: "Create", 1: "Destroy", 2: "Alarm", 3: "Step", 4: "Collision", 5: "Keyboard",
    6: "Mouse", 7: "Other", 8: "Draw", 9: "KeyPress", 10: "KeyRelease", 12: "CleanUp", 13: "Gesture",
}


class GMError(ValueError):
    """Raised for invalid input or an inconsistent project state."""


def strip_trailing_commas(raw: str) -> str:
    """Removes trailing commas before ']' or '}' without touching string contents."""
    out = []
    in_string = False
    escaped = False
    pending_comma = -1  # index in `out` of a comma that may be trailing
    for ch in raw:
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            pending_comma = -1
            in_string = True
            out.append(ch)
        elif ch == ",":
            pending_comma = len(out)
            out.append(ch)
        elif ch in "]}":
            if pending_comma >= 0:
                out[pending_comma] = ""
            pending_comma = -1
            out.append(ch)
        else:
            if not ch.isspace():
                pending_comma = -1
            out.append(ch)
    return "".join(out)


def read_json_permissive(path: str) -> Any:
    """Reads GameMaker JSON (which may contain trailing commas)."""
    with open(path, "r", encoding="utf-8-sig") as f:
        raw = f.read()
    return json.loads(strip_trailing_commas(raw))


def write_text_atomic(path: str, text: str) -> None:
    """Writes text via a temp file + rename so a crash never leaves a half-written file."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp_", suffix=os.path.basename(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def write_json_atomic(path: str, data: Any) -> None:
    """Writes JSON with 2-space indentation atomically."""
    # allow_nan=False: NaN/Infinity are not JSON and would make the file unreadable
    write_text_atomic(path, json.dumps(data, indent=2, allow_nan=False) + "\n")


def find_yyp(project_path: str) -> Tuple[str, str]:
    """Resolves a project directory or .yyp path to (yyp_path, project_dir)."""
    project_path = os.path.abspath(project_path)
    if os.path.isdir(project_path):
        yyps = sorted(f for f in os.listdir(project_path) if f.endswith(".yyp"))
        if not yyps:
            raise FileNotFoundError(f"No .yyp found in {project_path}")
        if len(yyps) > 1:
            raise GMError(f"Multiple .yyp files in {project_path}: {yyps}. Pass the .yyp path explicitly.")
        return os.path.join(project_path, yyps[0]), project_path
    if not project_path.endswith(".yyp"):
        raise GMError(f"Not a GameMaker project directory or .yyp file: {project_path}")
    if not os.path.exists(project_path):
        raise FileNotFoundError(f"Project file not found: {project_path}")
    return project_path, os.path.dirname(project_path)


def validate_asset_name(name: Any, kind: str = "asset") -> str:
    """Ensures a resource name is a valid GML identifier (also blocks path traversal)."""
    if not isinstance(name, str) or not ASSET_NAME_RE.match(name):
        raise GMError(
            f"Invalid {kind} name {name!r}: use letters, digits and underscores, not starting with a digit."
        )
    return name


def validate_event_filename(filename: Any) -> str:
    """Ensures an object event file name is a plain '<Kind>_<n>.gml' file name."""
    if not isinstance(filename, str) or not EVENT_FILE_RE.match(filename):
        raise GMError(f"Invalid event file name {filename!r}: expected e.g. 'Create_0.gml'.")
    return filename


def safe_join(base: str, *parts: str) -> str:
    """Joins paths and guarantees the result stays inside `base`."""
    base_real = os.path.realpath(base)
    target = os.path.realpath(os.path.join(base_real, *parts))
    if os.path.commonpath([base_real, target]) != base_real:
        raise GMError(f"Path escapes the project directory: {os.path.join(*parts)}")
    return target


def encode_tiles(data: List[int]) -> List[int]:
    """
    Run-length encodes tile data the way the IDE stores it (TileDataFormat 1 / TileCompressedData):
    a negative count -n repeats the next value n times, a positive count n is followed by n literal values.
    """
    out: List[int] = []
    i, n = 0, len(data)
    while i < n:
        j = i
        while j < n and data[j] == data[i]:
            j += 1
        if j - i >= 2:
            out += [-(j - i), data[i]]
            i = j
            continue
        literals = []
        while i < n and not (i + 1 < n and data[i] == data[i + 1]):
            literals.append(data[i])
            i += 1
        out += [len(literals)] + literals
    return out


# Upper bound on tilemap cells (a 4096x4096-tile room) so bad input can't exhaust memory
MAX_TILE_CELLS = 4096 * 4096


def decode_tiles(tiles: Dict[str, Any], limit: int = MAX_TILE_CELLS) -> List[int]:
    """
    Returns the flat row-major tile data of a GMRTileLayer 'tiles' block (compressed or raw).
    Raises ValueError for malformed data.
    """
    def _int(v: Any) -> int:
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError(f"tile data must be integers, got {v!r}")
        return v

    if "TileCompressedData" in tiles:
        packed, out, i = tiles["TileCompressedData"], [], 0
        if not isinstance(packed, list):
            raise ValueError("TileCompressedData must be a list")
        while i < len(packed):
            count = _int(packed[i])
            if count < 0:
                if i + 1 >= len(packed):
                    raise ValueError("TileCompressedData ends inside a run")
                if len(out) - count > limit:
                    raise ValueError(f"tile data exceeds {limit} cells")
                out += [_int(packed[i + 1])] * -count
                i += 2
            else:
                if i + 1 + count > len(packed):
                    raise ValueError("TileCompressedData ends inside a literal block")
                out += [_int(v) for v in packed[i + 1:i + 1 + count]]
                i += 1 + count
            if len(out) > limit:
                raise ValueError(f"tile data exceeds {limit} cells")
        return out
    raw = tiles.get("TileSerialiseData", [])
    if not isinstance(raw, list) or len(raw) > limit:
        raise ValueError("TileSerialiseData must be a list of at most %d cells" % limit)
    return [_int(v) for v in raw]




def strip_code(text: str) -> str:
    """
    Blanks comments and string literal contents (keeping line breaks and column positions) so rules only see code.
    Handles // and /* */ comments, "..." and '...' with escapes, @"..." verbatim strings, and keeps the
    {expressions} inside $"..." template strings as code.
    """
    out = []
    i, n = 0, len(text)

    def blank(chunk: str) -> str:
        return re.sub(r"[^\n]", " ", chunk)

    while i < n:
        ch = text[i]
        two = text[i:i + 2]
        if two == "//":
            end = text.find("\n", i)
            end = n if end < 0 else end
            out.append(blank(text[i:end]))
            i = end
        elif two == "/*":
            end = text.find("*/", i + 2)
            end = n if end < 0 else end + 2
            out.append(blank(text[i:end]))
            i = end
        elif two == '$"':
            # Template string: blank the literal text, keep the {expressions}
            out.append('$"')
            i += 2
            depth = 0
            while i < n:
                c = text[i]
                if depth == 0 and c == '"':
                    break
                if depth == 0 and c == "\\" and i + 1 < n:
                    out.append(blank(text[i:i + 2]))
                    i += 2
                    continue
                if c == "{":
                    depth += 1
                    out.append(" ")
                elif c == "}" and depth > 0:
                    depth -= 1
                    out.append(" ")
                else:
                    out.append(c if depth > 0 or c == "\n" else " ")
                i += 1
            if i < n:
                out.append('"')
                i += 1
        elif ch in "\"'" or two == '@"':
            verbatim = ch == "@"
            prefix = 2 if verbatim else 1
            start = i
            i += prefix
            quote = text[i - 1]
            while i < n and text[i] != quote:
                if text[i] == "\\" and not verbatim:
                    i += 1
                i += 1
            i = min(i + 1, n)
            literal = text[start:i]
            closed = len(literal) > prefix and literal.endswith(quote)
            body = literal[prefix:-1] if closed else literal[prefix:]
            out.append(literal[:prefix] + blank(body) + (quote if closed else ""))
        else:
            out.append(ch)
            i += 1
    return "".join(out)
