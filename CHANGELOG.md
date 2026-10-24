# Changelog

## 1.0.0

### Validator (`gm_validate_project`)
Project-structure rules come from errors reproduced with GameMaker LTS 2026 (runtime 2026.0.0.23):
- Broken references between assets: sprites, parents, collision objects, tilesets, room instances, room order.
- Fields the compiler requires: `.yyp` `resourceType`/`resourceVersion`, tile layer `x`/`y`, instance fields.
- Tile layers that are 0×0 or whose data doesn't match their size (`tilemap element corrupted` at runtime).
- Tilesets without `output_tileset.png` (they collide but draw nothing).
- Missing and orphaned event files; rooms missing from the room order; duplicate layers.
- GML rules: assigning the built-in globals `health`/`score`/`lives`, double movement with `hspeed`/`vspeed`,
  removed functions, legacy `argumentN`, mouse coordinates in Draw GUI. Strings and comments are ignored.

### Knowledge
- `SKILL.md` rewritten around workflow, rules and troubleshooting.
- References rewritten. Event order, built-in behaviour and GML semantics were measured on the runtime; every
  GML snippet compiles and only calls functions that exist in the runtime's API.

### MCP server
- Tool errors are returned as `isError` results; protocol version negotiation; UTF-8 stdio; opt-in logging.
- Malformed messages (bad params, deep nesting, `NaN`, invalid UTF-8) return JSON-RPC errors instead of stopping
  the server. Asset names are validated so no path can leave the project folder.

### Project
- MIT license, requirements, CI on Ubuntu and Windows (Python 3.9 and 3.12), tests on a committed fixture project,
  and a check that keeps machine paths and personal data out of the repository.
- The project-building tools of 0.x (creating projects, sprites, rooms and builds) are now part of GameMaker Expert
  Kit Pro, described at the end of the README.
