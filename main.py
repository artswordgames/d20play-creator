"""Terminal UI for d20play RPG character creation."""
import os
import sys

from creator import CharacterCreator
from roller import format_modifier, STAT_NAMES, display_stat_array

# ── ANSI helpers ──────────────────────────────────────────────────────────────

RESET  = '\033[0m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
CYAN   = '\033[96m'
GREEN  = '\033[92m'
YELLOW = '\033[93m'
RED    = '\033[91m'


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def hr(char='─', width=56):
    print(f"  {char * width}")


def header(title: str, step_info: str = ""):
    clear()
    print()
    top = f"  {BOLD}{CYAN}d20play RPG{RESET}"
    if step_info:
        top += f"  {DIM}{step_info}{RESET}"
    print(top)
    hr()
    print(f"  {BOLD}{title}{RESET}")
    hr()
    print()


def error(msg: str):
    print(f"\n  {RED}✗  {msg}{RESET}")


def success(msg: str):
    print(f"  {GREEN}✓  {msg}{RESET}")


def info(msg: str):
    print(f"  {DIM}{msg}{RESET}")


def ask(prompt: str) -> str:
    """Single-line input prompt. Ctrl-C exits gracefully."""
    try:
        return input(f"  {prompt}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n  Goodbye!\n")
        sys.exit(0)


def choose(options: list, prompt: str = "Choice") -> int:
    """
    Validate numeric input against a pre-displayed numbered list.
    Returns 0-based index. Entering 'q' prompts to quit.
    """
    while True:
        raw = ask(prompt)
        if raw.lower() in ('q', 'quit'):
            if _confirm("Quit character creator?"):
                sys.exit(0)
            continue
        try:
            n = int(raw)
            if 1 <= n <= len(options):
                return n - 1
        except ValueError:
            pass
        error(f"Enter a number between 1 and {len(options)}")


def _confirm(prompt: str) -> bool:
    raw = ask(f"{prompt} [y/N]").lower()
    return raw in ('y', 'yes')


def pause(msg: str = ""):
    ask(f"{msg}[Enter to continue]" if msg else "[Enter to continue]")


# ── Main wizard ───────────────────────────────────────────────────────────────

def run_creation_wizard() -> None:
    c = CharacterCreator()
    n = [0]

    def step():
        n[0] += 1
        return n[0]

    step_identity(c, step())
    step_stats(c, step())
    step_class(c, step())
    step_class_step2b(c, step())
    step_race(c, step())
    step_racial_talent(c, step())

    if c.has_ambitious():
        header("Ambitious — Extra Class Talent", f"Step {step()}")
        print(f"  {BOLD}You have the Ambitious talent!{RESET}")
        info("Roll an extra class talent on the class table.\n")
        pause("Press Enter to roll")
        _roll_and_apply_talent(c)

    step_background(c, step())
    step_background_choice(c, step())
    step_gear(c, step())

    if c.is_caster():
        c.auto_add_turn_undead()
        step_spells(c, step())

    lang_groups = c.get_class_extra_language_options()
    if lang_groups:
        step_extra_languages(c, lang_groups, step())

    step_final_details(c, step())

    char = c.finalize()
    show_character_sheet(char)
    post_creation_menu(char)


# ── Steps ─────────────────────────────────────────────────────────────────────

def step_identity(c: CharacterCreator, n: int):
    header("Character Identity", f"Step {n}")
    name   = ask("Character name")
    player = ask("Played by")
    c.set_identity(name, player)


