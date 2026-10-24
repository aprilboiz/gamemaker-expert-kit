# GameMaker Object Events (LTS 2024 / 2026)

> What each event is for, when it runs, and its `[eventType, eventNum]` as stored in the object's `.yy`.
> The frame order below was measured on runtime 2026.0.0.23 (one instance logging every event).

---

## Frame order (verified)

```
Create ─ Room Start ─┐                      (once, when the room starts)
                     ▼
   ┌──► Begin Step ─► Alarm N ─► Step ─► [engine applies speed/hspeed/vspeed/gravity/path]
   │        ─► Collision ─► End Step ─► Pre Draw ─► Draw ─► Post Draw ─► Draw GUI ──┐
   └────────────────────────────────────── next frame ◄───────────────────────────┘
Clean Up                                    (whenever the instance stops existing)
```

Consequences:
- **Built-in motion is applied after Step.** If you set `hspeed` and also do `x += hspeed`, the instance moves
  twice. Use your own `hsp`/`vsp` (see `tilemaps-and-collisions.md`).
- **Collision events see post-movement positions**; End Step sees everything final — that is where cameras
  and "snap to ground" logic belong.
- **Room Start runs after every instance of the room has been created**, so it is the safe place to count or
  find other instances. A Create event cannot assume another instance's Create has already run.

---

## Event catalog

| Event | `[type, num]` | Use it for |
| :--- | :--- | :--- |
| Create | `[0, 0]` | Initialise variables, structs, methods (`take_damage = function() {}`), cache layer/tilemap ids |
| Destroy | `[1, 0]` | Gameplay reaction to `instance_destroy()`: loot, particles, sounds |
| Clean Up | `[12, 0]` | **Free memory** (ds_*, surfaces, buffers, cameras you created). Runs on destroy, room end *and* game end |
| Alarm N | `[2, N]` (N = 0–11) | Simple countdown timers: `alarm[0] = game_get_speed(gamespeed_fps) * 2;` |
| Begin Step | `[3, 1]` | Read input, reset per-frame flags |
| Step | `[3, 0]` | Gameplay: state machines, movement with collisions |
| End Step | `[3, 2]` | Camera follow, final clamps, facing direction |
| Collision with X | `[4, "obj_x"]` | Reacting to touching X (and all of X's children). `other` is the instance touched |
| Room Start / End | `[7, 4]` / `[7, 5]` | Setup that needs every room instance; saving state on exit |
| Animation End | `[7, 7]` | Leaving one-shot animation states (attack, hurt) |
| User Event N | `[7, 10 + N]` (N = 0–15) | Callable hooks for polymorphism: `event_user(0)` |
| Draw | `[8, 0]` | World-space drawing. Defining it replaces the automatic `draw_self()` |
| Draw GUI | `[8, 64]` | Screen-space HUD/menus, independent of the camera |
| Pre / Post Draw | `[8, 72]` / `[8, 73]` | Whole-screen effects before/after all Draw events |

### Destroy vs Clean Up
`Destroy` only runs when `instance_destroy()` is called. Changing room or closing the game does **not** run it,
so memory freed there leaks in those cases. Free resources in **Clean Up**:

```gml
// Clean Up event
if (ds_exists(path_points, ds_type_list)) ds_list_destroy(path_points);
if (surface_exists(trail_surface)) surface_free(trail_surface);
if (buffer_exists(audio_buffer)) {
    audio_free_buffer_sound(audio_sound);
    buffer_delete(audio_buffer);
}
```

### Alarms vs time sources
Alarms count **frames** of one instance and stop when it is destroyed or deactivated. For timers with
callbacks, real seconds, repetition or pausing, use time sources:

```gml
function after_seconds(_seconds, _callback) {
    var _ts = time_source_create(time_source_game, _seconds, time_source_units_seconds, _callback);
    time_source_start(_ts);
    return _ts; // keep it to time_source_stop()/time_source_destroy() it
}
```

### Draw replaces the default
Adding a Draw event turns off GameMaker's automatic drawing of the sprite. Call `draw_self()` (or
`draw_sprite_ext(...)`) yourself, for example to flip the player without changing its mask.

### Draw GUI and the mouse
Draw GUI uses GUI coordinates. `mouse_x`/`mouse_y` are room coordinates, so in Draw GUI use
`device_mouse_x_to_gui(0)` / `device_mouse_y_to_gui(0)`.
