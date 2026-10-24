# Audio & Sound (LTS 2024 / 2026)

> Playing sounds with variation, volume mixing with audio groups, and sounds generated at runtime.

---

## 1. Playing sounds

`audio_play_sound(sound, priority, loop, [gain], [offset], [pitch], [listener_mask])` returns a **sound
instance**; pass that to `audio_sound_*` functions to affect only that playback.

```gml
/// @desc Plays a one-shot sound with slight random pitch/volume so repeats don't sound mechanical.
function sfx_play(_sound, _pitch_range = 0.08) {
    var _pitch = random_range(1 - _pitch_range, 1 + _pitch_range);
    var _gain = random_range(0.95, 1.0);
    return audio_play_sound(_sound, 1, false, _gain, 0, _pitch);
}
```

Music with a fade-in, and stopping it:

```gml
function music_play(_track, _fade_ms = 1000) {
    var _inst = audio_play_sound(_track, 10, true, 0);
    audio_sound_gain(_inst, 1, _fade_ms);
    return _inst;
}

function music_stop(_inst, _fade_ms = 500) {
    audio_sound_gain(_inst, 0, _fade_ms);
    // stop after the fade: see after_seconds() in gml-events-guide.md
}
```

## 2. Audio groups for volume settings

Assign each sound to an audio group in the IDE (e.g. `audiogroup_sfx`, `audiogroup_music`), then drive the
group gains from your options menu instead of changing every sound.

```gml
// Load non-default groups once at startup (audiogroup_default is always loaded)
function audio_groups_load(_groups) {
    for (var _i = 0; _i < array_length(_groups); _i++) {
        if (!audio_group_is_loaded(_groups[_i])) {
            audio_group_load(_groups[_i]);
        }
    }
}

// Options menu
function audio_set_volumes(_master, _sfx_group, _sfx, _music_group, _music) {
    audio_master_gain(_master);
    audio_group_set_gain(_sfx_group, _sfx, 0);
    audio_group_set_gain(_music_group, _music, 300); // 300 ms fade
}
```

## 3. Sounds generated at runtime (buffer sounds)

`audio_create_buffer_sound(buffer, format, rate, offset, length, channels)` makes a sound that **plays directly
from the buffer's memory**. That implies three rules:

1. Allocate the exact size up front with **`buffer_fixed`**. Don't use `buffer_grow` for audio data: growing
   reallocates the memory the sound reads from.
2. Write samples in the format you declare: `buffer_u8` (0–255, silence = 128) or `buffer_s16`.
3. Free in this order — **sound first, then buffer** — and only after the sound has stopped.

```gml
/// @desc A short square-wave beep generated in code. Returns { sound, buffer }.
function beep_create(_freq = 880, _seconds = 0.1, _rate = 22050) {
    var _samples = floor(_rate * _seconds);
    var _buf = buffer_create(_samples, buffer_fixed, 1);
    for (var _i = 0; _i < _samples; _i++) {
        var _phase = frac(_i * _freq / _rate);
        var _fade = 1 - _i / _samples;
        var _value = (_phase < 0.5 ? 1 : -1) * 0.4 * _fade;
        buffer_write(_buf, buffer_u8, clamp(round(128 + _value * 127), 0, 255));
    }
    var _snd = audio_create_buffer_sound(_buf, buffer_u8, _rate, 0, _samples, audio_mono);
    return { sound: _snd, buffer: _buf };
}

/// @desc Frees a beep created with beep_create (call from Clean Up).
function beep_free(_beep) {
    audio_stop_sound(_beep.sound);
    audio_free_buffer_sound(_beep.sound);
    buffer_delete(_beep.buffer);
}
```
