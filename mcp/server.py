"""
GameMaker Model Context Protocol (MCP) Server
JSON-RPC 2.0 over stdio (newline-delimited), tools capability.
Built-in tools inspect and validate projects. Extension packages found in the kit folder can register
more tools (see load_extensions).
"""

import os
import sys
import glob
import json
import importlib
import traceback
from typing import Any, Callable, Dict, List, Optional

KIT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPTS_DIR = os.path.join(KIT_DIR, "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from gm_common import GMError, __version__
from gm_project import GMProject
from gm_lint import run_lint
from gm_asset_inspector import inspect_assets

SERVER_NAME = "gamemaker-mcp"
SUPPORTED_PROTOCOL_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05"]

Handler = Callable[[Dict[str, Any]], Any]


def _reject_constant(name: str) -> Any:
    """NaN/Infinity are not JSON; accepting them would write invalid project files."""
    raise ValueError(f"{name} is not valid JSON")


class ToolRegistry:
    """Ordered collection of MCP tools: name -> (definition, handler)."""

    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}
        self.extensions: List[str] = []

    def add(self, name: str, description: str, properties: Dict[str, Any], required: List[str], handler: Handler) -> None:
        if name in self._tools:
            raise ValueError(f"Duplicate tool: {name}")
        self._tools[name] = {
            "definition": {
                "name": name,
                "description": description,
                "inputSchema": {"type": "object", "properties": properties, "required": required},
            },
            "handler": handler,
        }

    def definitions(self) -> List[Dict[str, Any]]:
        return [t["definition"] for t in self._tools.values()]

    def call(self, name: str, args: Dict[str, Any]) -> Any:
        tool = self._tools[name]
        missing = [r for r in tool["definition"]["inputSchema"]["required"] if r not in args]
        if missing:
            raise GMError(f"Missing required argument(s): {', '.join(missing)}")
        return tool["handler"](args)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


PROJECT_PATH = {"type": "string", "description": "Absolute path to the GameMaker project directory or .yyp file"}


def register_builtin_tools(registry: ToolRegistry) -> None:
    def read_project(args):
        proj = GMProject(args["project_path"])
        return {
            "name": proj.yyp_data.get("name"),
            "ide_version": proj.yyp_data.get("MetaData", {}).get("IDEVersion"),
            "categories": proj.get_resources_by_type(),
            "total_resources": len(proj.get_resources()),
            "room_order": [n.get("roomId", {}).get("name") for n in proj.yyp_data.get("RoomOrderNodes", [])],
        }

    registry.add(
        "gm_read_project",
        "Inspects a GameMaker project (.yyp) and returns its asset catalog by type, room order and IDE version.",
        {"project_path": PROJECT_PATH}, ["project_path"], read_project)

    registry.add(
        "gm_validate_project",
        "Validates a project: missing/orphaned files, broken references between assets, fields the compiler requires, "
        "event files, deprecated APIs and common GML pitfalls. Does not check GML syntax (compile for that).",
        {"project_path": PROJECT_PATH}, ["project_path"], lambda a: run_lint(a["project_path"]))

    registry.add(
        "gm_inspect_assets",
        "Extracts factual metadata from an art folder: image sizes, filmstrip frame counts, tile grid factors and "
        "name-based tags (movement, combat, environment, ui, items).",
        {"folder_path": {"type": "string", "description": "Path to a directory containing art assets"}},
        ["folder_path"], lambda a: inspect_assets(a["folder_path"]))

    def read_script(args):
        proj = GMProject(args["project_path"])
        return {"script_name": args["script_name"], "content": proj.read_script(args["script_name"])}

    registry.add(
        "gm_read_script",
        "Returns the GML source of a script asset.",
        {"project_path": PROJECT_PATH, "script_name": {"type": "string", "description": "Script asset name, e.g. scr_math"}},
        ["project_path", "script_name"], read_script)


