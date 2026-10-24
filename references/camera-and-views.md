# Cameras & Views (LTS 2024 / 2026)

> Following camera, screen shake, pixel-perfect scaling and a GUI that doesn't depend on the window.

---

## Three rules

1. **Follow in End Step.** Everything has moved by then (see the frame order in `gml-events-guide.md`);
   following in Step lags one frame behind and jitters.
2. **Set whole-pixel positions.** `floor()` the final camera position or pixel art shimmers.
3. **Fix the GUI size.** `display_set_gui_size()` makes the HUD independent of window size and zoom.

## View vs port

A room view has a **view** (the area of the room shown, e.g. 320×180) and a **port** (its size on screen,
e.g. 960×540). Port = 3 × view gives crisp 3× pixel art. Set both in the room's view settings and turn off texture
interpolation for pixel art (`option_windows_interpolate_pixels = false`).

## `obj_camera`

Using the room's view camera (`view_camera[0]`) means there is nothing to create or free.

```gml
// Create
target = obj_player;
cam = view_camera[0];
cam_w = camera_get_view_width(cam);
cam_h = camera_get_view_height(cam);

trauma = 0;          // 0..1, raised by screen_shake()
trauma_decay = 0.03; // per frame
max_offset = 6;      // pixels at full trauma

// Start on the target instead of sliding in from (0, 0)
if (instance_exists(target)) {
    x = clamp(target.x - cam_w / 2, 0, max(0, room_width - cam_w));
    y = clamp(target.y - cam_h / 2, 0, max(0, room_height - cam_h));
}
display_set_gui_size(cam_w * 2, cam_h * 2);
```

```gml
// End Step
if (instance_exists(target)) {
    var _dest_x = clamp(target.x - cam_w / 2, 0, max(0, room_width - cam_w));
    var _dest_y = clamp(target.y - cam_h / 2, 0, max(0, room_height - cam_h));
    x = lerp(x, _dest_x, 0.15);
    y = lerp(y, _dest_y, 0.15);
}

var _shake = trauma * trauma; // squared: small hits stay subtle, big ones punch
var _ox = random_range(-1, 1) * max_offset * _shake;
var _oy = random_range(-1, 1) * max_offset * _shake;
trauma = max(0, trauma - trauma_decay);

camera_set_view_pos(cam, floor(x + _ox), floor(y + _oy));
```

```gml
// scr_camera
/// @desc Adds screen shake (0..1); it decays on its own.
function screen_shake(_amount) {
    if (instance_exists(obj_camera)) {
        obj_camera.trauma = clamp(obj_camera.trauma + _amount, 0, 1);
    }
}
```

## Creating cameras yourself

If you need extra cameras (split screen, minimap), cameras you create are yours to free:

```gml
// Create
minimap_cam = camera_create_view(0, 0, room_width, room_height);
view_set_camera(1, minimap_cam);
view_set_visible(1, true);

// Clean Up
camera_destroy(minimap_cam);
```