def step_stats(c: CharacterCreator, n: int):
    header("Ability Scores", f"Step {n}")
    print("  Choose a stat generation method:\n")
    print(f"  1. {BOLD}Roll in order{RESET}   Roll 6d20: Str → Dex → Con → Int → Wis → Cha")
    print(f"  2. {BOLD}Roll freely{RESET}     Roll 6d20, then assign modifiers to any stat")
    print(f"  3. {BOLD}Default array{RESET}   Use +2, +1, 0, 0, -1, -2 (assign any order)\n")
    choice = choose(["Roll in order", "Roll freely", "Default array"])

    if choice == 0:
        print()
        pause("Press Enter to roll")
        sets = c.roll_stat_sets()
        if len(sets) > 1:
            info(f"Rerolled {len(sets) - 1} time(s) — earlier set(s) had no +2.\n")
        for i, stat_set in enumerate(sets):
            valid = i == len(sets) - 1
            mark = f"{GREEN}✓{RESET}" if valid else f"{RED}✗{RESET}"
            print(f"  {mark}  Set {i + 1}: {display_stat_array(stat_set)}")
        print()
        if len(sets) == 1:
            chosen = 0
            info("Using your rolled set.")
        else:
            print(f"  (Only the last set is guaranteed to have a +2.)\n")
            chosen = choose([f"Set {i + 1}" for i in range(len(sets))], "Which set")
        c.apply_stats_in_order(sets[chosen])

    elif choice == 1:
        print()
        pause("Press Enter to roll")
        sets = c.roll_stat_sets()
        stat_set = sets[-1]
        rolls = [s["roll"] for s in stat_set]
        mods  = [s["modifier"] for s in stat_set]
        print()
        print("  Rolled: " + ", ".join(f"d20={r} ({format_modifier(m)})" for r, m in zip(rolls, mods)))
        print()
        assignment = _assign_freely(mods)
        c.apply_stats_assigned(stat_set, assignment)

    else:
        default = c.get_default_array()
        mods = [s["modifier"] for s in default]
        print(f"\n  Default array: {', '.join(format_modifier(m) for m in mods)}\n")
        assignment = _assign_freely(mods)
        c.apply_stats_assigned(default, assignment)

    print()
    success("Stats: " + "  ".join(
        f"{s}: {format_modifier(c.character.stats[s])}" for s in STAT_NAMES
    ))
    pause()


def _assign_freely(modifiers: list[int]) -> dict:
    """Interactively assign a list of modifiers to the 6 stats. Returns index dict."""
    remaining = list(range(len(modifiers)))
    assignment = {}
    for stat_name in STAT_NAMES:
        available = [(i, modifiers[i]) for i in remaining]
        print(f"  Assign to {BOLD}{stat_name}{RESET}:")
        for j, (_, m) in enumerate(available, 1):
            print(f"    {j}. {format_modifier(m)}")
        print()
        idx = choose(available, stat_name)
        chosen = available[idx][0]
        assignment[stat_name] = chosen
        remaining.remove(chosen)
        print()
    return assignment


def step_class(c: CharacterCreator, n: int):
    header("Choose a Class", f"Step {n}")
    options = c.get_class_options()
    for i, cls in enumerate(options, 1):
        caster = f"  {DIM}caster{RESET}" if cls["spellcasting"] else ""
        print(f"  {i}. {BOLD}{cls['name']:<10}{RESET} {cls['primary_stat']} / {cls['hd']}"
              f"  {DIM}—{RESET}  {cls['description']}{caster}")
    print()
    idx = choose(options, "Class")
    c.set_class(options[idx]["name"])
    print()
    info(f"Base talents: {', '.join(options[idx]['base_talents'].keys())}")
    pause()


def step_class_step2b(c: CharacterCreator, n: int):
    header(f"{c.character.class_name} — Step 2b", f"Step {n}")
    print("  Choose one:\n")
    print(f"  1. {BOLD}+1 to a Stat{RESET}  (max +4)")
    print(f"  2. {BOLD}Roll Class Talent{RESET}\n")
    choice = choose(["+1 stat", "Roll talent"])
    if choice == 0:
        _pick_stat_bump(c)
    else:
        _roll_and_apply_talent(c)


def _pick_stat_bump(c: CharacterCreator):
    print()
    opts = c.get_stat_bump_options()
    print("  Choose a stat to raise by +1:\n")
    for i, o in enumerate(opts, 1):
        print(f"  {i}. {BOLD}{o['name']}{RESET}  "
              f"{format_modifier(o['current'])} → {GREEN}{format_modifier(o['new'])}{RESET}")
    print()
    idx = choose(opts, "Stat")
    c.apply_stat_bump(opts[idx]["name"])
    success(f"{opts[idx]['name']} raised to {format_modifier(opts[idx]['new'])}")
    pause()


