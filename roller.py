"""Dice rolling and stat generation for d20play RPG."""
import random
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_stat_table():
    with open(DATA_DIR / "stats.json") as f:
        return json.load(f)


def roll_d(sides: int) -> int:
    """Roll a single die with the given number of sides."""
    return random.randint(1, sides)


def roll_d20() -> int:
    return roll_d(20)


def d20_to_modifier(roll: int) -> int:
    """Convert a d20 roll to a stat modifier using the stat table."""
    table = load_stat_table()["stat_table_lookup"]
    for entry in table:
        if entry["min"] <= roll <= entry["max"]:
            return entry["modifier"]
    raise ValueError(f"Invalid d20 roll: {roll}")


def roll_stat_array() -> list[dict]:
    """Roll 6d20 in order, return list of {roll, modifier} dicts."""
    results = []
    for _ in range(6):
        roll = roll_d20()
        mod = d20_to_modifier(roll)
        results.append({"roll": roll, "modifier": mod})
    return results


def has_minimum_stat(stats: list[dict], minimum: int = 2) -> bool:
    """Check if at least one stat meets the minimum modifier threshold."""
    return any(s["modifier"] >= minimum for s in stats)


def roll_stats_with_reroll() -> list[list[dict]]:
    """Roll stat arrays, rerolling until at least one has a +2 or higher.
    
    Returns all rolled sets so the player can choose.
    """
    sets = []
    while True:
        stat_array = roll_stat_array()
        sets.append(stat_array)
        if has_minimum_stat(stat_array):
            break
    return sets


def get_default_array() -> list[dict]:
    """Return the default stat array: +2, +1, 0, 0, -1, -2."""
    table = load_stat_table()
    return [{"roll": None, "modifier": m} for m in table["default_array"]]


def roll_hp(hd_size: int, con_mod: int, level: int = 1, min_hp_level1: int = None) -> int:
    """Roll HP for a character.
    
    At level 1, minimum HP applies (e.g., 5 for d8 classes).
    Con modifier only adds if positive.
    """
    roll = roll_d(hd_size)
    if level == 1 and min_hp_level1 is not None:
        roll = max(roll, min_hp_level1)
    con_bonus = max(0, con_mod)
    return roll + con_bonus


def roll_talent(talent_table: list[dict]) -> dict:
    """Roll on a class talent table and return the matching entry."""
    roll = roll_d20()
    for entry in talent_table:
        if entry["roll"][0] <= roll <= entry["roll"][1]:
            return {"roll": roll, **entry}
    raise ValueError(f"No talent found for roll {roll}")


# --- Display helpers ---

STAT_NAMES = ["Str", "Dex", "Con", "Int", "Wis", "Cha"]


def format_modifier(mod: int) -> str:
    """Format a modifier with +/- sign."""
    if mod >= 0:
        return f"+{mod}"
    return str(mod)


def display_stat_array(stats: list[dict], names: list[str] = None) -> str:
    """Format a stat array for display."""
    names = names or STAT_NAMES
    parts = []
    for name, stat in zip(names, stats):
        parts.append(f"{name}: {format_modifier(stat['modifier'])}")
    return " | ".join(parts)


if __name__ == "__main__":
    # Quick test
    print("Rolling stats...")
    sets = roll_stats_with_reroll()
    for i, s in enumerate(sets):
        qualifier = " ✓" if has_minimum_stat(s) else " ✗ (reroll)"
        print(f"  Set {i+1}: {display_stat_array(s)}{qualifier}")
    
    print(f"\nDefault array: {display_stat_array(get_default_array())}")
    
    print(f"\nRolling d8 HP (min 5, Con +2): {roll_hp(8, 2, level=1, min_hp_level1=5)}")
