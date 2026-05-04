"""Rule enforcement for d20play RPG character creation."""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load_data(filename: str) -> dict:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def validate_armor_for_class(armor_name: str, class_name: str) -> bool:
    """Check if a class can wear the given armor."""
    classes = load_data("classes.json")["classes"]
    cls = classes.get(class_name)
    if not cls:
        return False
    
    allowed = cls["armor"]
    if allowed == "all":
        return True
    
    return armor_name.lower() in [a.lower() for a in allowed]


def validate_weapon_for_class(weapon_name: str, class_name: str) -> bool:
    """Check if a class can use the given weapon."""
    classes = load_data("classes.json")["classes"]
    cls = classes.get(class_name)
    if not cls:
        return False
    
    allowed = cls["weapons"]
    if allowed == "all":
        return True
    
    return weapon_name.lower() in [w.lower() for w in allowed]


def get_allowed_weapons(class_name: str) -> list[str]:
    """Return list of weapons a class can use."""
    classes = load_data("classes.json")["classes"]
    cls = classes.get(class_name)
    if not cls:
        return []
    
    if cls["weapons"] == "all":
        gear = load_data("gear.json")
        return list(gear["weapons"].keys())
    
    return cls["weapons"]


def get_allowed_armor(class_name: str) -> list[str]:
    """Return list of armor a class can wear."""
    classes = load_data("classes.json")["classes"]
    cls = classes.get(class_name)
    if not cls:
        return []
    
    if isinstance(cls["armor"], list):
        return cls["armor"]
    return []


def validate_stat_array(stats: list[dict], minimum: int = 2) -> bool:
    """Check if stat array meets the +2 minimum requirement."""
    return any(s["modifier"] >= minimum for s in stats)


def validate_background_skill(background_name: str, skill_name: str) -> bool:
    """Check if a skill is valid for the given background."""
    bgs = load_data("backgrounds.json")["backgrounds"]
    bg = bgs.get(background_name)
    if not bg:
        return False
    
    valid_choices = bg.get("skills", []) + bg.get("languages", [])
    
    if "Any" in valid_choices:
        return True
    
    return skill_name in valid_choices


def validate_spell_for_class(spell_name: str, class_name: str, spell_level: int) -> bool:
    """Check if a spell is available to a class at the given spell level."""
    # TODO: Implement once spells.json is built
    return True


def get_spells_known_count(class_name: str, char_level: int) -> dict:
    """Return how many spells of each level a class knows at the given character level."""
    classes = load_data("classes.json")["classes"]
    cls = classes.get(class_name)
    if not cls or not cls.get("spells_known"):
        return {}
    
    level_str = str(char_level)
    return cls["spells_known"].get(level_str, {})


def validate_gear_slots(gear_list: list[dict], capacity: int) -> bool:
    """Check if total gear slots don't exceed carrying capacity."""
    total = sum(item.get("slots", 1) for item in gear_list)
    return total <= capacity


def get_class_casting_stat(class_name: str) -> str | None:
    """Return the casting stat for a class, or None if non-caster."""
    classes = load_data("classes.json")["classes"]
    cls = classes.get(class_name)
    if not cls or not cls.get("spellcasting"):
        return None
    return cls.get("casting_stat")


if __name__ == "__main__":
    # Quick validation tests
    print("Fighter can wear Plate:", validate_armor_for_class("Plate", "Fighter"))
    print("Wizard can wear Plate:", validate_armor_for_class("Plate", "Wizard"))
    print("Thief can use Longsword:", validate_weapon_for_class("Longsword", "Thief"))
    print("Thief can use Shortsword:", validate_weapon_for_class("Shortsword", "Thief"))
    print("Fighter allowed weapons:", get_allowed_weapons("Fighter")[:5], "...")
    print("Wizard spells at L1:", get_spells_known_count("Wizard", 1))
    print("Wizard casting stat:", get_class_casting_stat("Wizard"))
    print("Fighter casting stat:", get_class_casting_stat("Fighter"))