def _roll_and_apply_talent(c: CharacterCreator):
    print()
    pause("Press Enter to roll talent")
    result = c.roll_class_talent()
    print(f"\n  Rolled {BOLD}{result['roll']}{RESET}: {CYAN}{result['talent']}{RESET}\n")

    if c.talent_needs_stat_choice(result):
        c.apply_talent_result(result)
        opts = c.get_stat_bump_options()
        print("  Choose which stat to raise by +1:\n")
        for i, o in enumerate(opts, 1):
            print(f"  {i}. {BOLD}{o['name']}{RESET}  "
                  f"{format_modifier(o['current'])} → {GREEN}{format_modifier(o['new'])}{RESET}")
        print()
        idx = choose(opts, "Stat")
        c.apply_stat_bump(opts[idx]["name"])
        success(f"{opts[idx]['name']} raised to {format_modifier(opts[idx]['new'])}")

    elif c.talent_needs_subtable_choice(result):
        sub_opts = c.get_subtable_options()
        named = [o for o in sub_opts if o["name"] in result["talent"]] or sub_opts
        print("  Choose one talent:\n")
        for i, t in enumerate(named, 1):
            print(f"  {i}. {BOLD}{t['name']:<14}{RESET} {DIM}{t['description']}{RESET}")
        print()
        idx = choose(named, "Talent")
        c.apply_talent_result(result, subtable_choice=named[idx]["name"])
        success(f"Talent: {named[idx]['name']}")

    else:
        c.apply_talent_result(result)
        success(f"Talent: {result['talent']}")

    pause()


def step_race(c: CharacterCreator, n: int):
    header("Choose a Race", f"Step {n}")
    options = c.get_race_options()
    for i, race in enumerate(options, 1):
        langs    = ", ".join(race["languages"])
        talents  = " / ".join(race["talents"])
        print(f"  {i}. {BOLD}{race['name']:<12}{RESET}  "
              f"{race['speed']}'  {DIM}{langs}  |  {talents}{RESET}")
    print()
    idx = choose(options, "Race")
    c.set_race(options[idx]["name"])
    success(f"Race: {c.character.race}")
    pause()


def step_racial_talent(c: CharacterCreator, n: int):
    header(f"{c.character.race} — Racial Talent", f"Step {n}")
    options = c.get_racial_talent_options()
    print("  Choose your racial talent:\n")
    for i, t in enumerate(options, 1):
        print(f"  {i}. {BOLD}{t['name']:<14}{RESET} {t['description']}")
    print()
    idx = choose(options, "Talent")
    c.set_racial_talent(options[idx]["name"])
    success(f"Racial talent: {options[idx]['name']}")
    pause()


def step_background(c: CharacterCreator, n: int):
    header("Choose a Background", f"Step {n}")
    options = c.get_background_options()
    for i, bg in enumerate(options, 1):
        parts = []
        if bg["skills"]:
            parts.append("skills: " + "/".join(bg["skills"]))
        if bg["languages"]:
            parts.append("lang: " + "/".join(bg["languages"]))
        extra = f"  {DIM}[{', '.join(parts)}]{RESET}" if parts else ""
        print(f"  {i:>2}. {BOLD}{bg['name']:<14}{RESET}{extra}")
    print()
    idx = choose(options, "Background")
    c.set_background(options[idx]["name"])
    success(f"Background: {c.character.background}")
    pause()


def step_background_choice(c: CharacterCreator, n: int):
    header(f"{c.character.background} — Skill or Language", f"Step {n}")
    choices = c.get_background_choice_options()
    skills = choices["skills"]
    langs  = choices["languages"]

    if not skills and not langs:
        info("No choices for this background.")
        pause()
        return

    all_opts: list[tuple[str, str]] = []
    print("  Choose one — gain AD on skill checks, or know a language:\n")

    if skills:
        info("— Skills —")
        for sk in skills:
            all_opts.append(("skill", sk))
            print(f"  {len(all_opts):>2}. {sk}")
        print()

    if langs:
        info("— Languages —")
        for lg in langs:
            all_opts.append(("lang", lg))
            print(f"  {len(all_opts):>2}. {lg}")
        print()

    idx = choose(all_opts, "Choice")
    typ, val = all_opts[idx]
    if typ == "skill":
        c.apply_background_skill(val)
        success(f"Trained skill: {val}")
    else:
        c.apply_background_language(val)
        success(f"Language added: {val}")
    pause()


