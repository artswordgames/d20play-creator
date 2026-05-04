"""Character data model for d20play RPG."""
from dataclasses import dataclass, field


@dataclass
class Character:
    """Holds all data for a d20play RPG character."""
    
    # Identity
    name: str = ""
    player_name: str = ""
    level: int = 1
    xp: int = 0
    alignment: str = ""
    deity: str = ""
    
    # Stats
    stats: dict = field(default_factory=lambda: {
        "Str": 0, "Dex": 0, "Con": 0, "Int": 0, "Wis": 0, "Cha": 0
    })
    
    # Class
    class_name: str = ""
    primary_stat: str = ""
    hd: str = ""
    hd_size: int = 0
    hp: int = 0
    max_hp: int = 0
    
    # Race
    race: str = ""
    speed: int = 30
    size: str = "Medium"
    
    # Background
    background: str = ""
    trained_skill: str = ""
    
    # Talents
    base_talents: list = field(default_factory=list)
    racial_talent: str = ""
    random_talents: list = field(default_factory=list)
    
    # Languages
    languages: list = field(default_factory=lambda: ["Common"])
    
    # Gear
    gear: list = field(default_factory=list)
    gold: int = 100
    
    # Armor
    worn_armor: str = ""
    has_shield: bool = False
    
    # Weapons
    weapons: list = field(default_factory=list)
    
    # Spells
    spells_known: list = field(default_factory=list)
    studied_spell: str = ""
    
    # Derived stats
    ac: int = 10
    
    # Tracking
    notes: list = field(default_factory=list)
    
    def get_stat(self, stat_name: str) -> int:
        return self.stats.get(stat_name, 0)
    
    def set_stat(self, stat_name: str, value: int):
        self.stats[stat_name] = min(value, 4)  # Max stat is +4
    
    def calculate_ac(self):
        """Calculate AC from armor, shield, and Dex."""
        base_ac = 10
        dex = self.get_stat("Dex")
        
        # Armor AC values
        armor_ac = {
            "Leather": 11, "Chain": 14, "Plate": 16, "Mithril Chain": 14
        }
        armor_max_dex = {
            "Leather": None, "Chain": 0, "Plate": 0, "Mithril Chain": 2
        }
        
        if self.worn_armor and self.worn_armor in armor_ac:
            base_ac = armor_ac[self.worn_armor]
            max_dex = armor_max_dex[self.worn_armor]
            
            if max_dex is not None:
                dex_bonus = min(max(dex, 0), max_dex)
            else:
                dex_bonus = max(dex, 0)  # Negative Dex doesn't lower AC
            
            base_ac += dex_bonus
        else:
            # No armor — add Dex (but negative doesn't lower)
            base_ac += max(dex, 0)
        
        if self.has_shield:
            base_ac += 2
        
        self.ac = base_ac
    
    def calculate_carrying_capacity(self) -> int:
        """Calculate total carrying slots."""
        base = 10
        str_mod = self.get_stat("Str")
        if str_mod > 0:
            base += str_mod * 2
        
        # Hauler talent (Fighter) adds Con if positive
        if "Hauler" in [t for t in self.base_talents]:
            con_mod = self.get_stat("Con")
            if con_mod > 0:
                base += con_mod
        
        # Porter talent (Ranger) uses different formula
        if "Porter" in [t for t in self.base_talents]:
            str_mod = self.get_stat("Str")
            con_mod = self.get_stat("Con")
            higher = max(str_mod, con_mod)
            if higher > 0:
                base = 10 + (higher * 2)
        
        return base
    
    def used_slots(self) -> int:
        """Count gear slots in use."""
        total = 0
        for item in self.gear:
            total += item.get("slots", 1)
        return total
    
    def get_attack_bonus(self, weapon_name: str) -> int:
        """Calculate attack bonus for a weapon."""
        from roller import format_modifier
        import json
        from pathlib import Path
        
        with open(Path(__file__).parent / "data" / "gear.json") as f:
            gear_data = json.load(f)
        
        weapon = gear_data["weapons"].get(weapon_name, {})
        properties = weapon.get("properties", [])
        
        # Determine stat to use
        if "F" in properties:
            # Finesse — use higher of Str or Dex
            stat_mod = max(self.get_stat("Str"), self.get_stat("Dex"))
        elif weapon.get("range") and "T" not in properties:
            # Ranged (not thrown) — use Dex
            stat_mod = self.get_stat("Dex")
        else:
            # Melee or thrown — use Str
            stat_mod = self.get_stat("Str")
        
        bonus = stat_mod
        
        # Weapons Master bonus (Fighter)
        # Count +1 atk/dmg talents
        for talent in self.random_talents:
            if "+1 atk and dmg" in talent:
                bonus += 1
        if "Weapons Master" in self.base_talents:
            bonus += 1  # Base +1 at level 1
        
        return bonus
    
    def to_dict(self) -> dict:
        """Convert character to dictionary for JSON export."""
        return {
            "name": self.name,
            "player_name": self.player_name,
            "level": self.level,
            "xp": self.xp,
            "class": self.class_name,
            "race": self.race,
            "background": self.background,
            "alignment": self.alignment,
            "deity": self.deity,
            "stats": self.stats,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "ac": self.ac,
            "speed": self.speed,
            "languages": self.languages,
            "base_talents": self.base_talents,
            "racial_talent": self.racial_talent,
            "random_talents": self.random_talents,
            "trained_skill": self.trained_skill,
            "gear": self.gear,
            "weapons": self.weapons,
            "worn_armor": self.worn_armor,
            "has_shield": self.has_shield,
            "gold": self.gold,
            "spells_known": self.spells_known,
            "studied_spell": self.studied_spell,
            "carrying_capacity": self.calculate_carrying_capacity(),
            "used_slots": self.used_slots(),
            "notes": self.notes
        }
    
    def to_text(self) -> str:
        """Generate plain text character sheet."""
        from roller import format_modifier
        
        lines = []
        lines.append(f"{'='*60}")
        lines.append(f"  {self.name or '[Unnamed]'}")
        lines.append(f"  Played By: {self.player_name or '[Unknown]'}")
        lines.append(f"{'='*60}")
        lines.append(f"  Class: {self.class_name}  Level: {self.level}  XP: {self.xp}")
        lines.append(f"  Race: {self.race}  AL: {self.alignment}  Deity: {self.deity}")
        lines.append(f"  Background: {self.background} ({self.trained_skill})")
        lines.append(f"{'─'*60}")
        
        # Stats
        stat_line = "  "
        for name in ["Str", "Dex", "Con", "Int", "Wis", "Cha"]:
            stat_line += f"{name}: {format_modifier(self.stats[name])}  "
        lines.append(stat_line.rstrip())
        lines.append(f"{'─'*60}")
        
        # Combat
        lines.append(f"  AC: {self.ac}  HP: {self.hp}/{self.max_hp}  Speed: {self.speed}'")
        lines.append(f"{'─'*60}")
        
        # Talents
        lines.append(f"  TALENTS")
        for t in self.base_talents:
            lines.append(f"    • {t}")
        if self.racial_talent:
            lines.append(f"    • {self.racial_talent} (racial)")
        for t in self.random_talents:
            lines.append(f"    • {t} (rolled)")
        lines.append(f"{'─'*60}")
        
        # Languages
        lines.append(f"  LANGUAGES: {', '.join(self.languages)}")
        lines.append(f"{'─'*60}")
        
        # Gear
        cap = self.calculate_carrying_capacity()
        used = self.used_slots()
        lines.append(f"  GEAR ({used} of {cap} slots)  Gold: {self.gold}gp")
        for item in self.gear:
            slots = item.get("slots", 1)
            lines.append(f"    • {item['name']} ({slots} slot{'s' if slots != 1 else ''})")
        lines.append(f"{'─'*60}")
        
        # Spells
        if self.spells_known:
            lines.append(f"  SPELLS KNOWN")
            for spell in self.spells_known:
                studied = " ★" if spell == self.studied_spell else ""
                lines.append(f"    • {spell}{studied}")
            if self.studied_spell:
                lines.append(f"  ★ = Studied Spell (cast with AD)")
        
        lines.append(f"{'='*60}")
        lines.append(f"  d20play RPG v0.2.8.1")
        lines.append(f"{'='*60}")
        
        return "\n".join(lines)
