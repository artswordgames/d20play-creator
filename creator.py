"""
Step-by-step character creation logic for d20play RPG.

No I/O — returns structured data, accepts choices.
Designed to be driven by main.py (terminal) or a future web frontend.
"""
import json
import re
from pathlib import Path

from character import Character
from roller import (
    roll_stats_with_reroll,
    get_default_array,
    roll_hp,
    roll_talent,
    STAT_NAMES,
)

DATA_DIR = Path(__file__).parent / "data"


def _load(filename: str) -> dict:
    with open(DATA_DIR / filename) as f:
        return json.load(f)


class CharacterCreator:
    """
    Drives d20play RPG character creation step by step.

    Call methods in order, passing user choices back in.
    Each step returns structured data; nothing is printed here.
    """

    def __init__(self):
        self.character = Character()
        self._classes = _load("classes.json")["classes"]
        self._races = _load("races.json")["races"]
        self._languages = _load("races.json")["languages"]
        self._backgrounds = _load("backgrounds.json")["backgrounds"]
        self._skills = _load("backgrounds.json")["skills"]
        self._gear_data = _load("gear.json")
        self._spells_data = _load("spells.json")

    # ── Step 1: Identity ──────────────────────────────────────────────────────

    def set_identity(self, name: str, player_name: str):
        self.character.name = name.strip()
        self.character.player_name = player_name.strip()

    # ── Step 2: Stat generation ───────────────────────────────────────────────

    def roll_stat_sets(self) -> list[list[dict]]:
        """Roll stat arrays with auto-reroll. Returns all sets (rerolls included)."""
        return roll_stats_with_reroll()

    def get_default_array(self) -> list[dict]:
        """Return the default stat array: +2, +1, 0, 0, -1, -2."""
        return get_default_array()

    def apply_stats_in_order(self, stat_array: list[dict]):
        """Apply rolled array in order: index 0→Str, 1→Dex, 2→Con, 3→Int, 4→Wis, 5→Cha."""
        for i, name in enumerate(STAT_NAMES):
            self.character.stats[name] = stat_array[i]["modifier"]

    def apply_stats_assigned(self, stat_array: list[dict], assignment: dict):
        """
        Apply rolled array with free assignment.
        assignment = {'Str': 0, 'Dex': 2, ...} — values are indices into stat_array.
        """
        for stat_name, idx in assignment.items():
            self.character.stats[stat_name] = stat_array[idx]["modifier"]

    # ── Step 3: Class ─────────────────────────────────────────────────────────

    def get_class_options(self) -> list[dict]:
        return [
            {
                "name": name,
                "primary_stat": cls["primary_stat"],
                "hd": cls["hd"],
                "description": cls["description"],
                "spellcasting": cls["spellcasting"],
                "armor": cls["armor"],
                "weapons": cls["weapons"],
                "base_talents": cls["base_talents"],
            }
            for name, cls in self._classes.items()
        ]

    def set_class(self, class_name: str):
        cls = self._classes[class_name]
        self.character.class_name = class_name
        self.character.primary_stat = cls["primary_stat"]
        self.character.hd = cls["hd"]
        self.character.hd_size = cls["hd_size"]
        self.character.base_talents = list(cls["base_talents"].keys())

    # ── Step 4: Class step 2b — +1 to stat OR roll class talent ──────────────

    def get_stat_bump_options(self) -> list[dict]:
        """Return stats that can receive +1 (not already at +4)."""
        return [
            {
                "name": s,
                "current": self.character.stats[s],
                "new": self.character.stats[s] + 1,
            }
            for s in STAT_NAMES
            if self.character.stats[s] < 4
        ]

    def apply_stat_bump(self, stat_name: str) -> bool:
        """Add +1 to a stat. Returns False if already at +4."""
        if self.character.stats.get(stat_name, 0) >= 4:
            return False
        self.character.stats[stat_name] += 1
        return True

    def roll_class_talent(self) -> dict:
        """Roll on the class random talent table. Returns the full result dict."""
        talent_table = self._classes[self.character.class_name]["random_talents"]
        return roll_talent(talent_table)

    def talent_needs_stat_choice(self, talent_result: dict) -> bool:
        """True if the rolled talent is '+1 to a Stat' — requires a follow-up stat bump."""
        return talent_result["talent"].startswith("+1 to a Stat")

    def talent_needs_subtable_choice(self, talent_result: dict) -> bool:
        """True if the talent says 'Choose 1 of: ...' — requires picking from subtable."""
        return talent_result["talent"].startswith("Choose")

    def get_subtable_options(self) -> list[dict]:
        """Return the class subtable talents (for 'Choose 1 of: ...' results)."""
        subtable = self._classes.get(self.character.class_name, {}).get("subtable_talents", {})
        return [{"name": k, "description": v} for k, v in subtable.items()]

    def apply_talent_result(self, talent_result: dict, subtable_choice: str = None):
        """
        Record a rolled talent on the character.
        For 'Choose X' results, pass the chosen talent name as subtable_choice.
        For '+1 to a Stat' results, call apply_stat_bump() separately after.
        """
        talent_text = subtable_choice if subtable_choice else talent_result["talent"]
        self.character.random_talents.append(talent_text)

    # ── Step 5: Race ──────────────────────────────────────────────────────────

    def get_race_options(self) -> list[dict]:
        return [
            {
                "name": name,
                "speed": race["speed"],
                "size": race["size"],
                "languages": race["languages"],
                "description": race["description"],
                "talents": list(race["talents"].keys()),
                "talent_descriptions": race["talents"],
            }
            for name, race in self._races.items()
        ]

    def set_race(self, race_name: str):
        race = self._races[race_name]
        self.character.race = race_name
        self.character.speed = race["speed"]
        self.character.size = race["size"]
        for lang in race["languages"]:
            if lang not in self.character.languages:
                self.character.languages.append(lang)

    # ── Step 6: Racial talent ─────────────────────────────────────────────────

    def get_racial_talent_options(self) -> list[dict]:
        race = self._races[self.character.race]
        return [
            {"name": name, "description": desc}
            for name, desc in race["talents"].items()
        ]

    def set_racial_talent(self, talent_name: str):
        self.character.racial_talent = talent_name

    def has_ambitious(self) -> bool:
        """True if the racial talent is Ambitious — triggers an extra class talent roll."""
        return self.character.racial_talent == "Ambitious"

    # ── Step 7: Ambitious extra roll — reuse roll_class_talent / apply_talent_result

    # ── Step 8: Background ────────────────────────────────────────────────────

    def get_background_options(self) -> list[dict]:
        return [
            {
                "name": name,
                "roll": bg["roll"],
                "skills": bg.get("skills", []),
                "languages": bg.get("languages", []),
            }
            for name, bg in self._backgrounds.items()
        ]

    def set_background(self, background_name: str):
        self.character.background = background_name

    # ── Step 9: Background skill / language choice ────────────────────────────

    def get_background_choice_options(self) -> dict:
        """Return expanded skill and language options for the chosen background."""
        bg = self._backgrounds[self.character.background]
        raw_skills = bg.get("skills", [])
        raw_langs = bg.get("languages", [])

        all_skills = list(self._skills.keys())
        std = self._languages["standard"]
        rare = self._languages["rare"]
        known = set(self.character.languages)

        skills = all_skills if "Any" in raw_skills else raw_skills

        langs: list[str] = []
        for entry in raw_langs:
            if entry == "Any":
                langs = [l for l in std + rare if l not in known]
                break
            elif entry == "Standard":
                langs.extend(l for l in std if l not in known)
            elif entry == "Rare":
                langs.extend(l for l in rare if l not in known)
            else:
                if entry not in known:
                    langs.append(entry)

        return {"skills": skills, "languages": langs}

    def apply_background_skill(self, skill_name: str):
        self.character.trained_skill = skill_name

    def apply_background_language(self, language: str):
        if language not in self.character.languages:
            self.character.languages.append(language)

    # ── Step 10: Gear ─────────────────────────────────────────────────────────

    def get_gear_status(self) -> dict:
        """Return current slot usage, equipped items, and gold."""
        capacity = self.character.calculate_carrying_capacity()
        used = self.character.used_slots()
        return {
            "used": used,
            "capacity": capacity,
            "remaining": capacity - used,
            "gear": list(self.character.gear),
            "weapons": list(self.character.weapons),
            "worn_armor": self.character.worn_armor,
            "has_shield": self.character.has_shield,
            "gold": self.character.gold,
        }

    def apply_suggested_gear(self):
        """Reset gear to the class-suggested loadout, expanding Explorer's Kit."""
        self.character.gear = []
        self.character.weapons = []
        self.character.worn_armor = ""
        self.character.has_shield = False

        suggested = self._gear_data["suggested_gear"].get(self.character.class_name, [])
        for entry in suggested:
            for item in self._resolve_gear_entry(entry):
                self._place_gear_item(item)

    def _resolve_gear_entry(self, entry: str) -> list[dict]:
        """
        Resolve a suggested-gear string into one or more item dicts.
        Tries direct lookup first, then 'item xN' multiplier pattern.
        Handles Explorer's Kit by expanding to its individual contents.
        """
        entry = entry.strip()

        if entry.lower() == "explorer's kit":
            return self._expand_explorers_kit()

        # Direct lookup first (e.g. "longsword", "leather")
        item = self._lookup_gear(entry)
        if item:
            return [item]

        # 'item x2' multiplier (e.g. "javelin x2")
        m = re.match(r"^(.+?)\s+x(\d+)$", entry, re.IGNORECASE)
        if m:
            item_name, count = m.group(1), int(m.group(2))
            item = self._lookup_gear(item_name)
            return [item] * count if item else []

        return []

    def _expand_explorers_kit(self) -> list[dict]:
        """Return individual item dicts for each item in the Explorer's Kit.

        Tries direct lookup first so 'iron spike x5' and 'rations x3' match their
        gear.json keys as single slot-items, then falls back to xN multiplier for
        items like 'torch x2' that need splitting.
        """
        kit = self._gear_data["adventuring_gear"].get("Explorer's Kit", {})
        result = []
        for content in kit.get("contents", []):
            # Direct lookup first — handles "iron spike x5", "rations x3" as unit keys
            item = self._lookup_gear(content)
            if item:
                result.append(item)
                continue
            # Fallback: 'sub_item xN' multiplier (e.g. "torch x2")
            m = re.match(r"^(.+?)\s+x(\d+)$", content, re.IGNORECASE)
            if m:
                sub_name, count = m.group(1), int(m.group(2))
                item = self._lookup_gear(sub_name)
                if item:
                    result.extend([item] * count)
        return result

    def _lookup_gear(self, name: str) -> dict | None:
        """Find a gear item by name (case-insensitive) across all categories."""
        name_lower = name.lower().strip()

        for item_name, data in self._gear_data["armor"].items():
            if item_name.lower() == name_lower:
                return {
                    "name": item_name,
                    "slots": data["slots"],
                    "category": "armor",
                    "ac": data["ac"],
                    "max_dex": data.get("max_dex"),
                }

        for item_name, data in self._gear_data["weapons"].items():
            if item_name.lower() == name_lower:
                return {
                    "name": item_name,
                    "slots": data["slots"],
                    "category": "weapon",
                    "damage": data["damage"],
                    "range": data.get("range"),
                    "properties": data["properties"],
                }

        for item_name, data in self._gear_data["adventuring_gear"].items():
            if item_name.lower() == name_lower:
                return {"name": item_name, "slots": data["slots"], "category": "gear"}

        return None

    def _place_gear_item(self, item: dict):
        """Apply a gear item to the character, routing by category."""
        cat = item["category"]
        if cat == "armor":
            if item["name"] == "Shield":
                self.character.has_shield = True
            else:
                self.character.worn_armor = item["name"]
        elif cat == "weapon":
            self.character.gear.append(item)
            if item["name"] not in self.character.weapons:
                self.character.weapons.append(item["name"])
        else:
            self.character.gear.append(item)

    def add_gear_item(self, item_name: str) -> tuple[bool, str]:
        """Try to add a gear item. Returns (success, message)."""
        from validators import validate_armor_for_class, validate_weapon_for_class

        item = self._lookup_gear(item_name)
        if not item:
            return False, f"Unknown item: {item_name}"

        if item["slots"] > 0:
            cap = self.character.calculate_carrying_capacity()
            used = self.character.used_slots()
            if used + item["slots"] > cap:
                return False, f"Not enough slots ({cap - used} remaining, need {item['slots']})"

        if item["category"] == "armor" and item["name"] != "Shield":
            if not validate_armor_for_class(item["name"], self.character.class_name):
                return False, f"{self.character.class_name} cannot wear {item['name']}"

        if item["category"] == "weapon":
            if not validate_weapon_for_class(item["name"], self.character.class_name):
                return False, f"{self.character.class_name} cannot use {item['name']}"

        self._place_gear_item(item)
        return True, f"Added {item['name']}"

    def remove_gear_item(self, item_name: str) -> bool:
        """Remove a gear item (or unequip armor/shield) by name. Returns True if found."""
        name_lower = item_name.lower()

        for i, item in enumerate(self.character.gear):
            if item["name"].lower() == name_lower:
                removed = self.character.gear.pop(i)
                if removed["category"] == "weapon":
                    self.character.weapons = [
                        w for w in self.character.weapons if w.lower() != name_lower
                    ]
                return True

        if self.character.worn_armor.lower() == name_lower:
            self.character.worn_armor = ""
            return True

        if name_lower == "shield" and self.character.has_shield:
            self.character.has_shield = False
            return True

        return False

    def get_available_weapons(self) -> list[dict]:
        """Return all weapons usable by this class with full item data."""
        from validators import get_allowed_weapons
        allowed = {w.lower() for w in get_allowed_weapons(self.character.class_name)}
        return [
            {"name": name, **data}
            for name, data in self._gear_data["weapons"].items()
            if name.lower() in allowed
        ]

    def get_available_armor(self) -> list[dict]:
        """Return all armor wearable by this class with full item data."""
        from validators import get_allowed_armor
        allowed = {a.lower() for a in get_allowed_armor(self.character.class_name)}
        return [
            {"name": name, **data}
            for name, data in self._gear_data["armor"].items()
            if name.lower() in allowed
        ]

    def get_all_gear(self) -> dict:
        """Return all available gear items for browsing (not filtered by class)."""
        return {
            "weapons": list(self._gear_data["weapons"].keys()),
            "armor": list(self._gear_data["armor"].keys()),
            "gear": list(self._gear_data["adventuring_gear"].keys()),
        }

    # ── Step 11: Spells (casters only) ────────────────────────────────────────

    def is_caster(self) -> bool:
        if not self.character.class_name:
            return False
        return bool(self._classes[self.character.class_name].get("spellcasting"))

    def get_spells_needed(self) -> dict:
        """How many spells of each level are needed at level 1: {'SL1': 4, ...}."""
        from validators import get_spells_known_count
        return get_spells_known_count(self.character.class_name, self.character.level)

    def get_spell_options_by_level(self) -> dict:
        """Available (not yet chosen) spells per level for this class."""
        known = set(self.character.spells_known)
        cls_spells = self._spells_data["spells_by_class"].get(self.character.class_name, {})
        return {
            level: [s for s in spells if s not in known]
            for level, spells in cls_spells.items()
        }

    def get_spell_selection_status(self) -> dict:
        """Return {'SL1': {'selected': 2, 'needed': 4}, ...} for progress display."""
        needed = self.get_spells_needed()
        details = self._spells_data["spell_details"]
        counts = {level: 0 for level in needed}
        for spell in self.character.spells_known:
            sl = details.get(spell, {}).get("sl")
            if sl:
                key = f"SL{sl}"
                if key in counts:
                    counts[key] += 1
        return {
            level: {"selected": counts.get(level, 0), "needed": n}
            for level, n in needed.items()
        }

    def spells_complete(self) -> bool:
        """True if all required spell slots are filled."""
        for level_status in self.get_spell_selection_status().values():
            if level_status["selected"] < level_status["needed"]:
                return False
        return True

    def add_spell(self, spell_name: str) -> tuple[bool, str]:
        """Try to add a spell to known spells. Returns (success, message)."""
        details = self._spells_data["spell_details"]
        spell_info = details.get(spell_name)
        if not spell_info:
            return False, f"Unknown spell: {spell_name}"

        cls = self.character.class_name
        if cls not in spell_info.get("classes", []):
            return False, f"{spell_name} is not on the {cls} spell list"

        if spell_name in self.character.spells_known:
            return False, f"Already know {spell_name}"

        level_key = f"SL{spell_info['sl']}"
        needed = self.get_spells_needed()
        if level_key not in needed:
            return False, f"No SL{spell_info['sl']} slots available at this level"

        current = sum(
            1 for s in self.character.spells_known
            if details.get(s, {}).get("sl") == spell_info["sl"]
        )
        if current >= needed[level_key]:
            return False, f"SL{spell_info['sl']} slots full ({needed[level_key]}/{needed[level_key]})"

        self.character.spells_known.append(spell_name)
        return True, f"Added {spell_name}"

    def remove_spell(self, spell_name: str) -> bool:
        if spell_name in self.character.spells_known:
            self.character.spells_known.remove(spell_name)
            if self.character.studied_spell == spell_name:
                self.character.studied_spell = ""
            return True
        return False

    def set_studied_spell(self, spell_name: str) -> tuple[bool, str]:
        """Wizard only: designate the Studied Spell (cast with AD)."""
        if self.character.class_name != "Wizard":
            return False, "Only Wizards have a Studied Spell"
        if spell_name not in self.character.spells_known:
            return False, f"{spell_name} is not in your known spells"
        self.character.studied_spell = spell_name
        return True, f"{spell_name} is now your Studied Spell"

    def auto_add_turn_undead(self):
        """Priest only: add Turn Undead (free, doesn't count toward spell slots)."""
        if self.character.class_name == "Priest":
            if "Turn Undead" not in self.character.spells_known:
                self.character.spells_known.insert(0, "Turn Undead")

    def get_spell_detail(self, spell_name: str) -> dict | None:
        """Return full spell detail dict, or None if not found."""
        return self._spells_data["spell_details"].get(spell_name)

    # ── Step 12-14: Alignment, deity, extra languages ─────────────────────────

    def set_alignment(self, alignment: str):
        self.character.alignment = alignment

    def set_deity(self, deity: str):
        self.character.deity = deity

    def get_class_extra_language_options(self) -> list[dict] | None:
        """
        Return class-specific extra language choices as a list of option groups.
        Returns None if the class has no extra language benefit.
        Example Wizard return: [
            {'type': 'standard', 'count': 2, 'options': [...]},
            {'type': 'rare',     'count': 2, 'options': [...]},
        ]
        """
        extra = self._classes.get(self.character.class_name, {}).get("extra_languages")
        if not extra:
            return None

        known = set(self.character.languages)
        std = self._languages["standard"]
        rare = self._languages["rare"]

        groups = []
        if "standard" in extra:
            groups.append({
                "type": "standard",
                "count": extra["standard"],
                "options": [l for l in std if l not in known],
            })
        if "rare" in extra:
            groups.append({
                "type": "rare",
                "count": extra["rare"],
                "options": [l for l in rare if l not in known],
            })
        if "choice_of" in extra:
            groups.append({
                "type": "choice",
                "count": extra["count"],
                "options": [l for l in extra["choice_of"] if l not in known],
            })
        return groups if groups else None

    def add_language(self, language: str):
        if language not in self.character.languages:
            self.character.languages.append(language)

    # ── Finalize ──────────────────────────────────────────────────────────────

    def finalize(self) -> Character:
        """Roll HP, calculate derived stats, and return the completed Character."""
        cls = self._classes[self.character.class_name]
        self.character.hp = roll_hp(
            cls["hd_size"],
            self.character.get_stat("Con"),
            level=1,
            min_hp_level1=cls["min_hp_level1"],
        )
        self.character.max_hp = self.character.hp
        self.character.calculate_ac()
        return self.character