def step_gear(c: CharacterCreator, n: int):
    header("Equipment", f"Step {n}")
    c.apply_suggested_gear()
    _show_gear(c)
    print()
    print(f"  1. {BOLD}Keep this gear{RESET}")
    print(f"  2. {BOLD}Customize{RESET}\n")
    if choose(["Keep", "Customize"]) == 1:
        _customize_gear(c)
    status = c.get_gear_status()
    success(f"Gear locked in: {status['used']}/{status['capacity']} slots used")
    pause()


def _show_gear(c: CharacterCreator):
    status = c.get_gear_status()
    used, cap = status["used"], status["capacity"]
    filled = int((used / cap) * 24) if cap else 0
    bar = f"{'█' * filled}{'░' * (24 - filled)}"
    print(f"  Slots: {BOLD}{used}/{cap}{RESET}  [{bar}]  {cap - used} remaining\n")
    if status["worn_armor"]:
        print(f"    {DIM}[worn]{RESET}  {status['worn_armor']}")
    if status["has_shield"]:
        print(f"    {DIM}[worn]{RESET}  Shield")
    for item in status["gear"]:
        slot_str = f"{item['slots']} slot{'s' if item['slots'] != 1 else ''}"
        print(f"    {DIM}[{slot_str:>6}]{RESET}  {item['name']}")
    print(f"\n  Gold: {status['gold']}gp")


def _customize_gear(c: CharacterCreator):
    while True:
        header("Equipment — Customize")
        _show_gear(c)
        print()
        print(f"  1. {BOLD}Add item{RESET}")
        print(f"  2. {BOLD}Remove item{RESET}")
        print(f"  3. {BOLD}Done{RESET}\n")
        choice = choose(["Add", "Remove", "Done"])
        if choice == 2:
            break
        elif choice == 0:
            _add_gear_item(c)
        else:
            _remove_gear_item(c)


def _add_gear_item(c: CharacterCreator):
    print()
    weapons = c.get_available_weapons()
    armor   = c.get_available_armor()
    all_g   = c.get_all_gear()
    if weapons:
        print(f"  {BOLD}Weapons:{RESET}  " + ", ".join(w["name"] for w in weapons))
    if armor:
        print(f"  {BOLD}Armor:{RESET}    " + ", ".join(a["name"] for a in armor))
    print(f"  {BOLD}Gear:{RESET}     " + ", ".join(all_g["gear"]))
    print()
    name = ask("Item name (blank to cancel)")
    if not name:
        return
    ok, msg = c.add_gear_item(name)
    if ok:
        success(msg)
    else:
        error(msg)
    pause()


def _remove_gear_item(c: CharacterCreator):
    print()
    status = c.get_gear_status()
    items = [item["name"] for item in status["gear"]]
    if status["worn_armor"]:
        items.append(status["worn_armor"])
    if status["has_shield"]:
        items.append("Shield")
    if not items:
        info("No items to remove.")
        pause()
        return
    for i, name in enumerate(items, 1):
        print(f"  {i}. {name}")
    print()
    idx = choose(items, "Remove which item")
    if c.remove_gear_item(items[idx]):
        success(f"Removed {items[idx]}")
    else:
        error(f"Could not remove {items[idx]}")
    pause()


