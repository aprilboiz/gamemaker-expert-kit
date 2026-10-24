# Modern GML Scripts & Functions (LTS 2024 / 2026)

> How scripts work in modern GameMaker: global boot execution, functions vs methods, constructor structs, and best practices.

---

## 🚀 1. The Global Boot Execution Rule

In modern GameMaker (LTS 2024 / 2026 / GML 2.3+):
* **All script files (`.gml`) execute ONCE at game startup**, before the first room loads!
* Code outside of functions runs globally on boot.
* Therefore, script files are the primary place for:
  - Global variable definitions (`global.player_score = 0;`).
  - Enum declarations (`enum STATE { IDLE, WALK, ATTACK }`).
  - Macro constants (`#macro TILE_SIZE 16`, `#macro GRAVITY 0.5`).
  - Function and Constructor definitions.

❌ **Anti-Pattern to Avoid:**
Never place object-specific logic or instance manipulation outside of a function in a script file. It will execute before any instances exist and throw an error!

---

## 🛠️ 2. Global Functions vs Instance Methods

### Global Functions (Declared in Scripts)
Global functions are declared with the `function` keyword directly in script files:
```gml
// In scripts/scr_math/scr_math.gml:
function approach(current, target, amount) {
    if (current < target) {
        return min(current + amount, target);
    } else {
        return max(current - amount, target);
    }
}
```
* Scope: Available globally across all objects, rooms, and scripts without prefix.

### Instance Methods (Declared on Objects/Structs)
Methods are bound to a specific instance using variable assignment:
```gml
// In obj_player Create Event:
take_damage = function(amount) {
    hp -= amount;
    if (hp <= 0) instance_destroy();
};
```

---

## 🏗️ 3. Constructor Structs (OOP in Modern GML)

Constructor functions allow creating lightweight, object-oriented data structures without spawning heavy GameMaker instances:

```gml
// In scripts/scr_vector/scr_vector.gml:
function Vector2(_x = 0, _y = 0) constructor {
    x = _x;
    y = _y;

    static add = function(_other) {
        x += _other.x;
        y += _other.y;
        return self;
    };

    static length = function() {
        return point_distance(0, 0, x, y);
    };

    static normalize = function() {
        var len = length();
        if (len > 0) {
            x /= len;
            y /= len;
        }
        return self;
    };
}
```

### Usage:
```gml
// In any object:
var velocity = new Vector2(3, 4);
var len = velocity.length(); // Returns 5
velocity.normalize();
```

---

## 💡 4. Modern GML Function Best Practices

1. **Default Argument Values:**
   ```gml
   function play_sound_effect(snd, volume = 1.0, pitch = 1.0) {
       var inst = audio_play_sound(snd, 10, false);
       audio_sound_gain(inst, volume, 0);
       audio_sound_pitch(inst, pitch);
       return inst;
   }
   ```
2. **Never Use Legacy `argument0`, `argument[i]`:**
   Named arguments and default values are standard in LTS 2024 / 2026.
3. **Static Methods in Constructors:**
   Always use `static method_name = function() { ... }` inside constructors. Static methods are created once in memory and shared across all struct instances, drastically saving RAM.
