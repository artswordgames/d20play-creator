"""Output functions for d20play RPG character sheets."""
import json
from pathlib import Path


def export_text(char, filepath: str):
    """Write plain-text character sheet."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text(char.to_text())


def export_json(char, filepath: str):
    """Write character as JSON."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    Path(filepath).write_text(json.dumps(char.to_dict(), indent=2))


def export_pdf(char, filepath: str):
    """Write PDF matching Tom's d20play character sheet layout."""
    from fpdf import FPDF
    from roller import format_modifier

    pdf = FPDF(orientation="P", unit="mm", format="Letter")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()

    # ── Layout constants ──────────────────────────────────────────────────────
    M      = 10          # page margin
    PW     = 216         # letter width mm
    PH     = 279         # letter height mm
    CW     = PW - 2 * M  # 196mm content width

    # Column x-origins and widths  (left | mid | right)
    LX, LW = M,       64
    MX, MW = M + LW,  82
    RX, RW = M + LW + MW, CW - LW - MW   # ~50mm

    # Top section y-range
    TOP_Y  = M
    TOP_H  = 180

    # Notes section
    NOTE_Y = TOP_Y + TOP_H + 4
    NOTE_H = PH - NOTE_Y - M
    NW     = CW // 3   # each notes column width

    # ── Font helpers ──────────────────────────────────────────────────────────
    def font(bold=False, size=9):
        pdf.set_font("Helvetica", "B" if bold else "", size)

    def label(x, y, text, size=9):
        font(bold=True, size=size)
        pdf.set_xy(x, y)
        pdf.cell(0, 4, text)

    def value(x, y, text, w=0, size=9):
        font(bold=False, size=size)
        pdf.set_xy(x, y)
        pdf.cell(w, 4, str(text))

    def field(x, y, lbl, val, lbl_w=18, val_w=40, size=9):
        """Print 'LABEL: value' pair."""
        font(bold=True, size=size)
        pdf.set_xy(x, y)
        pdf.cell(lbl_w, 4, f"{lbl}:")
        font(bold=False, size=size)
        pdf.cell(val_w, 4, str(val))

    def hline(x, y, w, lw=0.3):
        pdf.set_line_width(lw)
        pdf.line(x, y, x + w, y)

    def box(x, y, w, h, lw=0.4):
        pdf.set_line_width(lw)
        pdf.rect(x, y, w, h)

    def vline(x, y, h, lw=0.3):
        pdf.set_line_width(lw)
        pdf.line(x, y, x, y + h)

    def wrapped(x, y, w, text, line_h=4, size=8):
        font(bold=False, size=size)
        pdf.set_xy(x, y)
        pdf.multi_cell(w, line_h, str(text))

    # ── Draw outer border ─────────────────────────────────────────────────────
    box(M, TOP_Y, CW, TOP_H, lw=0.5)

    # ── Column separators ─────────────────────────────────────────────────────
    vline(MX, TOP_Y, TOP_H)
    vline(RX, TOP_Y, TOP_H)

    # ── LEFT COLUMN ───────────────────────────────────────────────────────────
    pad = 2   # inner horizontal padding

    # NAME / Played By row
    y = TOP_Y + 1
    label(LX + pad, y, "NAME:", size=9)
    value(LX + pad + 14, y, char.name or "", size=9)
    y += 6
    label(LX + pad, y, "Played By:", size=8)
    value(LX + pad + 18, y, char.player_name or "", size=8)
    y += 6
    hline(LX, y, LW)

    # Stats 3×2 grid
    y += 2
    stats_to_show = [("Str", "Int"), ("Dex", "Wis"), ("Con", "Cha")]
    for left_stat, right_stat in stats_to_show:
        lv = format_modifier(char.stats[left_stat])
        rv = format_modifier(char.stats[right_stat])
        font(bold=True, size=9)
        pdf.set_xy(LX + pad, y)
        pdf.cell(14, 4, f"{left_stat}:")
        font(bold=False, size=9)
        pdf.cell(16, 4, lv)
        font(bold=True, size=9)
        pdf.cell(12, 4, f"{right_stat}:")
        font(bold=False, size=9)
        pdf.cell(0, 4, rv)
        y += 5
    y += 1
    hline(LX, y, LW)

    # AC / hp / Speed
    y += 2
    label(LX + pad, y, "AC:", size=9)
    value(LX + pad + 8, y, char.ac, size=9)
    y += 5
    label(LX + pad, y, "hp:", size=9)
    value(LX + pad + 8, y, f"{char.hp}/{char.max_hp}", size=9)
    y += 5
    label(LX + pad, y, "Speed:", size=9)
    value(LX + pad + 12, y, f"{char.speed}'", size=9)
    y += 6
    hline(LX, y, LW)

    # Attacks
    y += 2
    label(LX + pad, y, "Attacks", size=9)
    y += 5
    attacks = _build_attack_lines(char)
    for atk in attacks:
        value(LX + pad, y, atk, size=8)
        y += 4

    # ── MIDDLE COLUMN ─────────────────────────────────────────────────────────
    y = TOP_Y + 1

    # Class / Lvl / XP
    font(bold=True, size=9)
    pdf.set_xy(MX + pad, y)
    pdf.cell(12, 4, "Class:")
    font(bold=False, size=9)
    pdf.cell(24, 4, char.class_name)
    font(bold=True, size=9)
    pdf.cell(8, 4, "Lvl:")
    font(bold=False, size=9)
    pdf.cell(8, 4, str(char.level))
    font(bold=True, size=9)
    pdf.cell(8, 4, "XP:")
    font(bold=False, size=9)
    pdf.cell(0, 4, str(char.xp))
    y += 6
    hline(MX, y, MW)

    # Race / AL / Deity
    y += 2
    font(bold=True, size=9)
    pdf.set_xy(MX + pad, y)
    pdf.cell(12, 4, "Race:")
    font(bold=False, size=9)
    pdf.cell(22, 4, char.race)
    font(bold=True, size=9)
    pdf.cell(8, 4, "AL:")
    font(bold=False, size=9)
    pdf.cell(10, 4, char.alignment or "")
    y += 5
    font(bold=True, size=9)
    pdf.set_xy(MX + pad, y)
    pdf.cell(12, 4, "Deity:")
    font(bold=False, size=9)
    pdf.cell(0, 4, char.deity or "")
    y += 5
    hline(MX, y, MW)

    # Background
    y += 2
    font(bold=True, size=9)
    pdf.set_xy(MX + pad, y)
    pdf.cell(12, 4, "Back:")
    font(bold=False, size=9)
    bg_str = char.background
    if char.trained_skill:
        bg_str += f"  ({char.trained_skill})"
    pdf.cell(0, 4, bg_str)
    y += 6
    hline(MX, y, MW)

    # Languages
    y += 2
    label(MX + pad, y, "Languages", size=9)
    y += 5
    lang_str = ", ".join(char.languages)
    wrapped(MX + pad, y, MW - pad * 2, lang_str, line_h=4, size=8)
    y += 9
    hline(MX, y, MW)

    # Gear section
    y += 2
    cap  = char.calculate_carrying_capacity()
    used = char.used_slots()
    label(MX + pad, y, f"Gear  (used {used} of {cap} slots)", size=9)
    y += 5

    # Free items line
    font(bold=False, size=8)
    pdf.set_xy(MX + pad, y)
    pdf.cell(0, 4, "clothes, packs")
    y += 4
    hline(MX + pad, y, MW - pad * 2, lw=0.2)
    y += 2

    # Gear items
    dot_x = MX + pad
    x_x   = MX + MW - 7
    for item in char.gear:
        if y > TOP_Y + TOP_H - 5:
            break
        font(bold=False, size=8)
        pdf.set_xy(dot_x, y)
        pdf.cell(MW - pad * 2 - 6, 3.5, f"· {item['name']}")
        pdf.set_xy(x_x, y)
        pdf.cell(5, 3.5, "· x", align="R")
        y += 3.5

    if char.worn_armor:
        if y < TOP_Y + TOP_H - 5:
            font(bold=False, size=8)
            pdf.set_xy(dot_x, y)
            pdf.cell(MW - pad * 2 - 6, 3.5, f"· {char.worn_armor}")
            pdf.set_xy(x_x, y)
            pdf.cell(5, 3.5, "· x", align="R")
            y += 3.5

    if char.has_shield:
        if y < TOP_Y + TOP_H - 5:
            font(bold=False, size=8)
            pdf.set_xy(dot_x, y)
            pdf.cell(MW - pad * 2 - 6, 3.5, "· Shield")
            pdf.set_xy(x_x, y)
            pdf.cell(5, 3.5, "· x", align="R")
            y += 3.5

    # Spells section (if caster) — below gear line
    if char.spells_known:
        if y < TOP_Y + TOP_H - 8:
            hline(MX, y + 1, MW, lw=0.2)
            y += 4
            label(MX + pad, y, "Spells Known", size=8)
            y += 4
            for spell in char.spells_known:
                if y >= TOP_Y + TOP_H - 4:
                    break
                star = " [S]" if spell == char.studied_spell else ""
                font(bold=False, size=7)
                pdf.set_xy(MX + pad, y)
                pdf.cell(0, 3.5, f"· {spell}{star}")
                y += 3.5
            if char.studied_spell:
                font(bold=False, size=6.5)
                pdf.set_xy(MX + pad, y + 0.5)
                pdf.cell(0, 3, "[S] = Studied Spell (cast with AD)")

    # d20play logo text (bottom of mid column)
    font(bold=True, size=8)
    pdf.set_xy(MX + MW // 2 - 8, TOP_Y + TOP_H - 7)
    pdf.cell(16, 4, "d20play", align="C")
    font(bold=False, size=6)
    pdf.set_xy(MX + MW // 2 - 8, TOP_Y + TOP_H - 4)
    pdf.cell(16, 3, "play", align="C")

    # ── RIGHT COLUMN ──────────────────────────────────────────────────────────
    y = TOP_Y + 1
    label(RX + pad, y, "Talents", size=9)
    y += 6

    talent_lines = list(char.base_talents)
    if char.racial_talent:
        talent_lines.append(f"{char.racial_talent} (racial)")
    for t in char.random_talents:
        talent_lines.append(f"{t} (rolled)")

    for talent in talent_lines:
        if y >= TOP_Y + TOP_H - 4:
            break
        font(bold=False, size=7.5)
        pdf.set_xy(RX + pad, y)
        # Wrap long talent lines
        if len(talent) > 30:
            pdf.multi_cell(RW - pad * 2, 3.5, talent)
            y += 7
        else:
            pdf.cell(RW - pad * 2, 4, talent)
            y += 4

    # ── NOTES SECTION ─────────────────────────────────────────────────────────
    box(M, NOTE_Y, CW, NOTE_H, lw=0.5)
    vline(M + NW,     NOTE_Y, NOTE_H)
    vline(M + NW * 2, NOTE_Y, NOTE_H)

    for i in range(3):
        nx = M + i * NW
        label(nx + pad, NOTE_Y + 2, "Notes", size=9)
        if i == 1:
            # d20play logo in center notes header
            font(bold=True, size=7)
            pdf.set_xy(nx + NW - 18, NOTE_Y + 1)
            pdf.cell(16, 3, "d20play", align="C")

    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(filepath)


def _build_attack_lines(char) -> list[str]:
    """Build attack description lines for the attacks section."""
    from roller import format_modifier
    lines = []

    if not char.weapons:
        return lines

    try:
        import json as _json
        from pathlib import Path as _Path
        with open(_Path(__file__).parent / "data" / "gear.json") as f:
            gear_data = _json.load(f)
    except Exception:
        return [w for w in char.weapons[:4]]

    weapons_data = gear_data.get("weapons", {})

    for weapon_name in char.weapons[:4]:   # max 4 attacks on sheet
        data = weapons_data.get(weapon_name, {})
        dmg  = data.get("damage", "?")
        props = data.get("properties", [])
        rng  = data.get("range")

        # Determine attack bonus
        bonus = char.get_attack_bonus(weapon_name)
        bonus_str = format_modifier(bonus) if bonus != 0 else "+0"

        prop_str = ""
        if props:
            prop_str = " [" + ", ".join(props) + "]"

        if rng:
            line = f"{weapon_name} {bonus_str} {dmg} rng {rng}'{prop_str}"
        else:
            line = f"{weapon_name} {bonus_str} {dmg}{prop_str}"

        lines.append(line)

    return lines