def step_spells(c: CharacterCreator, n: int):
    header("Spell Selection", f"Step {n}")
    cls = c.character.class_name

    if cls == "Priest":
        info("Turn Undead added automatically (free — doesn't count toward spell slots).\n")

    needed = c.get_spells_needed()
    print(f"  Starting spells for {BOLD}{cls}{RESET}:\n")
    for level_key, count in needed.items():
        print(f"    {level_key.replace('SL', 'Spell Level ')}: choose {count}")
    print()
    pause()

    details = c._spells_data["spell_details"]

    while not c.spells_complete():
        header("Spell Selection", f"Step {n}")

        # Status bar
        status = c.get_spell_selection_status()
        for level_key, s in status.items():
            bar = f"[{'●' * s['selected']}{'○' * (s['needed'] - s['selected'])}]"
            complete = f"  {GREEN}✓{RESET}" if s["selected"] >= s["needed"] else ""
            print(f"  {level_key}: {bar} {s['selected']}/{s['needed']}{complete}")
        print()

        # Find first incomplete level
        target_level = next(
            (lk for lk, s in status.items() if s["selected"] < s["needed"]),
            None
        )
        if not target_level:
            break

        sl_num = int(target_level.replace("SL", ""))
        spells = c.get_spell_options_by_level().get(target_level, [])

        print(f"  {BOLD}SL{sl_num} spells available:{RESET}\n")
        for i, spell in enumerate(spells, 1):
            detail = details.get(spell, {})
            effect = detail.get("effect", "")
            preview = effect[:55] + ("…" if len(effect) > 55 else "")
            focus = f"  {DIM}[Focus]{RESET}" if "Focus" in detail.get("duration", "") else ""
            print(f"  {i:>2}. {BOLD}{spell:<22}{RESET} {DIM}{preview}{RESET}{focus}")
        print()

        idx = choose(spells, f"Add SL{sl_num} spell")
        ok, msg = c.add_spell(spells[idx])
        if ok:
            success(msg)
        else:
            error(msg)
        print()
        pause("(press Enter to continue) ")

    if cls == "Wizard":
        header("Wizard — Studied Spell", f"Step {n}")
        print(f"  {BOLD}Studied Spell:{RESET} You cast this spell with Advantage Dice.\n")
        info("Change your Studied Spell during any rest (with your spellbook).\n")
        known = [s for s in c.character.spells_known]
        for i, spell in enumerate(known, 1):
            print(f"  {i}. {spell}")
        print()
        idx = choose(known, "Studied Spell")
        ok, msg = c.set_studied_spell(known[idx])
        if ok:
            success(msg)
        pause()


def step_extra_languages(c: CharacterCreator, groups: list, n: int):
    header(f"{c.character.class_name} — Extra Languages", f"Step {n}")
    for group in groups:
        type_label = group["type"].capitalize()
        count      = group["count"]

        print(f"  {BOLD}{c.character.class_name}s know {count} extra {type_label} language(s).{RESET}\n")
        for _ in range(count):
            available = [l for l in group["options"] if l not in c.character.languages]
            if not available:
                info("No more languages available.")
                break
            info(f"Currently know: {', '.join(c.character.languages)}\n")
            for i, lang in enumerate(available, 1):
                print(f"  {i}. {lang}")
            print()
            idx = choose(available, "Language")
            c.add_language(available[idx])
            success(f"Added {available[idx]}")
            print()
    pause()


def step_final_details(c: CharacterCreator, n: int):
    header("Final Details", f"Step {n}")

    print("  Choose your alignment:\n")
    aligns = ["Lawful", "Neutral", "Chaotic"]
    for i, al in enumerate(aligns, 1):
        print(f"  {i}. {al}")
    print()
    c.set_alignment(aligns[choose(aligns, "Alignment")])
    print()

    if c.character.class_name == "Priest":
        print(f"  {BOLD}Priests must serve a deity whose alignment matches their own.{RESET}\n")
        c.set_deity(ask("Deity name"))
    else:
        deity = ask("Deity (optional — press Enter to skip)")
        if deity:
            c.set_deity(deity)
    print()

    print(f"  {BOLD}Languages known:{RESET} {', '.join(c.character.languages)}")
    pause()


# ── Character sheet ───────────────────────────────────────────────────────────

