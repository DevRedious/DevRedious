#!/usr/bin/env python3
"""Génère les SVG animés du README de profil (assets/profile-*.svg).

Pour changer les projets ou la stack : modifier PROJECTS / STACK puis relancer
    python design/build_readme_assets.py

Le texte est converti en tracés : GitHub affiche les SVG dans des <img>, qui ne
peuvent charger aucune police. Les animations partent toujours de l'état final
(fill-mode backwards), donc un lecteur sans animation montre une image complète.

Polices (licence OFL) : Oswald et Source Code Pro, installées pour l'utilisateur.
"""
import base64
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICONS = ROOT / "uploads"
FONTS = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"

BG = "#0A0A0B"
INK = "#F4F3F0"
SOFT = "#CFCDC8"
MUTED = "#8E8E93"
DIM = "#7A7A80"
GOLD = "#C2A878"
EASE_OUT = "cubic-bezier(.16,1,.3,1)"
EASE_IO = "cubic-bezier(.65,0,.35,1)"
WIDTH = 960

ROLES = ["apps desktop", "bots Discord", "plateformes web", "outils & scripts"]

# (nom, description, technos, logo dans uploads/projects/)
PROJECTS = [
    ("Wilobot", "Bot Discord et plateforme web", "RUST · AXUM · REACT", "wilobot.png"),
    ("ARK Management", "Gestion de serveurs ARK : API, agent, plugin, interface web", "TYPESCRIPT · RUST · C++", "ark-management.svg"),
    ("Rilindra", "Écosystème communautaire ARK : bot, application, staff, MCP", "DISCORD.JS · TYPESCRIPT · MCP", "rilindra.png"),
    ("Primal Ascension", "Bot Discord, console staff et état du cluster en direct", "DISCORD.JS · NEXT.JS · HEROUI", "primal-ascension.png"),
    ("Poddock", "Cockpit desktop pour Podman : conteneurs, bots, sites locaux", "TAURI · RUST · REACT", "poddock.svg"),
]

# (fichier dans uploads/, libellé, viewBox de recadrage éventuel)
STACK = [
    ("tauri.svg", "Tauri", None),
    ("rust_dark.svg", "Rust", None),
    ("React_dark.svg", "React", None),
    ("typescript.svg", "TypeScript", None),
    ("nextjs_icon_dark.svg", "Next.js", None),
    ("nodejs.svg", "Node.js", None),
    ("biomejs.svg", "Biome", None),
    ("LogosDiscord.svg", "Discord", "0 0 127 100"),
    ("linux-dark.svg", "Linux", None),
    ("claude-logo.svg", "Claude", None),
]


def num(value):
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


class Face:
    """Police convertie en tracés SVG, avec crénage GPOS."""

    def __init__(self, filename):
        self.font = TTFont(FONTS / filename)
        self.glyphs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self.upem = self.font["head"].unitsPerEm
        self.pairs = self._kerning_subtables()

    def _kerning_subtables(self):
        if "GPOS" not in self.font:
            return []
        table = self.font["GPOS"].table
        indexes = {
            i
            for record in table.FeatureList.FeatureRecord
            if record.FeatureTag == "kern"
            for i in record.Feature.LookupListIndex
        }
        found = []
        for i in sorted(indexes):
            for sub in table.LookupList.Lookup[i].SubTable:
                sub = getattr(sub, "ExtSubTable", sub)
                if sub.LookupType == 2:
                    found.append(sub)
        return found

    def _kern(self, left, right):
        for sub in self.pairs:
            if left not in sub.Coverage.glyphs:
                continue
            if sub.Format == 1:
                index = sub.Coverage.glyphs.index(left)
                for pair in sub.PairSet[index].PairValueRecord:
                    if pair.SecondGlyph == right:
                        return getattr(pair.Value1, "XAdvance", 0) if pair.Value1 else 0
                continue
            first = sub.ClassDef1.classDefs.get(left, 0)
            second = sub.ClassDef2.classDefs.get(right, 0)
            value = sub.Class1Record[first].Class2Record[second].Value1
            return getattr(value, "XAdvance", 0) if value else 0
        return 0

    def _layout(self, text, size, tracking):
        scale = size / self.upem
        names = [self.cmap[ord(ch)] for ch in text]
        pen_x, placed = 0.0, []
        for i, name in enumerate(names):
            placed.append((name, pen_x))
            pen_x += self.glyphs[name].width * scale + tracking
            if i + 1 < len(names):
                pen_x += self._kern(name, names[i + 1]) * scale
        return placed, pen_x - tracking

    def width(self, text, size, tracking=0):
        return self._layout(text, size, tracking)[1]

    def letters(self, text, size, x, y, tracking=0, anchor="start"):
        placed, total = self._layout(text, size, tracking)
        if anchor == "end":
            x -= total
        scale = size / self.upem
        result = []
        for name, offset in placed:
            pen = SVGPathPen(self.glyphs, ntos=num)
            self.glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x + offset, y)))
            result.append(pen.getCommands())
        return result

    def path(self, text, size, x, y, tracking=0, anchor="start"):
        return "".join(self.letters(text, size, x, y, tracking, anchor))


