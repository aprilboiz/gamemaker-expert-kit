# GameMaker Project Format (LTS 2024 / 2026, Format 2.0)

> What the IDE and the compiler expect on disk. Every rule marked ✔ was found by compiling generated
> projects with Igor; `gm_validate_project` checks all of them.

---

## Files

```
MyGame/
├── MyGame.yyp                 project manifest (JSON)
├── MyGame.resource_order      IDE tree order (optional; keep it if present)
├── options/main/options_main.yy, options/windows/options_windows.yy
├── objects/<name>/<name>.yy + one .gml per event (Create_0.gml, Step_0.gml, Collision_obj_wall.gml, ...)
├── sprites/<name>/<name>.yy + <frame-guid>.png + layers/<frame-guid>/<layer-guid>.png
├── tilesets/<name>/<name>.yy + output_tileset.png
├── rooms/<name>/<name>.yy
└── scripts/<name>/<name>.yy + <name>.gml
```

Every asset is `<kind>/<name>/<name>.yy` and must be registered in the `.yyp` `resources` array:
`{"id": {"name": "obj_player", "path": "objects/obj_player/obj_player.yy"}}`. References between assets use
the same `{name, path}` shape. Asset names must be valid identifiers (letters, digits, `_`).

## JSON dialect
The IDE writes **trailing commas** (`[1, 2,]`). Parse with a reader that tolerates them; standard JSON
(no trailing commas) is accepted when reading back.

## `.yyp` ✔
- Top level needs `"resourceType": "GMProject"` and `"resourceVersion": "2.0"`; without them the project does not load.
- `RoomOrderNodes` lists rooms in order; **the first one is the start room**. Rooms missing from it can't be
  reached with `room_goto_next()`.
- `Folders` holds IDE folders (`folders/Sprites.yy`, ...). Projects created by the IDE start with none; an asset's
  `parent` should point to a folder that exists.

## Objects
`eventList` entries: `{"$GMEvent": "v1", "eventType": 3, "eventNum": 0, "collisionObjectId": null, ...}`.
The code lives in a file whose name is derived from the event — the IDE ignores files with other names:

| Event | File |
| :--- | :--- |
| `[0, 0]` Create | `Create_0.gml` |
| `[2, N]` Alarm N | `Alarm_N.gml` |
| `[3, 0/1/2]` Step / Begin / End | `Step_0.gml` / `Step_1.gml` / `Step_2.gml` |
| `[4, -]` Collision with obj_x | `Collision_obj_x.gml`, with `collisionObjectId` = obj_x and `eventNum` 0 |
| `[7, N]` Other | `Other_N.gml` |
| `[8, N]` Draw / Draw GUI | `Draw_0.gml` / `Draw_64.gml` |
| `[12, 0]` Clean Up | `CleanUp_0.gml` |

`parentObjectId` makes the object inherit every event it doesn't define.

## Sprites
`$GMSprite` `"v2"` with `frames` (one GUID per frame), one image `layer`, and a `sequence` whose frames track
has one keyframe per frame. `origin` is an enum: 0 top-left, 4 centre, **9 custom** (then `xorigin/yorigin`
in `sequence` are used).

## Tilesets ✔
`$GMTileSet` `"v1"` referencing a sprite. The compiler takes the tile graphics from
**`tilesets/<name>/output_tileset.png`**, which the IDE generates: tiles re-flowed into `out_columns` columns,
each padded by `out_tilehborder`/`out_tilevborder` pixels (2) that repeat the tile's edge pixels.
Without that file the tileset loads and collides but **draws nothing**.

## Rooms ✔
Layers are listed **top to bottom** (lowest depth first); the background layer is normally last.

- **`GMRInstanceLayer`**: `instances` — each `"$GMRInstance": "v4"` with `objectId`, `x`, `y`,
  `inheritCode: false`. Every instance is also listed in the room's `instanceCreationOrder`.
- **`GMRTileLayer`**: needs `x` and `y` (else *Field "x": expected* and the room doesn't load) and a `tiles`
  block whose size covers the room:
  ```json
  "tiles": {"SerialiseWidth": 60, "SerialiseHeight": 34, "TileDataFormat": 1,
            "TileCompressedData": [-2040, 0]}
  ```
  `TileCompressedData` is run-length encoded: a negative count `-n` repeats the next value `n` times, a positive
  count `n` is followed by `n` literal values. Uncompressed `TileSerialiseData` (one value per cell) also loads.
  A 0×0 block loads, but every `tilemap_get`/`tilemap_set` then fails with *"tilemap element corrupted"*.
- **`GMRBackgroundLayer`**: `colour` (ABGR integer, e.g. `0xFF2C1C1A`), optional `spriteId`, `htiled/vtiled/stretch`.
- `views[0]`: `wview/hview` (area of the room shown) and `wport/hport` (size on screen); `viewSettings.enableViews`.
