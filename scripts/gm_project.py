"""
gm_project.py - Read-only access to GameMaker LTS Format 2.0 projects (.yyp and asset .yy files).
It never writes; gm_lint.py validates what it reads.
"""

import os
from typing import Any, Dict, List, Optional

from gm_common import GMError, find_yyp, read_json_permissive, safe_join, validate_asset_name


class GMProject:
    def __init__(self, project_path: str):
        self.project_path = os.path.abspath(project_path)
        self.yyp_path, self.project_dir = find_yyp(self.project_path)
        self.yyp_data = self._read_json_permissive(self.yyp_path)

    @staticmethod
    def _read_json_permissive(filepath: str) -> Dict[str, Any]:
        """Reads GameMaker JSON files safely by sanitizing trailing commas."""
        return read_json_permissive(filepath)

    def _asset_dir(self, kind: str, name: str) -> str:
        """Returns '<project>/<kind>/<name>' after validating the name."""
        validate_asset_name(name, kind.rstrip("s"))
        return safe_join(self.project_dir, kind, name)

    def _asset_ref(self, kind: str, name: str) -> Dict[str, str]:
        return {"name": name, "path": f"{kind}/{name}/{name}.yy"}

    def has_resource(self, res_name: str, kind: Optional[str] = None) -> bool:
        """Whether a resource with this name (optionally under `kind/`) is registered in .yyp."""
        for r in self.get_resources():
            rid = r.get("id", {})
            if rid.get("name") == res_name and (kind is None or rid.get("path", "").startswith(f"{kind}/")):
                return True
        return False

    def _require_resource(self, kind: str, name: str) -> None:
        if not self.has_resource(name, kind):
            raise GMError(f"{kind.rstrip('s').capitalize()} '{name}' is not registered in the project")

    def get_resources(self) -> List[Dict[str, Any]]:
        """Returns all resources registered in .yyp."""
        return self.yyp_data.get("resources", [])

    def get_resources_by_type(self) -> Dict[str, List[str]]:
        """Categorizes resources into sprites, objects, rooms, scripts, sounds, etc."""
        categories = {
            "sprites": [],
            "tilesets": [],
            "objects": [],
            "rooms": [],
            "scripts": [],
            "sounds": [],
            "others": []
        }
        for res in self.get_resources():
            path = res.get("id", {}).get("path", "")
            name = res.get("id", {}).get("name", "")
            if path.startswith("sprites/"):
                categories["sprites"].append(name)
            elif path.startswith("tilesets/"):
                categories["tilesets"].append(name)
            elif path.startswith("objects/"):
                categories["objects"].append(name)
            elif path.startswith("rooms/"):
                categories["rooms"].append(name)
            elif path.startswith("scripts/"):
                categories["scripts"].append(name)
            elif path.startswith("sounds/"):
                categories["sounds"].append(name)
            else:
                categories["others"].append(name)
        return categories

    def read_script(self, script_name: str) -> str:
        """Reads the GML code of an existing script asset."""
        gml_path = os.path.join(self._asset_dir("scripts", script_name), f"{script_name}.gml")
        if not os.path.exists(gml_path):
            raise FileNotFoundError(f"Script GML file not found: {gml_path}")
        with open(gml_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_scripts(self) -> List[str]:
        """Returns all script asset names registered in the project."""
        return self.get_resources_by_type().get("scripts", [])

    def _room_path(self, room_name: str) -> str:
        room_yy_path = os.path.join(self._asset_dir("rooms", room_name), f"{room_name}.yy")
        if not os.path.exists(room_yy_path):
            raise FileNotFoundError(f"Room not found: {room_yy_path}")
        return room_yy_path


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print("usage: python gm_project.py <project dir or .yyp>", file=sys.stderr)
        sys.exit(2)
    try:
        project = GMProject(sys.argv[1])
    except (GMError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps({
        "name": project.yyp_data.get("name"),
        "ide_version": project.yyp_data.get("MetaData", {}).get("IDEVersion"),
        "categories": project.get_resources_by_type(),
        "total_resources": len(project.get_resources()),
        "room_order": [n.get("roomId", {}).get("name") for n in project.yyp_data.get("RoomOrderNodes", [])],
    }, indent=2))