DISPLAY = Face("Oswald-Light.ttf")
HEADING = Face("Oswald-Regular.ttf")
MONO = Face("Source Code Pro for Powerline.otf")


def document(height, label, css, defs, body):
    reduced = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" fill="none" '
        f'role="img" aria-label="{escape(label)}">\n'
        f"<title>{escape(label)}</title>\n"
        f"<style>{css}{reduced}</style>\n"
        f'<defs><clipPath id="panel"><rect width="{WIDTH}" height="{height}" rx="16"/></clipPath>{defs}</defs>\n'
        f'<g clip-path="url(#panel)"><rect width="{WIDTH}" height="{height}" fill="{BG}"/>\n{body}\n</g>\n'
        f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{height - 1}" rx="15.5" stroke="#fff" stroke-opacity=".09"/>\n'
        f"</svg>\n"
    )


def label_text(text, x, y, fill=MUTED, anchor="start", size=13, tracking=2.6):
    return f'<path fill="{fill}" d="{MONO.path(text, size, x, y, tracking, anchor)}"/>'


def hero():
    cx, cy = 842, 170
    baseline = 212
    letters = DISPLAY.letters("DevRedious", 134, 53, baseline, tracking=1.5)
    rise = "".join(
        f'<path class="rise" style="animation-delay:{0.15 + i * 0.05:.2f}s" d="{d}"/>'
        for i, d in enumerate(letters)
    )
    mark = "".join(letters)

    roll_step = 32
    roll_x = 118 + MONO.width("développeur", 19) + 40
    items = ROLES + ROLES[:1]
    strip = "".join(
        f'<path d="{MONO.path(role, 19, roll_x, 268 + i * roll_step)}"/>' for i, role in enumerate(items)
    )
    stops = []
    count = len(ROLES)
    for i in range(count):
        start, end = i * 100 / count, (i + 1) * 100 / count - 5
        stops.append(f"{start:g}%,{end:g}%{{transform:translateY({-i * roll_step}px)}}")
    stops.append(f"100%{{transform:translateY({-count * roll_step}px)}}")

    css = f"""
.rise{{animation:rise 1.25s {EASE_OUT} backwards}}
@keyframes rise{{from{{transform:translateY(170px)}}}}
.rule{{transform-origin:58px 0;animation:grow 1s .8s {EASE_OUT} backwards}}
@keyframes grow{{from{{transform:scaleX(0)}}}}
.fade{{animation:fade 1.2s .95s ease backwards}}
@keyframes fade{{from{{opacity:0}}}}
.roll{{animation:roll 12s {EASE_IO} infinite}}
@keyframes roll{{{"".join(stops)}}}
.spin{{transform-origin:{cx}px {cy}px;animation:spin linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.rings{{transform-origin:{cx}px {cy}px;animation:rings 1.8s .25s {EASE_OUT} backwards}}
@keyframes rings{{from{{opacity:0;transform:scale(.86) rotate(-24deg)}}}}
.ping{{opacity:0;transform-origin:{cx}px {cy}px;animation:ping 4.5s ease-out 1.6s infinite}}
@keyframes ping{{0%{{opacity:.75;transform:scale(1)}}70%,100%{{opacity:0;transform:scale(14)}}}}
.core{{animation:core 4.5s ease-in-out 1.6s infinite}}
@keyframes core{{0%,100%{{opacity:1}}50%{{opacity:.45}}}}
.glow{{animation:glow 9s ease-in-out infinite}}
@keyframes glow{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
.sheen{{animation:sheen 10s {EASE_IO} 2.2s infinite}}
@keyframes sheen{{0%{{transform:translateX(0)}}32%,100%{{transform:translateX(1000px)}}}}
.line{{animation:line 7s {EASE_IO} 1.4s infinite}}
@keyframes line{{0%{{transform:translateX(0);opacity:0}}12%,88%{{opacity:1}}100%{{transform:translateX(1360px);opacity:0}}}}
"""
    defs = f"""
<pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r=".9" fill="#fff" fill-opacity=".1"/></pattern>
<radialGradient id="dotfade" cx="{cx}" cy="{cy}" r="460" gradientUnits="userSpaceOnUse"><stop stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>
<mask id="dotmask"><rect width="{WIDTH}" height="340" fill="url(#dotfade)"/></mask>
<radialGradient id="halo" cx="{cx}" cy="{cy}" r="330" gradientUnits="userSpaceOnUse"><stop stop-color="{GOLD}" stop-opacity=".2"/><stop offset=".55" stop-color="{GOLD}" stop-opacity=".04"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
<clipPath id="stage"><rect x="0" y="0" width="{WIDTH}" height="{baseline + 3}"/></clipPath>
<clipPath id="rollclip"><rect x="{roll_x - 4:.1f}" y="247" width="280" height="30"/></clipPath>
<mask id="markmask"><path fill="#fff" d="{mark}"/></mask>
<linearGradient id="sheenfill" x1="0" x2="1" y1="0" y2="0"><stop stop-color="{GOLD}" stop-opacity="0"/><stop offset=".5" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>
<linearGradient id="hair" x1="0" x2="1" y1="0" y2="0"><stop stop-color="{GOLD}" stop-opacity="0"/><stop offset=".5" stop-color="{GOLD}" stop-opacity=".5"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>
<linearGradient id="spark" x1="0" x2="1" y1="0" y2="0"><stop stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".95"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
"""

    def arc(radius, length, width=1.5, color=GOLD, opacity=1, offset=0):
        import math

        gap = 2 * math.pi * radius - length
        return (
            f'<circle cx="{cx}" cy="{cy}" r="{radius}" stroke="{color}" stroke-opacity="{opacity}" '
            f'stroke-width="{width}" stroke-dasharray="{length} {gap:.1f}" stroke-dashoffset="{offset}" stroke-linecap="round"/>'
        )

    def ring(radius, opacity, dash=None, width=1):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<circle cx="{cx}" cy="{cy}" r="{radius}" stroke="#fff" stroke-opacity="{opacity}" stroke-width="{width}"{extra}/>'

    def satellite(radius):
        return f'<circle cx="{cx + radius}" cy="{cy}" r="3.2" fill="{GOLD}"/>'

    rings = f"""
<g class="rings">
  <g class="spin" style="animation-duration:140s">{ring(214, .16, "1 12.45", 9)}</g>
  {ring(164, .1)}
  <g class="spin" style="animation-duration:22s">{arc(164, 150, 1.6, GOLD, .95)}{satellite(164)}</g>
  <g class="spin" style="animation-duration:74s;animation-direction:reverse">{ring(116, .22, "2 7")}</g>
  <g class="spin" style="animation-duration:13s;animation-direction:reverse">{arc(116, 70, 1.4, GOLD, .7)}</g>
  {ring(62, .14)}
  <g class="spin" style="animation-duration:8s">{satellite(62)}</g>
</g>
<circle class="ping" cx="{cx}" cy="{cy}" r="6" stroke="{GOLD}" vector-effect="non-scaling-stroke"/>
<circle class="core" cx="{cx}" cy="{cy}" r="4.5" fill="{GOLD}"/>
"""

    body = f"""
<rect width="{WIDTH}" height="340" fill="url(#dots)" mask="url(#dotmask)"/>
<rect class="glow" width="{WIDTH}" height="340" fill="url(#halo)"/>
{rings}
<g class="fade">{label_text("GITHUB.COM / DEVREDIOUS", 58, 66)}</g>
<g clip-path="url(#stage)" fill="{INK}">{rise}</g>
<g mask="url(#markmask)"><rect class="sheen" x="-300" y="60" width="300" height="170" fill="url(#sheenfill)"/></g>
<rect class="rule" x="58" y="261" width="46" height="2" fill="{GOLD}"/>
<g class="fade">
  <path fill="{MUTED}" d="{MONO.path("développeur", 19, 118, 268)}"/>
  <path fill="{DIM}" d="{MONO.path("/", 19, 118 + MONO.width("développeur", 19) + 15, 268)}"/>
  <g clip-path="url(#rollclip)" fill="{INK}"><g class="roll">{strip}</g></g>
</g>
<rect x="40" y="306" width="880" height="1" fill="url(#hair)"/>
<rect class="line" x="-300" y="305" width="260" height="3" fill="url(#spark)"/>
"""
    label = "DevRedious, développeur : " + ", ".join(ROLES)
    return document(340, label, css, defs, body)


