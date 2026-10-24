# Modern GML Pitfalls (LTS 2024 / 2026)

> Mistakes that compile fine and then misbehave. Everything marked ✔ was checked on runtime 2026.0.0.23.
> Many are flagged automatically by `gm_validate_project` (built-in globals, double movement, legacy calls).

---

## 1. Functions that don't exist compile anyway ✔
GML resolves function names at runtime. `instance_create(...)` (removed years ago) or an invented
`draw_sprite_fancy(...)` **compiles without error** and crashes when that line runs. Older tutorials and
LLM training data are full of these. Check names against `GmlSpec.xml` in your runtime folder (it lists every
built-in function and marks the deprecated ones) or the manual.

| Removed / deprecated | Use |
| :--- | :--- |
| `instance_create(x, y, obj)` | `instance_create_layer(x, y, "Instances", obj)` or `instance_create_depth(x, y, depth, obj)` |
| `room_speed` | `game_get_speed(gamespeed_fps)` |
| `sound_play(snd)` | `audio_play_sound(snd, 1, false)` |
| `argument0`, `argument[i]` | named parameters: `function f(_a, _b = 0)` |
| `globalvar name;` | `global.name` |
| `instance_change()` | create the new instance, destroy the old one |

## 2. Built-in variables that bite
- **`health`, `score`, `lives` are global** ✔ (and deprecated). `health = 10` in one object is seen by every
  object. Use instance variables (`hp`) or a component struct.
- **`hspeed`, `vspeed`, `speed`, `direction`, `gravity`, `friction` move the instance automatically** after
  the Step event ✔. Doing `x += hspeed` as well moves it twice. For controlled movement use your own
  `hsp`/`vsp` variables and `move_solid()` (`tilemaps-and-collisions.md`).
- **`x`, `y`, `image_*`, `sprite_index`, `depth`, `visible`** are per-instance built-ins: naming your own
  variable the same changes engine behaviour.

## 3. Arrays and structs are references ✔
With copy-on-write off (the default for new projects), arrays and structs are passed and assigned **by
reference**. A function that modifies its array argument modifies the caller's array; `b = a` aliases.

```gml
function array_copy_shallow(_source) {
    var _copy = array_create(array_length(_source));
    array_copy(_copy, 0, _source, 0, array_length(_source));
    return _copy;
}

function struct_copy_shallow(_source) {
    var _copy = {};
    var _keys = struct_get_names(_source);
    for (var _i = 0; _i < array_length(_keys); _i++) {
        _copy[$ _keys[_i]] = _source[$ _keys[_i]];
    }
    return _copy;
}
```

`==` on two structs compares **identity**, not contents ✔ (`new Vec(1) == new Vec(1)` is false).

## 4. Missing struct members ✔
- `my_struct[$ "key"]` returns `undefined` when the key is missing — combine it with `??` for defaults.
- `my_struct.key` on a missing key **throws** "not set before reading it".

```gml
function config_get(_config, _key, _default) {
    return _config[$ _key] ?? _default;
}
```

## 5. `self` and `other` ✔
- A method created in an instance's event (`take_damage = function() {}`) stays **bound to that instance**
  even if you store it in a struct. Rebind with `method(target, fn)`.
- Functions in a **struct literal** or **constructor** are bound to that struct.
- In `with (target) { ... }`, `self` is the target and `other` is the instance that ran the `with`.
- In a **Collision event**, `other` is the instance collided with.

```gml
/// @desc Damages every enemy within _radius of the caller; `other` inside `with` is the caller.
function damage_area(_radius, _amount) {
    with (obj_enemy_parent) {
        if (point_distance(x, y, other.x, other.y) <= _radius) {
            take_damage(_amount, other.x, other.y);
        }
    }
}
```

## 6. Numbers and strings ✔
- `/` is always real division (`7 / 2` = 3.5). Integer division is `div` (`7 div 2` = 3).
- `mod` keeps the sign of the left operand (`-7 mod 3` = -1). For a wrapping index use
  `((i mod n) + n) mod n`.
- `string(3.5)` gives `"3.50"` (two decimals); `string(true)` gives `"1"` (`typeof(true)` is `"bool"`).
  Format explicitly: `string("{0} / {1}", coins, total)` or `string_format(value, 0, 1)`.
- String positions are **1-based**: `string_char_at("abc", 1)` is `"a"`.

## 7. Errors: `try` / `catch` / `throw` ✔
Runtime errors raise exceptions with `message`, `longMessage`, `script` and `line`. You can throw your own
values (often a struct).

```gml
function load_json_file(_path) {
    if (!file_exists(_path)) return undefined;
    var _buffer = buffer_load(_path);
    try {
        return json_parse(buffer_read(_buffer, buffer_string));
    } catch (_error) {
        show_debug_message("Bad save file " + _path + ": " + _error.message);
        return undefined;
    } finally {
        buffer_delete(_buffer);
    }
}

function save_json_file(_path, _value) {
    var _text = json_stringify(_value);
    var _buffer = buffer_create(string_byte_length(_text) + 1, buffer_fixed, 1);
    buffer_write(_buffer, buffer_string, _text);
    buffer_save(_buffer, _path);
    buffer_delete(_buffer);
}
```

## 8. Frame-rate independence
Movement in "pixels per step" changes with the game speed. For real-time logic, scale by delta time:

```gml
/// @desc Seconds since the previous frame, clamped so a hitch can't teleport things through walls.
function dt_seconds() {
    return min(delta_time / 1000000, 1 / 20);
}
```

## 9. Resources you must free
`ds_*` structures, surfaces, buffers, created cameras, particle systems and time sources are not garbage
collected. Free them in **Clean Up** (not Destroy — see `gml-events-guide.md`). Prefer arrays and structs,
which are collected automatically.

Surfaces can disappear at any time (window resize, alt-tab): always check before drawing to them.

```gml
function surface_ensure(_surface, _width, _height) {
    if (!surface_exists(_surface)) {
        _surface = surface_create(_width, _height);
    }
    return _surface;
}
// Draw:     trail = surface_ensure(trail, room_width, room_height);
// Clean Up: if (surface_exists(trail)) surface_free(trail);
```

## 10. Scripts run at game start
Every script file runs **once, before the first room**. Put functions, constructors, `enum`s, `#macro`s and
`global.` initial values there — never instance code. Enums and macros are compile-time and global.

## 11. Draw GUI uses GUI coordinates
`mouse_x`/`mouse_y` are room coordinates. In Draw GUI use `device_mouse_x_to_gui(0)` and
`device_mouse_y_to_gui(0)`.
