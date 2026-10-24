---
name: gamemaker-expert
description: Modern GameMaker (LTS 2024/2026, GML 2.3+) development. Use when creating, modifying, debugging, validating or reviewing GameMaker projects (.yyp, .yy, .gml), writing GML, or planning a game from an art pack.
when_to_use: "Working in a GameMaker project folder (a .yyp file), writing or fixing GML, scaffolding rooms/objects/sprites/tilesets, or turning an asset pack into a game."
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
version: 1.0.0
---

# GameMaker Expert

Modern GameMaker knowledge plus tools that read and validate projects the way the IDE and the compiler will.
Paths below are relative to this skill's folder.

## 1. Tools

The MCP server (`mcp/server.py`) exposes these tools; the same checks run from the command line.

| Tool | CLI | Use |
| :--- | :--- | :--- |
| `gm_read_project` | `python scripts/gm_project.py <project>` | Asset catalog by type, room order, IDE version |
| `gm_validate_project` | `python scripts/gm_lint.py <project>` | Broken references, missing files, fields the compiler requires, GML pitfalls |
| `gm_inspect_assets` | `python scripts/gm_asset_inspector.py <folder>` | Facts about an art folder: sizes, filmstrips, tile grids, tags |
| `gm_read_script` | — | Source of a script asset |

If tools that create or edit assets are available (for example `gm_create_project`), prefer them. Otherwise
create and edit assets by writing files exactly as described in
[`references/project-format.md`](references/project-format.md), then run `gm_validate_project`.

## 2. Workflow for any change

1. **Read first:** `gm_read_project`, then the objects/scripts involved. Match the project's naming and style.
2. **Change** through tools where possible; when editing `.yy` files by hand, follow `project-format.md`
   (register new assets in the `.yyp`, keep `{name, path}` references consistent).
3. **Validate:** `gm_validate_project` must report `passed: true` — fix every error, read every warning.
4. **Build and run** before saying the work is done: with a build tool if one is available, otherwise in the IDE
   or with Igor ([`references/cli-igor.md`](references/cli-igor.md)).

## 3. GML rules that prevent the usual bugs

1. **Modern API only.** `instance_create_layer`/`instance_create_depth` (not `instance_create`),
   `game_get_speed(gamespeed_fps)` (not `room_speed`), named parameters (not `argument0`). Calls to functions
   that don't exist **compile** and crash later — see [`gml-pitfalls.md`](references/gml-pitfalls.md).
2. **Own your movement variables.** Built-in `hspeed`/`vspeed` move the instance automatically after Step;
   use `hsp`/`vsp` and move with collisions:
   ```gml
   function move_solid(_dx, _dy, _solids) {
       var _hit_x = place_meeting(x + _dx, y, _solids);
       if (_hit_x) {
           while (sign(_dx) != 0 && !place_meeting(x + sign(_dx), y, _solids)) x += sign(_dx);
       } else {
           x += _dx;
       }
       var _hit_y = place_meeting(x, y + _dy, _solids);
       if (_hit_y) {
           while (sign(_dy) != 0 && !place_meeting(x, y + sign(_dy), _solids)) y += sign(_dy);
       } else {
           y += _dy;
       }
       return { hit_x: _hit_x, hit_y: _hit_y };
   }
   ```
   `_solids` can be a tilemap id (`layer_tilemap_get_id("Tiles_Collision")`), an object, or an array of both.
3. **Never name variables `health`, `score` or `lives`** — they are built-in globals shared by every instance.
4. **Free memory in Clean Up**, not Destroy: ds_*, surfaces, buffers, created cameras, time sources.
5. **Event order:** Begin Step → Alarms → Step → *built-in motion* → Collision → End Step → Draw → Draw GUI.
   Cameras follow in **End Step**; count or find other instances in **Room Start** (Create order is not guaranteed).