def projects():
    top, row, node_x, icon_x, box, text_x, right = 74, 100, 64, 94, 56, 170, 920
    count = len(PROJECTS)
    height = top + row * count + 8
    first_node = top + row // 2
    period = 2.5 * count
    share = 100 / count
    moves = []
    for k in range(count):
        at = k * share
        moves.append(f"{at:g}%,{at + share * .62:g}%{{transform:translateY({k * row}px)}}")
    moves.append(f"100%{{transform:translateY({(count - 1) * row}px)}}")

    css = f"""
.rowband,.nodeon,.tileon{{opacity:0}}
.rowband,.nodeon,.tileon,.tile,.halo,.name,.desc{{animation-duration:{period:g}s;animation-iteration-count:infinite;animation-fill-mode:backwards}}
.rowband,.nodeon,.tileon{{animation-name:on}}
@keyframes on{{0%{{opacity:0}}3%,16%{{opacity:1}}23%,100%{{opacity:0}}}}
.tile{{transform-box:fill-box;transform-origin:center;animation-name:pop;animation-timing-function:{EASE_OUT}}}
@keyframes pop{{0%{{transform:scale(1)}}5%{{transform:scale(1.08)}}16%{{transform:scale(1.04)}}23%,100%{{transform:scale(1)}}}}
.name{{fill:{INK};animation-name:name}}
@keyframes name{{0%{{fill:{INK}}}3%,16%{{fill:{GOLD}}}23%,100%{{fill:{INK}}}}}
.desc{{fill:{MUTED};animation-name:desc}}
@keyframes desc{{0%{{fill:{MUTED}}}3%,16%{{fill:{SOFT}}}23%,100%{{fill:{MUTED}}}}}
.halo{{opacity:0;transform-box:fill-box;transform-origin:center;animation-name:halo;animation-timing-function:ease-out}}
@keyframes halo{{0%{{opacity:.8;transform:scale(1)}}15%,100%{{opacity:0;transform:scale(3.6)}}}}
.pulse{{opacity:0;animation:move {period:g}s {EASE_IO} infinite,show {period:g}s linear infinite}}
@keyframes move{{{"".join(moves)}}}
@keyframes show{{0%{{opacity:0}}2%,{100 - share * .3:g}%{{opacity:1}}{100 - share * .1:g}%,100%{{opacity:0}}}}
"""
    defs = f"""
<radialGradient id="comet"><stop stop-color="{GOLD}" stop-opacity=".55"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
<linearGradient id="bandfill" x1="0" x2="1" y1="0" y2="0"><stop stop-color="{GOLD}" stop-opacity=".1"/><stop offset=".7" stop-color="{GOLD}" stop-opacity=".02"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>
<radialGradient id="tilefill" cx=".5" cy=".42" r=".78"><stop stop-color="#55555C"/><stop offset="1" stop-color="#1C1C20"/></radialGradient>
{"".join(load_icon(ICONS / "projects" / p[3], f"app{i}") for i, p in enumerate(PROJECTS))}
"""
    parts = [
        label_text("PROJETS", 40, 46),
        label_text("DÉPÔTS PRIVÉS", right, 46, DIM, "end"),
        f'<rect x="40" y="{top - 1}" width="{right - 40}" height="1" fill="#fff" fill-opacity=".08"/>',
        f'<rect x="{node_x - .5}" y="{first_node}" width="1" height="{(count - 1) * row}" fill="#fff" fill-opacity=".16"/>',
    ]
    for i, (name, description, tags, logo) in enumerate(PROJECTS):
        y = top + i * row
        node_y = y + row // 2
        box_y = node_y - box // 2
        delay = f'style="animation-delay:{i * 2.5:g}s"'
        parts.append(f'<rect class="rowband" {delay} x="1" y="{y}" width="{WIDTH - 2}" height="{row}" fill="url(#bandfill)"/>')
        if i:
            parts.append(f'<rect x="{icon_x}" y="{y}" width="{right - icon_x}" height="1" fill="#fff" fill-opacity=".06"/>')
        parts.append(f'<circle cx="{node_x}" cy="{node_y}" r="5" fill="{BG}" stroke="{GOLD}" stroke-opacity=".7" stroke-width="1.2"/>')
        parts.append(f'<circle class="halo" {delay} cx="{node_x}" cy="{node_y}" r="5" stroke="{GOLD}" vector-effect="non-scaling-stroke"/>')
        parts.append(f'<circle class="nodeon" {delay} cx="{node_x}" cy="{node_y}" r="5" fill="{GOLD}"/>')
        square = logo.endswith(".svg")  # les logos vectoriels ont déjà leur fond arrondi
        pad = 0 if square else 4
        tile_bg = "" if square else f'<rect x="{icon_x}" y="{box_y}" width="{box}" height="{box}" rx="13" fill="url(#tilefill)"/>'
        parts.append(
            f'<g class="tile" {delay}>{tile_bg}'
            f'<use href="#app{i}" xlink:href="#app{i}" x="{icon_x + pad}" y="{box_y + pad}" width="{box - 2 * pad}" height="{box - 2 * pad}"/>'
            f'<rect x="{icon_x + .5}" y="{box_y + .5}" width="{box - 1}" height="{box - 1}" rx="12.5" stroke="#fff" stroke-opacity=".12"/>'
            f'<rect class="tileon" {delay} x="{icon_x + .5}" y="{box_y + .5}" width="{box - 1}" height="{box - 1}" rx="12.5" stroke="{GOLD}" stroke-width="1.4"/></g>'
        )
        parts.append(f'<path class="name" {delay} d="{HEADING.path(name, 33, text_x, y + 47, .3)}"/>')
        parts.append(f'<path class="desc" {delay} d="{MONO.path(description, 16, text_x, y + 77)}"/>')
        parts.append(label_text(tags, right, y + 46, MUTED, "end", 13, 1.1))
    parts.append(
        f'<g class="pulse"><circle cx="{node_x}" cy="{first_node}" r="13" fill="url(#comet)"/>'
        f'<circle cx="{node_x}" cy="{first_node}" r="2.6" fill="#fff"/></g>'
    )
    label = "Projets (dépôts privés). " + " ".join(f"{n} : {d}." for n, d, *_ in PROJECTS)
    return document(height, label, css, defs, "\n".join(parts))


