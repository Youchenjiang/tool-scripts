# Exam Seating Planner

[閱讀繁體中文版](README.zh-TW.md)

Arranges exam seats and produces a seating chart to project in the exam room. Rooms and exams are described in JSON config files, so a new room or a new exam needs a config, not a code change.

## Features

- **Real room layouts**: rectangular rooms are described as rows and blocks; irregular rooms (e.g. a fan-shaped lecture hall) are read straight from a PowerPoint drawing, nested and rotated groups included
- **Exact seat spacing**: nobody sits side by side; diagonal neighbours are minimised first (the desk diagonally ahead is visible, the one straight ahead is blocked by its owner); seats closest to the podium are preferred. Solved exactly row by row, not by random search
- **Seating rules**: required rooms or exact seats for given students; consecutive student IDs never around each other
- **Independent rule check**: every rule is re-verified after seating and printed to the terminal
- **Projection-ready slides**: one 16:9 slide per room in its real orientation, every seat drawn (empty ones lighter) so students can find theirs; names upright and sized to fit
- **Reproducible**: a seed in the exam config gives the same chart every run

## Folder structure

```
exam-seating-planner/
├── src/
│   ├── seating.py      # entry point
│   ├── rooms.py        # loads rooms, works out who sits next to whom
│   ├── solver.py       # stage 1: which seats are used
│   ├── assign.py       # stage 2: who sits where, and the rule check
│   ├── render.py       # draws the slides
│   └── pptx_desks.py   # reads desks from a PowerPoint slide
├── rooms/              # one JSON per room (309: grid, 404: from PowerPoint)
├── layouts/            # room drawings referenced by room configs
├── exams/              # example exam config
├── data.example/       # fictional roster for the example
├── data/               # [git-ignored] your real rosters and exam configs
└── output/             # [git-ignored] generated charts
```

## Quick start

```bash
pip install -r requirements.txt
python src/seating.py exams/example.json
```

This seats 60 fictional students in rooms 309 and 404 and writes two files to `output/`:

- `<exam>_<course>_seating-chart.pptx`: the chart shown to students. Names and IDs on their seats; the only other text is the room name. The rule check stays in the terminal so no student's special arrangement appears on screen.
- `<exam>_<course>_seat-layout-preview.pptx`: internal. Used seats in blue, every seat labelled with its seat code.

## Using real data

Keep real rosters and exam configs in `data/`; it is git-ignored, so they are never committed.

1. Put the roster (`.xlsx`) in `data/`. Any sheet layout works as long as one row holds the name and ID column headers.
2. Copy `exams/example.json` to `data/<exam>.json` and point it at the roster (paths are relative to the config file):
   ```json
   "roster": "roster.xlsx",
   "roster_columns": ["Name", "ID"],
   "output": "../output"
   ```
3. Run `python src/seating.py data/<exam>.json`.

## Room config

Both types end up as "a set of desks, each with a position and an angle", and the same neighbour rules then apply to every room.

**Grid** (`rooms/309.json`)

```json
{
  "name": "309",
  "type": "grid",
  "rows": 8,
  "blocks": [3, 3, 3],
  "blocked": [[8, 5]],
  "blocked_label": "Pillar",
  "podium": {"side": "top", "block": 2}
}
```

- `rows`: number of rows; `blocks`: columns per block, with an aisle between blocks
- `blocked`: positions nobody can sit in, as `[row, column]` (1-based; columns count across all blocks)
- `podium`: at the `top` or `bottom`, centred on the given block

**From PowerPoint** (`rooms/404.json`)

```json
{
  "name": "404",
  "type": "pptx",
  "file": "../layouts/room-404.pptx",
  "slide": 1,
  "podium_text": "講桌",
  "stretch_x": 1.1
}
```

- The box whose text equals `podium_text` is the podium; every other box on the slide is a desk (boxes may be grouped and rotated)
- Desks in the same row must be drawn **touching**; that is how rows are recognised
- `stretch_x`: widens the room on the slide; appearance only

## Exam config

```json
{
  "name": "example-midterm",
  "course": "EXAMPLE101",
  "roster": "../data.example/roster.example.xlsx",
  "roster_columns": ["Name", "ID"],
  "rooms": ["309", "404"],
  "counts": {},
  "fixed": {},
  "rules": {
    "room": {"404": ["Student 13", "Student 38"]},
    "seat": {"Student 13": "404 A1-1"},
    "id_apart": true
  },
  "labels": {"podium": "Blackboard", "blocked": "Pillar", "rooms": {"309": "Building I 309"}},
  "seed": 1,
  "output": "../output"
}
```

- `course`: used in the output file names only (never on the slides)
- `roster_columns`: the roster's column headers for name and student ID
- `counts`: fix the head-count of a room, e.g. `{"309": 36}`; omitted rooms are decided by the solver
- `fixed`: seats that must be used or left empty, by seat code, e.g. `{"309": {"sit": ["B1-2"], "empty": ["B1-1", "B1-3"]}}`
- `rules.room`: students who must be in a given room
- `rules.seat`: students who must sit at a given seat, as `"<room> <seat code>"`. They are swapped into place so the rest of the chart stays the same; only if a swap would break a rule is the room searched again
- `rules.id_apart`: students with consecutive IDs must not sit around each other
- `labels` (optional): wording on the slides: `podium`, `blocked` (e.g. pillars) and per-room titles under `rooms`; defaults are `Podium`, the room config's `blocked_label` and `Room <name>`
- `seed`: everyone else is placed in a shuffle seeded by this number; change it for a different arrangement

## Seat codes

`<block><row>-<seat>`, e.g. `B1-2` is block B, row 1, seat 2. Blocks are A, B, C… from left to right as drawn, rows count back from the podium, seats run left to right. The preview file shows every code.

## Seating rules

**Stage 1: which seats are used**

1. Nobody side by side (always met)
2. As few diagonal neighbours as possible
3. As close to the podium as possible

Neighbours come from geometry: touching desks in the same row are side by side; the closest desk in the next row back is front/back, the ones just beside it are diagonal. Each block is a chain of rows from the podium back, so a row-by-row search finds the exact optimum.

**Stage 2: who sits where** (always met; the program stops with an error if it cannot be)

1. Required rooms (`rules.room`) and seats (`rules.seat`)
2. Consecutive student IDs never around each other (`rules.id_apart`). "Consecutive" means next to each other in the roster sorted by ID; "around" means front/back, diagonal, one empty seat away in the same row, or across an aisle in the same row

## Notes

- Slides use the Microsoft JhengHei font (bundled with Windows) so Chinese names render; PowerPoint substitutes a font elsewhere
- Opening a `.pptx` output in PowerPoint and exporting to PDF or images is the easiest way to print or share it