6. **Script files run once at game start:** only functions, constructors, `enum`, `#macro` and `global.` defaults.
7. **Arrays and structs are references;** `struct[$ "key"] ?? fallback` for optional keys (`struct.key` throws if missing).
8. **Draw GUI is screen space:** use `device_mouse_x_to_gui(0)` there, not `mouse_x`.
9. **One responsibility per object;** shared behaviour in parent objects (`obj_enemy_parent`) and script
   functions — see [`gml-solid-architecture.md`](references/gml-solid-architecture.md).
10. **Tile index, not tile data:** `tile_get_index(tilemap_get_at_pixel(tm, x, y))`; tile 0 is empty.

## 4. Planning a game from an art pack

1. `gm_inspect_assets` on the folder: filmstrips (frame counts), tile sizes (grid factors), tags.
2. Audit what exists and what is missing: player animations (idle/run/jump/attack/hurt), tiles (floor/wall),
   props and pickups, UI, audio. Say explicitly what is missing.
3. Offer 2–3 designs: **A** uses only the existing assets; **B** is the best-fit genre plus a list of missing
   assets; **C** an unusual combination of what's there.
4. For the chosen design, specify objects (with parents), events, sprites to slice (cell size, frames) and whether
   collisions are tilemap- or object-based.

## 5. Proving gameplay works

A build that compiles can still be unplayable. Drive the game from code and print results:

- Read input through one function (e.g. `input_read()`) that returns `global.input_override` when it is a struct.
- Add a test-only object whose Step sets `global.input_override`, prints facts with
  `show_debug_message("MARKER:" + string(value))` and calls `game_end()` after N frames.
- Run the game (IDE, Igor `Run`, or a build tool) and read the markers from the output.

## 6. Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `Field "x": expected` loading a room | Tile layer without `x`/`y` | Add `"x": 0, "y": 0` to the `GMRTileLayer` |
| `Field "resourceType": expected` in the `.yyp` | Hand-made `.yyp` missing top-level fields | Add `"resourceType": "GMProject", "resourceVersion": "2.0"` |
| `tilemap element corrupted` | Tile layer is 0×0 | Size `tiles` to the room (`project-format.md`) |
| Tiles collide but are invisible | Tileset has no `output_tileset.png` | Re-create the tileset with the tools or save it once in the IDE |
| `... not set before reading it` | Variable read before assignment (often in another instance's Create) | Initialise in Create; read other instances in Room Start/Step |
| Function "does nothing" or crashes when reached | Called a function that doesn't exist | Check the name in the manual or in `GmlSpec.xml` in the runtime folder, which lists every built-in function |
| Object moves twice as fast as expected | `hspeed`/`vspeed` plus manual `x +=` | Use your own `hsp`/`vsp` |

## 7. References

| File | Topic |
| :--- | :--- |
| [`gml-events-guide.md`](references/gml-events-guide.md) | Event catalog with `[type, num]`, measured frame order, Clean Up vs Destroy, time sources |
| [`gml-pitfalls.md`](references/gml-pitfalls.md) | Verified behaviours that cause bugs: built-ins, references, scope, numbers, errors |
| [`gml-scripts-and-functions.md`](references/gml-scripts-and-functions.md) | Script boot rule, functions vs methods, constructors, static |
| [`gml-solid-architecture.md`](references/gml-solid-architecture.md) | Object responsibilities, parents, components, events bus, state machines |
| [`tilemaps-and-collisions.md`](references/tilemaps-and-collisions.md) | Tileset pipeline, `place_meeting` with tilemaps, editing tiles |
| [`camera-and-views.md`](references/camera-and-views.md) | End Step camera, screen shake, view vs port, GUI size |
| [`audio-and-sound-management.md`](references/audio-and-sound-management.md) | Playback with variation, audio groups, buffer sounds |
| [`project-format.md`](references/project-format.md) | `.yyp`/`.yy` rules the compiler enforces |
| [`cli-igor.md`](references/cli-igor.md) | Building and running from the command line |

Every GML block in these files compiles on LTS 2026 and only uses functions that exist in its runtime
(checked by the kit's test suite).
