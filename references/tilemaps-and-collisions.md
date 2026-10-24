# Tilemaps & Collisions (LTS 2024 / 2026)

> Tilesets, tile layers, collision against tilemaps, and editing tiles at runtime.
> Every snippet here compiles on LTS 2026.

---

## 1. The tileset pipeline

1. **Sprite** with the tiles on a grid (e.g. 16×16). Tile **0 is always the empty tile** — leave the first
   cell blank.
2. **Tileset asset** (`$GMTileSet`): tile size, offsets/separation, and `output_tileset.png`.
   The compiler builds the tileset texture from that PNG, which the IDE generates when you save the tileset.
   A tileset without it still collides but **draws nothing**.
3. **Tile layer** (`GMRTileLayer`) in a room, bound to the tileset. Its tile grid must cover the room
   (`SerialiseWidth/Height`); a 0×0 layer loads, but `tilemap_get`/`tilemap_set` fail with
   *"tilemap element corrupted"*.

`gm_validate_project` flags 0×0 layers, missing tileset textures and broken references.

Keep **collision** and **decoration** on separate layers (`Tiles_Collision`, `Tiles_Floor`), so art can change
without changing what is solid.

---

## 2. Why tilemap collision

A wall object per tile means thousands of instances, each with its own events and collision checks.
A tile layer is one element: a lookup by cell, no per-tile instances, and the level stays editable as tiles.

---

## 3. Collide with `place_meeting` — it accepts tilemaps

`place_meeting`, `instance_place`, `position_meeting` and `move_and_collide` accept a **tilemap id**
(or an array mixing tilemaps and objects). They test the instance's collision mask against non-empty tiles,
so there is no bounding-box corner maths and no off-by-one at the right/bottom edge.

```gml
// scr_movement
/// @desc Moves the calling instance by (_dx, _dy), stopping flush against _solids on each axis.
/// @param {Real} _dx
/// @param {Real} _dy
/// @param {Any} _solids  Tilemap id, object, instance, or an array of them
/// @returns {Struct} { hit_x, hit_y }
function move_solid(_dx, _dy, _solids) {
    var _hit_x = place_meeting(x + _dx, y, _solids);
    if (_hit_x) {
        var _step_x = sign(_dx);
        while (_step_x != 0 && !place_meeting(x + _step_x, y, _solids)) {
            x += _step_x;
        }
    } else {
        x += _dx;
    }

    var _hit_y = place_meeting(x, y + _dy, _solids);
    if (_hit_y) {
        var _step_y = sign(_dy);
        while (_step_y != 0 && !place_meeting(x, y + _step_y, _solids)) {
            y += _step_y;
        }
    } else {
        y += _dy;
    }
    return { hit_x: _hit_x, hit_y: _hit_y };
}
```

Use it from the object:

```gml
// obj_player Create
hsp = 0;
vsp = 0;
solids = layer_tilemap_get_id("Tiles_Collision");
mask_index = spr_player_idle; // fixed mask: animation frames and flipping don't change collisions

// obj_player Step
function player_move(_input_x) {
    hsp = _input_x * 2;
    vsp = min(vsp + 0.25, 6);
    var _hit = move_solid(hsp, vsp, solids);
    if (_hit.hit_x) hsp = 0;
    if (_hit.hit_y) vsp = 0;
    var _on_ground = place_meeting(x, y + 1, solids);
    return _on_ground;
}
```

Also block on objects (moving platforms, doors) by passing an array: `move_solid(hsp, vsp, [solids, obj_door])`.

<!-- gml-skip -->
```gml
// ❌ Don't use the built-in hspeed/vspeed for this: GameMaker moves the instance by them automatically
// after the Step event, so this moves it twice per frame (and collision only checked half of it).
hspeed = 2;
x += hspeed;
```

---

## 4. Reading and editing tiles at runtime

`tilemap_get*` returns **tile data**, which packs the index with flip/rotate flags. Always extract the index
with `tile_get_index` before comparing.

```gml
/// @desc Tile index (0 = empty) at a room position.
function tile_index_at(_tilemap, _x, _y) {
    return tile_get_index(tilemap_get_at_pixel(_tilemap, _x, _y));
}

/// @desc Digging / farming / destruction: change the tile under a room position.
function tile_set_at(_tilemap, _x, _y, _index) {
    var _cx = tilemap_get_cell_x_at_pixel(_tilemap, _x, _y);
    var _cy = tilemap_get_cell_y_at_pixel(_tilemap, _x, _y);
    if (_cx < 0 || _cy < 0) return false; // outside the tilemap
    var _data = tilemap_get(_tilemap, _cx, _cy);
    _data = tile_set_index(_data, _index);  // keeps the flip/rotate flags
    tilemap_set(_tilemap, _data, _cx, _cy);
    return true;
}
```

Building a level from code, e.g. from a string map:

```gml
function level_paint(_tilemap, _rows) {
    for (var _y = 0; _y < array_length(_rows); _y++) {
        var _row = _rows[_y];
        for (var _x = 0; _x < string_length(_row); _x++) {
            var _ch = string_char_at(_row, _x + 1); // strings are 1-based
            tilemap_set(_tilemap, _ch == "#" ? 1 : 0, _x, _y);
        }
    }
}
```

For levels designed up front, prefer painting tiles in the room editor: the level is then visible and
editable there.