def load_icon(path, symbol_id, crop=None):
    if path.suffix == ".png":
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return (
            f'<symbol id="{symbol_id}" viewBox="0 0 128 128">'
            f'<image width="128" height="128" href="data:image/png;base64,{data}"/></symbol>'
        )
    raw = path.read_text(encoding="utf-8")
    root = re.search(r"<svg\b[^>]*>", raw).group(0)
    inner = raw[raw.index(root) + len(root) : raw.rindex("</svg>")]
    inner = re.sub(r"<title>.*?</title>|<!--.*?-->", "", inner, flags=re.S)
    view_box = crop or re.search(r'viewBox="([^"]+)"', root).group(1)
    prefix = f"{symbol_id}-"
    if "fill=" not in raw:  # sans couleur, le tracé serait noir sur fond noir
        inner = f'<g fill="{INK}">{inner.strip()}</g>'
    for old in re.findall(r'\bid="([^"]+)"', inner):
        inner = inner.replace(f'id="{old}"', f'id="{prefix}{old}"')
        inner = inner.replace(f"url(#{old})", f"url(#{prefix}{old})")
        inner = inner.replace(f'href="#{old}"', f'href="#{prefix}{old}"')
    return f'<symbol id="{symbol_id}" viewBox="{view_box}">{inner.strip()}</symbol>'


