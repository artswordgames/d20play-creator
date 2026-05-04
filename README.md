# d20play RPG Character Creator

A character creation tool for the d20play RPG system.

## Project Structure

```
d20play-creator/
├── README.md
├── main.py                  # Entry point — terminal app
├── character.py             # Character class — holds all PC data
├── creator.py               # Creation flow — step-by-step wizard
├── roller.py                # Dice rolling and stat generation
├── validators.py            # Rule enforcement (class/armor/weapon restrictions)
├── exporter.py              # Output to text, PDF, JSON
├── data/
│   ├── stats.json           # d20-to-modifier table, default array
│   ├── races.json           # All races, talents, languages, speed
│   ├── classes.json         # All classes, HD, talents, spells known
│   ├── backgrounds.json     # Backgrounds, skill/language choices
│   ├── gear.json            # Weapons, armor, adventuring gear, costs, slots
│   └── spells.json          # All spells by class and level (TODO)
├── output/                  # Generated character sheets go here
└── templates/
    └── character_sheet.py   # PDF template matching Tom's sheet layout
```

## Setup

1. Clone/copy this directory into your VS Code workspace
2. Python 3.10+ required
3. Install dependencies: `pip install fpdf2` (for PDF output)
4. Run: `python main.py`

## Design Principles

- **Data-driven**: All game data in JSON files — easy to update per version
- **Strict enforcement**: Invalid choices blocked, stats validated, restrictions applied
- **Separation of concerns**: Game logic (creator.py, validators.py) separate from UI (main.py) and output (exporter.py)
- **Future-ready**: Logic layer reusable for web/iOS app — just swap main.py for a web frontend

## Rules Version

Currently targets **d20play RPG v0.2.8.1**.
Update JSON files in `data/` when new versions release.