def show_character_sheet(char):
    clear()
    print()
    w = 58
    print(f"  {'═' * w}")
    name_line = f"  {char.name or '[Unnamed]'}"
    print(f"  {BOLD}{CYAN}{name_line}{RESET}")
    print(f"  {DIM}  Played by: {char.player_name or '[Unknown]'}{RESET}")
    print(f"  {'═' * w}")
    print()

    print(f"  {BOLD}Class:{RESET} {char.class_name}   "
          f"{BOLD}Level:{RESET} {char.level}   {BOLD}XP:{RESET} {char.xp}")
    print(f"  {BOLD}Race:{RESET}  {char.race}   "
          f"{BOLD}AL:{RESET} {char.alignment or '—'}   "
          f"{BOLD}Deity:{RESET} {char.deity or '—'}")
    print(f"  {BOLD}Back:{RESET}  {char.background}  {DIM}({char.trained_skill}){RESET}")
    hr('─', w)

    stat_parts = [f"{BOLD}{s}{RESET}: {format_modifier(char.stats[s])}" for s in STAT_NAMES]
    print("  " + "  ".join(stat_parts))
    hr('─', w)

    print(f"  {BOLD}AC:{RESET} {char.ac}   "
          f"{BOLD}HP:{RESET} {char.hp}/{char.max_hp}   "
          f"{BOLD}Speed:{RESET} {char.speed}'")
    print()

    print(f"  {BOLD}Talents{RESET}")
    for t in char.base_talents:
        print(f"    • {t}")
    if char.racial_talent:
        print(f"    • {char.racial_talent}  {DIM}(racial){RESET}")
    for t in char.random_talents:
        print(f"    • {t}  {DIM}(rolled){RESET}")
    print()

    print(f"  {BOLD}Languages:{RESET} {', '.join(char.languages)}")
    print()

    cap  = char.calculate_carrying_capacity()
    used = char.used_slots()
    print(f"  {BOLD}Gear{RESET}  {DIM}(used {used} of {cap} slots)   "
          f"Gold: {char.gold}gp{RESET}")
    if char.worn_armor:
        print(f"    {DIM}[worn]{RESET}  {char.worn_armor}")
    if char.has_shield:
        print(f"    {DIM}[worn]{RESET}  Shield")
    for item in char.gear:
        print(f"    • {item['name']}")

    if char.spells_known:
        print()
        print(f"  {BOLD}Spells Known{RESET}")
        for spell in char.spells_known:
            star = f"  {YELLOW}★ Studied{RESET}" if spell == char.studied_spell else ""
            print(f"    • {spell}{star}")

    print()
    print(f"  {'═' * w}")
    print(f"  {DIM}  d20play RPG v0.2.8.2{RESET}")
    print(f"  {'═' * w}")
    print()


# ── Post-creation ─────────────────────────────────────────────────────────────

def post_creation_menu(char):
    print(f"  {BOLD}Character creation complete!{RESET}\n")
    print("  1. Export as text")
    print("  2. Export as JSON")
    print("  3. Export as PDF")
    print("  4. Create another character")
    print("  5. Quit\n")

    while True:
        choice = choose(["Export text", "Export JSON", "Export PDF", "New character", "Quit"])
        if choice == 0:
            _export_text(char)
        elif choice == 1:
            _export_json(char)
        elif choice == 2:
            _export_pdf(char)
        elif choice == 3:
            run_creation_wizard()
            return
        else:
            print()
            sys.exit(0)


def _export_text(char):
    from pathlib import Path
    path = Path("output") / f"{char.name or 'character'}.txt"
    path.parent.mkdir(exist_ok=True)
    path.write_text(char.to_text())
    success(f"Saved → {path}")
    pause()


def _export_json(char):
    import json as _json
    from pathlib import Path
    path = Path("output") / f"{char.name or 'character'}.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(_json.dumps(char.to_dict(), indent=2))
    success(f"Saved → {path}")
    pause()


def _export_pdf(char):
    try:
        from exporter import export_pdf
        from pathlib import Path
        path = Path("output") / f"{char.name or 'character'}.pdf"
        path.parent.mkdir(exist_ok=True)
        export_pdf(char, str(path))
        success(f"Saved → {path}")
    except (ImportError, Exception) as e:
        error(f"PDF export failed: {e}")
    pause()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    try:
        while True:
            clear()
            print()
            print(f"  {BOLD}{CYAN}d20play RPG{RESET}  {BOLD}Character Creator{RESET}  {DIM}v0.2.8.2{RESET}")
            hr()
            print()
            print("  1. Create new character")
            print("  2. Quit\n")
            choice = choose(["Create", "Quit"])
            if choice == 0:
                run_creation_wizard()
            else:
                print()
                sys.exit(0)
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Goodbye!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
