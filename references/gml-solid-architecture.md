# SOLID & Clean Architecture for GameMaker (LTS 2024 / 2026)

> How to structure maintainable GameMaker projects without monolithic controller objects.

---

## The monolithic anti-pattern

```
❌ obj_game (thousands of lines)
 ├── player input & physics
 ├── enemy spawning & AI
 ├── collision detection
 ├── HUD drawing
 └── camera tracking
```
Every change touches the same file, bugs interact, and nothing can be reused.

---

## S — Single Responsibility: one reason to change per object

| Object | Owns | Main events |
| :--- | :--- | :--- |
| `obj_player` | input → movement, state machine, taking damage | Create, Step, Draw |
| `obj_enemy_parent` | shared enemy behaviour (chase, damage, death) | Create, Step, Collision, Draw |
| `obj_spawner` | wave pacing | Create, Alarm 0 |
| `obj_camera` | follow target, screen shake | Create, End Step |
| `obj_hud` | drawing UI only | Draw GUI |
| `obj_game` | session state, restart, audio init | Create, Step |

Cross-cutting helpers (input, movement, camera shake) live in **script functions**, not in objects.

## O — Open/Closed: parent objects

Collide with the **parent**, never with each concrete child. Adding `obj_enemy_bat` then needs no changes
to the player, the sword, or the HUD.

```gml
// obj_slash, Collision event with obj_enemy_parent (fires for every child too)
if (!array_contains(hit_list, other.id)) {
    array_push(hit_list, other.id);
    other.take_damage(1, x, y);
}
```

## L — Liskov: children keep the parent's contract

A child's Create calls `event_inherited()` first, then changes only data. It may tune `hp` or `spd`,
but `take_damage(amount, from_x, from_y)` must keep working the same way for every caller.

```gml
// obj_enemy_bat, Create event (parent: obj_enemy_parent)
event_inherited();
hp = 1;
spd = 1.1;
chase_range = 260;
```

## I — Interface Segregation: small component structs

Give objects only the capabilities they need, as constructor structs. Use `static` for methods so they
exist once and are shared by every struct instance, instead of being re-created for each one.

```gml
function HealthComponent(_max_hp) constructor {
    max_hp = _max_hp;
    hp = _max_hp;

    static take_damage = function(_amount) {
        hp = max(0, hp - _amount);
        return hp == 0; // true when this hit was fatal
    };

    static heal = function(_amount) {
        hp = min(max_hp, hp + _amount);
    };

    static is_dead = function() {
        return hp <= 0;
    };
}

// obj_player Create:   hp_comp = new HealthComponent(5);
// obj_crate Create:    hp_comp = new HealthComponent(2);
// Anywhere:            if (other.hp_comp.take_damage(1)) instance_destroy(other);
```

> ⚠️ Do not name the variable `health`, `score` or `lives`: those are **built-in global** variables
> (deprecated, but still present). `health = new HealthComponent(5)` in two objects writes the same global,
> so the player and every crate share one health value. `gm_validate_project` warns about this.

## D — Dependency Inversion: talk to abstractions, not instances

Code that reaches into another object directly (`obj_player.coins += 1`) crashes when that instance
does not exist and ties both objects together. Depend on a small API instead: a function or event
that the owner implements.

```gml
// scr_events: a tiny publish/subscribe bus
global.listeners = {};

function events_on(_name, _callback) {
    if (!struct_exists(global.listeners, _name)) {
        global.listeners[$ _name] = [];
    }
    array_push(global.listeners[$ _name], _callback);
}

function events_emit(_name, _data = undefined) {
    var _list = global.listeners[$ _name] ?? [];
    for (var _i = 0; _i < array_length(_list); _i++) {
        _list[_i](_data);
    }
}

// obj_hud Create:      events_on("coin_collected", function(_value) { coins_shown += _value; });
// obj_coin Collision:  events_emit("coin_collected", 1); instance_destroy();
```

Callbacks created in an instance's event are bound to that instance; if listeners can be destroyed,
remove them in their Clean Up event or check `instance_exists` inside the callback.

---

## State machines

An `enum` plus a `switch` is the clearest pattern for most characters. Declare the enum in a **script**
(enums are global and compile-time), keep the state in an instance variable.

```gml
// scr_player_states
enum PSTATE { IDLE, RUN, ATTACK, HURT }

// obj_player Step (excerpt)
function player_update_state(_input_x, _attack_pressed) {
    switch (state) {
        case PSTATE.IDLE:
            if (_input_x != 0) state = PSTATE.RUN;
            if (_attack_pressed) state = PSTATE.ATTACK;
            break;
        case PSTATE.RUN:
            if (_input_x == 0) state = PSTATE.IDLE;
            if (_attack_pressed) state = PSTATE.ATTACK;
            break;
        case PSTATE.ATTACK:
            // Leave the state from the Animation End event (Other, 7)
            break;
    }
}
```

For many states with their own enter/exit logic, use one struct per state:

```gml
function State(_name) constructor {
    name = _name;
    static enter = function(_owner) {};
    static step = function(_owner) {};
    static leave = function(_owner) {};
}

function state_change(_owner, _next) {
    if (_owner.state != undefined) _owner.state.leave(_owner);
    _owner.state = _next;
    _next.enter(_owner);
}
```
