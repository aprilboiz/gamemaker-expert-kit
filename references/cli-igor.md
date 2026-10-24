# Headless Builds with Igor (Windows)

> `Igor.exe` is GameMaker's command-line build driver. This page shows how to build and run a project with it
> from a terminal or your own scripts.

---

## 1. What Igor needs

| Argument | Where it is | Notes |
| :--- | :--- | :--- |
| `Igor.exe` | `C:\ProgramData\GameMakerStudio2-LTS2026\Cache\runtimes\runtime-<version>\bin\igor\windows\x64\` | Non-LTS installs use `GameMakerStudio2` instead of `GameMakerStudio2-LTS2026` |
| `--runtimePath=` | the `runtime-<version>` folder above | Required: without it Igor reports "Cannot find a runtime" |
| `--user=` | `%APPDATA%\GameMakerStudio2-LTS2026\<your user folder>` — the one containing `licence.plist` | Required: you must have logged in to GameMaker once |
| `--project=` | your `.yyp` | |
| `--of=` | output `.win` | Name it after the project (`MyGame.win`): the runner looks for that name when you `Run` |
| `--cache=` / `--temp=` | any writable folders | Keeps build files out of the project |
| `--jsonErrors` | — | Prints a line `{"errors":[{"source": ..., "message": ...}]}` when the build fails |

To pick them automatically, take the newest `runtime-*` folder and the user folder that contains `licence.plist`
(the example below finds the user folder; put your runtime version in `$rt`).

## 2. Commands

`Igor.exe [options] <platform> <command>` — platform `windows`, command:
- `Compile` — build the game (catches syntax and asset errors, **not** calls to functions that don't exist:
  check names against `GmlSpec.xml` in the runtime folder for those).
- `Run` — build and launch; the game's `show_debug_message()` output is printed, so a test game can report
  results and quit with `game_end()`.
- `Clean` — clear the build cache.

## 3. Example

```powershell
$rt  = "C:\ProgramData\GameMakerStudio2-LTS2026\Cache\runtimes\runtime-2026.0.0.23"
$usr = Get-ChildItem "$env:APPDATA\GameMakerStudio2-LTS2026" -Directory |
       Where-Object { Test-Path "$($_.FullName)\licence.plist" } | Select-Object -First 1
& "$rt\bin\igor\windows\x64\Igor.exe" `
  --project="C:\Games\MyGame\MyGame.yyp" `
  --runtimePath="$rt" `
  --user="$($usr.FullName)" `
  --cache="$env:TEMP\igor\cache" --temp="$env:TEMP\igor\temp" `
  --of="$env:TEMP\igor\out\MyGame.win" `
  --jsonErrors `
  windows Run
```

## 4. Reading the result
- Exit code 0 and no `{"errors": ...}` line: success.
- Asset/compile failure: the `errors` line, e.g. `Room1.yy(17,541): Error: Field "x": expected.`
- Runtime error while running: a block starting `ERROR in action number 1 / of Create Event for object obj_x`
  followed by the message and `at gml_Object_obj_x_Create_0 (line N)`. GameMaker then shows a modal error
  dialog and waits, so a build script should stop the game once the error has been printed.