def stack():
    height, left, usable, box, icon_y = 196, 40, 880, 46, 72
    step = usable / len(STACK)
    period = 9
    css = f"""
.lit,.tag,.lift{{animation-duration:{period}s;animation-iteration-count:infinite;animation-fill-mode:backwards}}
.lit{{animation-name:tide}}
@keyframes tide{{0%{{opacity:0}}7%,52%{{opacity:1}}60%,100%{{opacity:0}}}}
.tag{{fill:{MUTED};animation-name:tag}}
@keyframes tag{{0%{{fill:{DIM}}}7%,52%{{fill:{SOFT}}}60%,100%{{fill:{DIM}}}}}
.lift{{animation-name:lift;animation-timing-function:{EASE_OUT}}}
@keyframes lift{{0%{{transform:translateY(0)}}3.5%{{transform:translateY(-5px)}}11%,100%{{transform:translateY(0)}}}}
.head{{opacity:0;animation:head {period}s linear infinite}}
@keyframes head{{0%{{transform:translateX(0);opacity:0}}2%{{opacity:1}}19%{{transform:translateX({usable - 90}px);opacity:1}}22%{{transform:translateX({usable - 90}px);opacity:0}}50%{{transform:translateX(0);opacity:0}}52%{{transform:translateX(0);opacity:1}}71%{{transform:translateX({usable - 90}px);opacity:1}}74%,100%{{transform:translateX({usable - 90}px);opacity:0}}}}
"""
    symbols = "".join(load_icon(ICONS / f, f"icon{i}", crop) for i, (f, _, crop) in enumerate(STACK))
    defs = f"""
<filter id="mono" color-interpolation-filters="sRGB"><feColorMatrix type="matrix" values=".1 .33 .03 0 .035 .1 .33 .03 0 .035 .1 .33 .03 0 .04 0 0 0 .9 0"/></filter>
<linearGradient id="headfill" x1="0" x2="1" y1="0" y2="0"><stop stop-color="{GOLD}" stop-opacity="0"/><stop offset=".5" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient>
{symbols}
"""
    parts = [
        label_text("STACK", 40, 46),
        f'<rect x="40" y="{height - 26}" width="{usable}" height="1" fill="#fff" fill-opacity=".08"/>',
    ]
    for i, (_, name, _crop) in enumerate(STACK):
        center = left + step * (i + 0.5)
        x = center - box / 2
        delay = f'style="animation-delay:{i * .16:.2f}s"'
        use = f'<use href="#icon{i}" xlink:href="#icon{i}" x="{x:g}" y="{icon_y}" width="{box}" height="{box}"/>'
        parts.append(
            f'<g class="lift" {delay}><g filter="url(#mono)">{use}</g><g class="lit" {delay}>{use}</g></g>'
        )
        parts.append(f'<path class="tag" {delay} d="{MONO.path(name, 13, center - MONO.width(name, 13, .3) / 2, icon_y + box + 30, .3)}"/>')
    parts.append(f'<rect class="head" x="40" y="{height - 27}" width="90" height="2" fill="url(#headfill)"/>')
    label = "Stack : " + ", ".join(name for _, name, _ in STACK)
    return document(height, label, css, defs, "\n".join(parts))


def main():
    outputs = {"profile-hero.svg": hero(), "profile-projects.svg": projects(), "profile-stack.svg": stack()}
    for filename, content in outputs.items():
        (ASSETS / filename).write_text(content, encoding="utf-8", newline="\n")
        print(f"{filename}: {len(content.encode('utf-8')) / 1024:.1f} Ko")


if __name__ == "__main__":
    main()