def load_extensions(registry: ToolRegistry) -> None:
    """
    An extension is a package one level below a top-level kit folder (<kit>/<folder>/<package>/__init__.py)
    that defines register_tools(registry). Set GM_KIT_NO_EXTENSIONS=1 to run with the built-in tools only.
    """
    if os.environ.get("GM_KIT_NO_EXTENSIONS") == "1":
        return
    for init in sorted(glob.glob(os.path.join(KIT_DIR, "*", "*", "__init__.py"))):
        package_dir = os.path.dirname(init)
        with open(init, encoding="utf-8", errors="ignore") as f:
            if "def register_tools(" not in f.read():
                continue
        parent = os.path.dirname(package_dir)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        module = importlib.import_module(os.path.basename(package_dir))
        module.register_tools(registry)
        registry.extensions.append(module.__name__)


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    register_builtin_tools(registry)
    load_extensions(registry)
    return registry


class Server:
    def __init__(self, registry: ToolRegistry, log_path: Optional[str] = None) -> None:
        self.registry = registry
        self.log_path = log_path

    def log(self, msg: str) -> None:
        if not self.log_path:
            return
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except OSError:
            pass

    def handle(self, req: Any) -> Optional[Dict[str, Any]]:
        """Handles one JSON-RPC message and returns the response (None for notifications). Never raises."""
        req_id = req.get("id") if isinstance(req, dict) else None
        try:
            return self._dispatch(req)
        except Exception as e:  # A malformed message must never take the server down
            self.log(traceback.format_exc())
            return self._error(req_id, -32603, f"Internal error: {e!r}")

    def _dispatch(self, req: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or not isinstance(req.get("method"), str):
            return self._error(req.get("id") if isinstance(req, dict) else None, -32600, "Invalid Request")
        req_id = req.get("id")
        method = req["method"]
        params = req.get("params")
        if "id" not in req:
            self.log(f"notification {method}")
            return None  # Notifications never get a response
        if params is None:
            params = {}
        if not isinstance(params, dict):
            return self._error(req_id, -32602, "params must be an object")

        if method == "initialize":
            requested = params.get("protocolVersion")
            version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
            return self._result(req_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": __version__},
            })
        if method == "ping":
            return self._result(req_id, {})
        if method == "tools/list":
            return self._result(req_id, {"tools": self.registry.definitions()})
        if method == "tools/call":
            name = params.get("name")
            args = params.get("arguments")
            if args is None:
                args = {}
            if not isinstance(name, str) or name not in self.registry:
                return self._error(req_id, -32602, f"Unknown tool: {name}")
            if not isinstance(args, dict):
                return self._error(req_id, -32602, "Tool arguments must be an object")
            self.log(f"call {name}")
            try:
                data = self.registry.call(name, args)
                return self._result(req_id, {"content": [{"type": "text", "text": json.dumps(data, indent=2)}], "isError": False})
            except (GMError, FileNotFoundError, ValueError, KeyError, TypeError, OSError) as e:
                self.log(f"tool error {name}: {e!r}")
                return self._result(req_id, {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True})
            except Exception as e:  # Unexpected bug: report it to the client instead of killing the server
                self.log(traceback.format_exc())
                return self._result(req_id, {"content": [{"type": "text", "text": f"Internal error in {name}: {e!r}"}], "isError": True})
        return self._error(req_id, -32601, f"Method not found: {method}")

    @staticmethod
    def _result(req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    def serve(self, stdin=None, stdout=None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line, parse_constant=_reject_constant)
            except (ValueError, RecursionError):  # JSONDecodeError is a ValueError
                resp = self._error(None, -32700, "Parse error")
            else:
                resp = self.handle(req)
            if resp is not None:
                stdout.write(json.dumps(resp) + "\n")
                stdout.flush()


def main() -> None:
    # MCP messages are UTF-8; Windows consoles default to a legacy code page
    for stream in (sys.stdin, sys.stdout):
        if hasattr(stream, "reconfigure"):
            # errors="replace": an invalid byte becomes a parse error instead of ending the server
            stream.reconfigure(encoding="utf-8", errors="replace")
    if "--version" in sys.argv:
        print(f"{SERVER_NAME} {__version__}")
        return
    Server(build_registry(), log_path=os.environ.get("GM_MCP_LOG")).serve()


if __name__ == "__main__":
    main()
