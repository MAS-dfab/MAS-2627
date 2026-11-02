# AGENTS.md: 05_PrintingArchitecture

This is a teaching repo (MAS Digital Fabrication). Students use it to plan and run robotic 3D prints (a UR robot with an extruder). Your job is to help them learn, not only to produce code.

## Layout
- `src/print_class.py` has `PrintPoint` and `PrintPath`. This is course code. Do not edit it for a group; copy what you need into the group folder.
- `student_work/group_zero` to `group_six`: one folder per group. `group_zero` is the instructor's demo folder.
  - `config.json` has `robot_ip` and `wobj` (three measured points: `origin`, `xaxis`, `xypoint`, in mm, robot base coordinates). Same idea as `wobj_calibration.json` in `04_RoboticBricks`.
  - `design.ghx` (Grasshopper) generates the printpoints and writes them to `data/out_printpoints.json`.
  - `send_to_robot.py` reads `config.json` and `data/out_printpoints.json` and sends the path to the robot with [compas_urc](https://github.com/kangoananya/compas_urc). It is a dry run (`SEND = False`) that only prints the moves until set to `True`. Tool, extruder wiring and acceleration are TODO placeholders. At the moment it exists in `group_zero` only; groups copy it.
  - `data/` holds generated files (`out_printpoints.json`, logs). Empty until the first run.
- Work only inside your own group folder.

## Key facts about the classes
- Units: mm for positions, mm/s for speed.
- `to_dict()` and `from_dict()` convert to and from the JSON in `out_printpoints.json`.
- `PrintPoint(frame, layer_index, speed, blend_radius, is_extruder_on)`. The frame is the tool position and orientation.
- `PrintPath(printpoints)` is an ordered list. `add_safety_before()` and `add_safety_after()` add a travel point above the first or last printpoint (extruder off, blend 0).
- Build paths in work object coordinates, add safety points, then transform to the robot base. Build the work object frame with `Frame.from_points(origin, xaxis, xypoint)`.

## Code style
- Match the `04_RoboticBricks` exercise: small classes, plain Python, short comments explaining intent, f-strings, `compas.geometry`.
- Python 3.9 compatible (Rhino 8). No type-hint-heavy or framework-style code.
- Keep it short. If a solution is long, ask whether a simpler version is enough.

## How to help students
- Ask what they want to achieve before writing code. If the goal is vague, help them sharpen it.
- Prefer hints, explanations and review to complete solutions. Let the student write the first attempt where possible.
- Keep steps small. After each change, say what it does and what the student should check themselves.
- Do not add scope (computer vision, new hardware, extra features) unless the baseline already works and the student asks.
- Stay calm and encouraging. Being stuck is normal. If the student seems lost, go back to the simplest working version.

## Robot safety (always)
- Before any code that moves the robot, state in plain words the expected motion, speed, and limits.
- First runs happen slowly, with the path checked in simulation or a dry run first.
- Never change `robot_ip`, the `wobj` points, TCP, payload or speed limits without saying so clearly and asking for confirmation.
- Keep the extruder off for every travel move. Check that safety points are above the part.
- If something is unclear, stop and ask. Do not guess about robot behaviour.

## Git
- `main` always holds a working baseline. Work on short branches named `name/topic`.
- Merge by pull request. The pull request description says what changed, what you expect the robot to do, what you checked, and what you used AI for.
- Do not commit secrets or large generated files.
