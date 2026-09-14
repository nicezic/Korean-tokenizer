import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "svg" / "hangul-jamo.svg"

WIDTH = 800
HEIGHT = 955
MARGIN = 35
CONTENT_WIDTH = WIDTH - 2 * MARGIN
SECTION_INSET_X = 18
SECTION_GAP = 12

PANEL_GAP = 20
PANEL_WIDTH = (CONTENT_WIDTH - PANEL_GAP) // 2
PANEL_INSET_X = 16
PANEL_INNER_WIDTH = PANEL_WIDTH - 2 * PANEL_INSET_X
PANEL_CENTER_X = PANEL_WIDTH / 2
PANEL_HEADER_END_X = PANEL_WIDTH - 15
TOP_ITEM_GAP = 15
HEADER_Y = 20
HEADER_BADGE_WIDTH = 86
HEADER_BADGE_CENTER_X = HEADER_BADGE_WIDTH / 2
HEADER_TITLE_X = HEADER_BADGE_WIDTH + 10

TOP_PANELS_Y = 65
TOP_PANELS_HEIGHT = 175
RIGHT_PANEL_X = MARGIN + PANEL_WIDTH + PANEL_GAP

DOCK_Y = TOP_PANELS_Y + TOP_PANELS_HEIGHT + SECTION_GAP
DOCK_HEIGHT = 142
DOCK_LABEL_WIDTH = 86
DOCK_KEYS_X = 98
KEY_AREA_WIDTH = 596
KEY_HEIGHT = 22
DOCK_FIRST_ROW_Y = 42
DOCK_ROW_STEP = 28

SCALE_Y = DOCK_Y + DOCK_HEIGHT + 14
SCALE_HEIGHT = 336
SCALE_BODY_Y = 38
SCALE_BODY_HEIGHT = 282
SCALE_COLUMN_GAP = 8
SCALE_ASIDE_WIDTH = 186
SCALE_ASIDE_X = CONTENT_WIDTH - SECTION_INSET_X - SCALE_ASIDE_WIDTH
SCALE_MAIN_WIDTH = SCALE_ASIDE_X - SECTION_INSET_X - SCALE_COLUMN_GAP
SCALE_CARD_INSET = 8
SCALE_MAIN_INNER_WIDTH = SCALE_MAIN_WIDTH - 2 * SCALE_CARD_INSET
SCALE_ASIDE_INSET = 7
SCALE_ASIDE_INNER_WIDTH = SCALE_ASIDE_WIDTH - 2 * SCALE_ASIDE_INSET
SCALE_ASIDE_CENTER_X = SCALE_ASIDE_WIDTH / 2
SCALE_ASIDE_RIGHT_TEXT_X = SCALE_ASIDE_WIDTH - 13
SCALE_MAIN_CENTER_X = SCALE_MAIN_WIDTH / 2
SCALE_SUMMARY_HEIGHT = 110
SCALE_HUD_GAP = 6
SCALE_HUD_Y = SCALE_SUMMARY_HEIGHT + SCALE_HUD_GAP
SCALE_HUD_HEIGHT = SCALE_BODY_HEIGHT - SCALE_HUD_Y
DENSE_ROW_COUNT = 6
DENSE_COLUMN_COUNT = 56
DENSE_ROW_STEP = 14
DENSE_TEXT_X = 10
DENSE_TEXT_LENGTH = SCALE_MAIN_WIDTH - 2 * DENSE_TEXT_X
DENSE_UPPER_Y = 37
DENSE_TRUNCATION_Y = 118
DENSE_TRUNCATION_HEIGHT = 22
DENSE_LOWER_Y = DENSE_TRUNCATION_Y + DENSE_TRUNCATION_HEIGHT + DENSE_ROW_STEP

SHOWDOWN_Y = SCALE_Y + SCALE_HEIGHT + SECTION_GAP
SHOWDOWN_HEIGHT = 100
SHOWDOWN_CARD_Y = 34
SHOWDOWN_CARD_HEIGHT = 54
SHOWDOWN_CARD_CENTER_Y = SHOWDOWN_CARD_Y + SHOWDOWN_CARD_HEIGHT / 2

FOOTER_Y = SHOWDOWN_Y + SHOWDOWN_HEIGHT + SECTION_GAP
FOOTER_HEIGHT = 66
FOOTER_INSET_X = 16
FOOTER_BADGE_WIDTH = 84
FOOTER_BADGE_CENTER_X = FOOTER_INSET_X + FOOTER_BADGE_WIDTH / 2
FOOTER_TITLE_X = FOOTER_INSET_X + FOOTER_BADGE_WIDTH + 12
FOOTER_RIGHT_X = CONTENT_WIDTH - FOOTER_INSET_X

COLOR_BG = "#0d1117"
COLOR_SURFACE = "#161b22"
COLOR_PANEL = "#10151d"
COLOR_DIVIDER = "#21262d"
COLOR_BORDER = "#30363d"
COLOR_MUTED = "#8b949e"
COLOR_DIM = "#6e7681"
COLOR_SUBTLE = "#c9d1d9"
COLOR_TEXT = "#f0f6fc"
COLOR_WHITE = "#ffffff"
ALERT_FILL = "#da3633"
ALERT_DOT = "#f85149"
ALERT_TEXT = "#ff7b72"

ANIMATION_SECONDS = 8.0
FLIGHT_TRAVEL_SECONDS = 0.5

HANGUL_BASE = 0xAC00
HANGUL_SYLLABLE_COUNT = 11_172


@dataclass(frozen=True)
class JamoRole:
    label: str
    chars: tuple[str, ...]
    fill: str
    stroke: str
    label_color: str
    dot_color: str
    glow: str
    key_width: int
    key_start_x: int
    prefix_label: str | None
    prefix_width: int
    key_font_size: float
    highlight_font_size: float
    flight_width: int
    flight_height: int
    flight_font_size: int


JAMO_ROLES = {
    "initial": JamoRole(
        label="INITIAL",
        chars=tuple("ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎㄲㄸㅃㅆㅉ"),
        fill="#1f6feb",
        stroke="#79c0ff",
        label_color="#58a6ff",
        dot_color="#388bfd",
        glow="glow-blue",
        key_width=27,
        key_start_x=0,
        prefix_label=None,
        prefix_width=0,
        key_font_size=12.5,
        highlight_font_size=12.5,
        flight_width=32,
        flight_height=32,
        flight_font_size=18,
    ),
    "vowel": JamoRole(
        label="VOWEL",
        chars=tuple("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"),
        fill="#d29922",
        stroke="#f2cc60",
        label_color="#e3b341",
        dot_color="#d29922",
        glow="glow-gold",
        key_width=25,
        key_start_x=0,
        prefix_label=None,
        prefix_width=0,
        key_font_size=12.5,
        highlight_font_size=12.5,
        flight_width=32,
        flight_height=32,
        flight_font_size=18,
    ),
    "final": JamoRole(
        label="FINAL",
        chars=tuple("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"),
        fill="#238636",
        stroke="#56d364",
        label_color="#3fb950",
        dot_color="#2ea043",
        glow="glow-green",
        key_width=18,
        key_start_x=48,
        prefix_label="(none)",
        prefix_width=40,
        key_font_size=11,
        highlight_font_size=11.5,
        flight_width=44,
        flight_height=26,
        flight_font_size=17,
    ),
}

ROLE_ORDER = tuple(JAMO_ROLES)
JAMO_SYMBOL_COUNT = sum(len(role.chars) for role in JAMO_ROLES.values())
FINAL_COMBINATION_COUNT = len(JAMO_ROLES["final"].chars) + 1
INITIAL_STRIDE = len(JAMO_ROLES["vowel"].chars) * FINAL_COMBINATION_COUNT

SYLLABLE_SLOT_Y = 38
SYLLABLE_SLOT_WIDTH = (PANEL_INNER_WIDTH - TOP_ITEM_GAP) // 2
SYLLABLE_SLOT_HEIGHT = 96
SYLLABLE_BOX_INSET = 6
SYLLABLE_BOX_GAP = 6
SYLLABLE_BOX_HEIGHT = 40
SYLLABLE_TOP_BOX_WIDTH = (SYLLABLE_SLOT_WIDTH - 2 * SYLLABLE_BOX_INSET - SYLLABLE_BOX_GAP) // 2
SYLLABLE_FINAL_BOX_WIDTH = SYLLABLE_SLOT_WIDTH - 2 * SYLLABLE_BOX_INSET
SYLLABLE_FINAL_BOX_Y = SYLLABLE_SLOT_HEIGHT - SYLLABLE_BOX_INSET - SYLLABLE_BOX_HEIGHT
SYLLABLE_ROLE_BOXES = {
    "initial": (SYLLABLE_BOX_INSET, SYLLABLE_BOX_INSET, SYLLABLE_TOP_BOX_WIDTH, SYLLABLE_BOX_HEIGHT),
    "vowel": (
        SYLLABLE_BOX_INSET + SYLLABLE_TOP_BOX_WIDTH + SYLLABLE_BOX_GAP,
        SYLLABLE_BOX_INSET,
        SYLLABLE_TOP_BOX_WIDTH,
        SYLLABLE_BOX_HEIGHT,
    ),
    "final": (SYLLABLE_BOX_INSET, SYLLABLE_FINAL_BOX_Y, SYLLABLE_FINAL_BOX_WIDTH, SYLLABLE_BOX_HEIGHT),
}
BYTE_BOX_MARGIN = 12
BYTE_BOX_WIDTH = (PANEL_INNER_WIDTH - 2 * BYTE_BOX_MARGIN - TOP_ITEM_GAP) // 2


@dataclass(frozen=True)
class SyllableSpec:
    char: str
    byte_text: str
    jamo: tuple[str, str, str]
    inject_seconds: tuple[float, float, float]
    assemble_seconds: float

    @property
    def formula(self):
        return " + ".join(self.jamo)

    @property
    def injections(self):
        return tuple(zip(ROLE_ORDER, self.jamo, self.inject_seconds, strict=True))


SYLLABLES = (
    SyllableSpec("한", "ED 95 9C", ("ㅎ", "ㅏ", "ㄴ"), (0.3, 0.9, 1.5), 2.1),
    SyllableSpec("글", "EA B8 80", ("ㄱ", "ㅡ", "ㄹ"), (2.7, 3.3, 3.9), 4.5),
)
SAMPLE_WORD = "".join(syllable.char for syllable in SYLLABLES)
COMPLETE_SECONDS = 4.8


def syllable_slot_x(syllable):
    index = SYLLABLES.index(syllable)
    return PANEL_INSET_X + index * (SYLLABLE_SLOT_WIDTH + TOP_ITEM_GAP)


def byte_box_x(index):
    return BYTE_BOX_MARGIN + index * (BYTE_BOX_WIDTH + TOP_ITEM_GAP)


@dataclass(frozen=True)
class FlightSpec:
    char: str
    role: str
    syllable: SyllableSpec
    start_seconds: float

    @property
    def start_fraction(self):
        return self.start_seconds / ANIMATION_SECONDS

    @property
    def end_fraction(self):
        return self.syllable.assemble_seconds / ANIMATION_SECONDS


FLIGHTS = tuple(
    FlightSpec(char, role, syllable, seconds) for syllable in SYLLABLES for role, char, seconds in syllable.injections
)
FLIGHT_BY_KEY = {(flight.role, flight.char): flight for flight in FLIGHTS}


class Svg:
    def __init__(self):
        self.lines = []
        self.level = 0

    @staticmethod
    def _attrs(attrs):
        parts = []
        for key, value in attrs.items():
            if value is None:
                continue
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            name = key.replace("_", "-")
            encoded = escape(str(value), quote=False).replace('"', "&quot;")
            parts.append(f'{name}="{encoded}"')
        return " ".join(parts)

    def _emit(self, line):
        self.lines.append(f"{'  ' * self.level}{line}")

    def open(self, tag, **attrs):
        suffix = self._attrs(attrs)
        self._emit(f"<{tag}{' ' + suffix if suffix else ''}>")
        self.level += 1

    def close(self, tag):
        self.level -= 1
        self._emit(f"</{tag}>")

    @contextmanager
    def group(self, **attrs):
        self.open("g", **attrs)
        try:
            yield
        finally:
            self.close("g")

    def empty(self, tag, **attrs):
        suffix = self._attrs(attrs)
        self._emit(f"<{tag}{' ' + suffix if suffix else ''}/>")

    def text(self, content, **attrs):
        suffix = self._attrs(attrs)
        body = escape(str(content))
        self._emit(f"<text{' ' + suffix if suffix else ''}>{body}</text>")

    def animated_text(self, content, animations, **attrs):
        self.open("text", **attrs)
        for attribute, values, key_times in animations:
            self.animate(attribute, values, key_times)
        self._emit(escape(str(content)))
        self.close("text")

    def animate(self, attribute, values, key_times):
        self.empty(
            "animate",
            attributeName=attribute,
            values=values,
            keyTimes=key_times,
            dur=f"{ANIMATION_SECONDS:.1f}s",
            repeatCount="indefinite",
        )

    def animate_transform(self, values, key_times):
        self.empty(
            "animateTransform",
            attributeName="transform",
            type="translate",
            values=values,
            keyTimes=key_times,
            keySplines="0.16 1 0.3 1; 0.16 1 0.3 1; 0 0 1 1; 0 0 1 1",
            calcMode="spline",
            dur=f"{ANIMATION_SECONDS:.1f}s",
            repeatCount="indefinite",
        )

    def render(self):
        return "\n".join(self.lines)


def draw_defs(svg):
    blue = JAMO_ROLES["initial"]
    svg.open("defs")
    for gradient_id, start, end in (
        ("bg-grad", COLOR_BG, COLOR_SURFACE),
        ("card-glow-blue", blue.fill, blue.dot_color),
        ("card-glow-red", ALERT_FILL, ALERT_DOT),
    ):
        svg.open("linearGradient", id=gradient_id, x1="0%", y1="0%", x2="100%", y2="100%")
        svg.empty("stop", offset="0%", stop_color=start, stop_opacity=None if gradient_id == "bg-grad" else "0.16")
        svg.empty("stop", offset="100%", stop_color=end, stop_opacity=None if gradient_id == "bg-grad" else "0.02")
        svg.close("linearGradient")

    for filter_id, blur in (
        ("glow-blue", 4),
        ("glow-gold", 4),
        ("glow-green", 4),
        ("glow-red-strong", 4),
        ("glow-white", 3),
    ):
        svg.open("filter", id=filter_id, x="-30%", y="-30%", width="160%", height="160%")
        svg.empty("feGaussianBlur", stdDeviation=blur, result="blur")
        svg.empty("feComposite", **{"in": "SourceGraphic", "in2": "blur", "operator": "over"})
        svg.close("filter")
    svg.close("defs")


def draw_section_divider(svg, y):
    svg.empty(
        "line",
        x1=SECTION_INSET_X,
        y1=y,
        x2=CONTENT_WIDTH - SECTION_INSET_X,
        y2=y,
        stroke=COLOR_DIVIDER,
    )


def draw_section_shell(svg, height):
    svg.empty(
        "rect",
        width=CONTENT_WIDTH,
        height=height,
        rx=10,
        fill=COLOR_BG,
        stroke=COLOR_BORDER,
        stroke_width=1.5,
    )


def draw_section_header(svg, title, accent, circle_fill, font_size=11):
    svg.empty("circle", cx=18, cy=18, r=4, fill=circle_fill)
    svg.text(title, x=28, y=22, font_size=font_size, font_weight=700, fill=accent)
    draw_section_divider(svg, 28)


def draw_top_panel_frame(svg, title, subtitle, gradient, border, dot, title_color, border_opacity):
    svg.empty(
        "rect",
        width=PANEL_WIDTH,
        height=TOP_PANELS_HEIGHT,
        rx=10,
        fill=f"url(#{gradient})",
        stroke=border,
        stroke_opacity=border_opacity,
    )
    svg.empty("circle", cx=18, cy=18, r=4.5, fill=dot)
    svg.text(title, x=30, y=22, font_size=12, font_weight=700, fill=title_color)
    svg.text(subtitle, x=PANEL_HEADER_END_X, y=22, text_anchor="end", font_size=10, fill=COLOR_MUTED)
    svg.empty("line", x1=15, y1=32, x2=PANEL_HEADER_END_X, y2=32, stroke=COLOR_BORDER, stroke_width=0.8)


def draw_header(svg):
    green = JAMO_ROLES["final"]
    svg.empty("rect", width=WIDTH, height=HEIGHT, rx=14, fill="url(#bg-grad)", stroke=COLOR_BORDER, stroke_width=1.5)
    with svg.group(transform=f"translate({MARGIN}, {HEADER_Y})"):
        svg.empty(
            "rect",
            x=0,
            y=0,
            width=HEADER_BADGE_WIDTH,
            height=20,
            rx=10,
            fill=green.fill,
            fill_opacity=0.2,
            stroke=green.dot_color,
        )
        svg.text(
            "BENCHMARK",
            x=HEADER_BADGE_CENTER_X,
            y=14,
            text_anchor="middle",
            font_size=10.5,
            font_weight=700,
            fill=green.label_color,
        )
        svg.text(
            "Hangul: alphabetic Jamo assemble by role into two-dimensional syllable blocks.",
            x=HEADER_TITLE_X,
            y=15,
            font_size=12.8,
            font_weight=700,
            fill=COLOR_TEXT,
        )
        svg.text(
            "The benchmark asks whether tokenization preserves this structure while still compressing well.",
            x=0,
            y=37,
            font_size=11.5,
            fill=COLOR_MUTED,
        )


def draw_top_panels(svg):
    blue = JAMO_ROLES["initial"]
    with svg.group(transform=f"translate({MARGIN}, {TOP_PANELS_Y})"):
        draw_top_panel_frame(
            svg,
            "Precomposed Surface Form",
            "UTF-8 Encoding",
            "card-glow-red",
            ALERT_FILL,
            ALERT_DOT,
            ALERT_TEXT,
            0.4,
        )
        with svg.group(transform=f"translate({PANEL_INSET_X}, 40)"):
            svg.empty("rect", width=PANEL_INNER_WIDTH, height=82, rx=6, fill=COLOR_BG, stroke=COLOR_BORDER)
            for index, syllable in enumerate(SYLLABLES):
                x = byte_box_x(index)
                svg.empty(
                    "rect",
                    x=x,
                    y=16,
                    width=BYTE_BOX_WIDTH,
                    height=50,
                    rx=5,
                    fill=COLOR_DIVIDER,
                    stroke=ALERT_DOT,
                    stroke_width=1.2,
                )
                svg.text(
                    syllable.byte_text,
                    x=x + BYTE_BOX_WIDTH / 2,
                    y=40,
                    text_anchor="middle",
                    font_size=13,
                    font_family="monospace",
                    font_weight=800,
                    fill=ALERT_TEXT,
                )
                svg.text(
                    f"[ {syllable.char} · 3 Bytes ]",
                    x=x + BYTE_BOX_WIDTH / 2,
                    y=57,
                    text_anchor="middle",
                    font_size=11,
                    font_weight=700,
                    fill=COLOR_MUTED,
                )
        svg.empty(
            "rect",
            x=PANEL_INSET_X,
            y=130,
            width=PANEL_INNER_WIDTH,
            height=30,
            rx=5,
            fill=ALERT_FILL,
            fill_opacity=0.15,
            stroke=ALERT_FILL,
            stroke_width=0.8,
        )
        svg.text(
            "Structure is hidden at this representation layer",
            x=PANEL_CENTER_X,
            y=150,
            text_anchor="middle",
            font_size=10.5,
            font_weight=700,
            fill=ALERT_TEXT,
        )

    with svg.group(transform=f"translate({RIGHT_PANEL_X}, {TOP_PANELS_Y})"):
        draw_top_panel_frame(
            svg,
            "Hangul 2D Syllable Architecture",
            "Positional Assembly",
            "card-glow-blue",
            blue.fill,
            blue.dot_color,
            blue.label_color,
            0.5,
        )
        for syllable in SYLLABLES:
            draw_syllable_slot(svg, syllable)
        svg.empty(
            "rect",
            x=PANEL_INSET_X,
            y=140,
            width=PANEL_INNER_WIDTH,
            height=24,
            rx=4,
            fill=COLOR_BG,
            stroke=COLOR_BORDER,
            stroke_width=0.8,
        )
        svg.text(
            f"0x{HANGUL_BASE:04X} + (Initial×{INITIAL_STRIDE}) + (Vowel×{FINAL_COMBINATION_COUNT}) + Final",
            x=PANEL_CENTER_X,
            y=156,
            text_anchor="middle",
            font_size=10,
            font_family="monospace",
            fill=blue.stroke,
        )


def draw_syllable_slot(svg, syllable):
    blue = JAMO_ROLES["initial"]
    reveal_at = syllable.assemble_seconds / ANIMATION_SECONDS
    with svg.group(transform=f"translate({syllable_slot_x(syllable)}, {SYLLABLE_SLOT_Y})"):
        svg.empty(
            "rect",
            width=SYLLABLE_SLOT_WIDTH,
            height=SYLLABLE_SLOT_HEIGHT,
            rx=6,
            fill=COLOR_BG,
            stroke=COLOR_BORDER,
            stroke_width=1.2,
            stroke_dasharray="3 3",
        )
        for role in ROLE_ORDER:
            rx, ry, rw, rh = SYLLABLE_ROLE_BOXES[role]
            role_spec = JAMO_ROLES[role]
            svg.empty(
                "rect",
                x=rx,
                y=ry,
                width=rw,
                height=rh,
                rx=3,
                fill=role_spec.fill,
                fill_opacity=0.08,
                stroke=role_spec.fill,
                stroke_width=0.8,
                stroke_dasharray="2 2",
            )
            svg.text(
                role_spec.label,
                x=rx + rw / 2,
                y=ry + 24,
                text_anchor="middle",
                font_size=9,
                font_weight=700,
                fill=role_spec.label_color,
                opacity=0.7,
            )
        with svg.group(opacity=0):
            svg.animate("opacity", "0;0;1;1;0;0", f"0;{reveal_at - 0.0015:.4f};{reveal_at:.4f};0.916;0.95;1")
            svg.empty(
                "rect",
                width=SYLLABLE_SLOT_WIDTH,
                height=SYLLABLE_SLOT_HEIGHT,
                rx=6,
                fill=COLOR_SURFACE,
                stroke=blue.label_color,
                stroke_width=1.8,
                filter="url(#glow-blue)",
            )
            svg.text(
                syllable.char,
                x=SYLLABLE_SLOT_WIDTH / 2,
                y=62,
                text_anchor="middle",
                font_size=44,
                font_weight=900,
                fill=COLOR_TEXT,
            )
            svg.text(
                syllable.formula,
                x=SYLLABLE_SLOT_WIDTH / 2,
                y=86,
                text_anchor="middle",
                font_size=9,
                font_weight=700,
                fill=blue.stroke,
            )


def syllable_role_center(syllable, role):
    rx, ry, rw, rh = SYLLABLE_ROLE_BOXES[role]
    return (
        RIGHT_PANEL_X + syllable_slot_x(syllable) + rx + rw / 2,
        TOP_PANELS_Y + SYLLABLE_SLOT_Y + ry + rh / 2,
    )


def role_row_y(role):
    return DOCK_FIRST_ROW_Y + ROLE_ORDER.index(role) * DOCK_ROW_STEP


def dock_key_local_x(role, char):
    role_spec = JAMO_ROLES[role]
    gap = (KEY_AREA_WIDTH - role_spec.key_start_x - role_spec.key_width * len(role_spec.chars)) / (
        len(role_spec.chars) - 1
    )
    return role_spec.key_start_x + role_spec.chars.index(char) * (role_spec.key_width + gap)


def dock_key_center(role, char):
    role_spec = JAMO_ROLES[role]
    x = MARGIN + SECTION_INSET_X + DOCK_KEYS_X + dock_key_local_x(role, char) + role_spec.key_width / 2
    return x, DOCK_Y + role_row_y(role) + KEY_HEIGHT / 2


def highlight_times(role, char):
    flight = FLIGHT_BY_KEY.get((role, char))
    if flight is None:
        return None
    start = flight.start_fraction
    arrive = (flight.start_seconds + FLIGHT_TRAVEL_SECONDS) / ANIMATION_SECONDS
    return start - 0.0015, start, arrive, arrive + 0.001


def draw_flying_tiles(svg):
    for flight in FLIGHTS:
        source_x, source_y = dock_key_center(flight.role, flight.char)
        target_x, target_y = syllable_role_center(flight.syllable, flight.role)
        role_spec = JAMO_ROLES[flight.role]
        start = flight.start_fraction
        end = flight.end_fraction
        with svg.group(opacity=0):
            svg.animate("opacity", "0;0;1;1;0;0", f"0;{start - 0.001:.4f};{start:.4f};{end - 0.001:.4f};{end:.4f};1")
            arrive = (flight.start_seconds + FLIGHT_TRAVEL_SECONDS) / ANIMATION_SECONDS
            values = f"{source_x:.1f},{source_y:.1f}; {source_x:.1f},{source_y:.1f}; {target_x:.1f},{target_y:.1f}; {target_x:.1f},{target_y:.1f}; {source_x:.1f},{source_y:.1f}"
            key_times = f"0; {start:.4f}; {arrive:.4f}; {end:.4f}; 1"
            svg.animate_transform(values, key_times)
            svg.empty(
                "rect",
                x=-role_spec.flight_width / 2,
                y=-role_spec.flight_height / 2,
                width=role_spec.flight_width,
                height=role_spec.flight_height,
                rx=5,
                fill=role_spec.fill,
                stroke=role_spec.stroke,
                stroke_width=1.6,
                filter=f"url(#{role_spec.glow})",
            )
            svg.text(
                flight.char,
                x=0,
                y=6,
                text_anchor="middle",
                font_size=role_spec.flight_font_size,
                font_weight=900,
                fill=COLOR_TEXT,
            )


def draw_highlighted_key(svg, char, role, key_width, font_size):
    role_spec = JAMO_ROLES[role]
    times = highlight_times(role, char)
    if times is None:
        raise ValueError(f"No flight timing for highlighted key: {role} {char}")
    svg.open(
        "rect",
        width=key_width,
        height=KEY_HEIGHT,
        rx=4 if key_width > 18 else 3,
        fill=COLOR_SURFACE,
        stroke=COLOR_BORDER,
        stroke_width=1,
    )
    key_times = ";".join(("0", *(f"{t:.4f}" for t in times), "1"))
    svg.animate(
        "fill",
        f"{COLOR_SURFACE};{COLOR_SURFACE};{role_spec.fill};{role_spec.fill};{COLOR_SURFACE};{COLOR_SURFACE}",
        key_times,
    )
    svg.animate(
        "stroke",
        f"{COLOR_BORDER};{COLOR_BORDER};{role_spec.stroke};{role_spec.stroke};{COLOR_BORDER};{COLOR_BORDER}",
        key_times,
    )
    svg.animate("stroke-width", "1;1;2;2;1;1", key_times)
    svg.close("rect")
    svg.animated_text(
        char,
        [("fill", f"{COLOR_DIM};{COLOR_DIM};{COLOR_WHITE};{COLOR_WHITE};{COLOR_DIM};{COLOR_DIM}", key_times)],
        x=key_width / 2,
        y=15,
        text_anchor="middle",
        font_size=font_size,
        font_weight=700,
        fill=COLOR_DIM,
    )


def draw_plain_key(svg, char, role_spec):
    svg.empty(
        "rect",
        width=role_spec.key_width,
        height=KEY_HEIGHT,
        rx=4 if role_spec.key_width > 18 else 3,
        fill=COLOR_SURFACE,
        stroke=COLOR_DIVIDER,
    )
    svg.text(
        char,
        x=role_spec.key_width / 2,
        y=15,
        text_anchor="middle",
        font_size=role_spec.key_font_size,
        font_weight=600,
        fill=COLOR_MUTED,
    )


def draw_role_label(svg, role):
    role_spec = JAMO_ROLES[role]
    svg.empty(
        "rect",
        x=0,
        y=-1,
        width=DOCK_LABEL_WIDTH,
        height=KEY_HEIGHT,
        rx=4,
        fill=role_spec.fill,
        fill_opacity=0.15,
        stroke=role_spec.fill,
        stroke_width=0.8,
    )
    svg.text(
        f"{role_spec.label} ({len(role_spec.chars)})",
        x=DOCK_LABEL_WIDTH / 2,
        y=14,
        text_anchor="middle",
        font_size=9.5,
        font_weight=700,
        fill=role_spec.label_color,
    )


def draw_key_row(svg, role):
    role_spec = JAMO_ROLES[role]
    with svg.group(transform=f"translate({SECTION_INSET_X}, {role_row_y(role)})"):
        draw_role_label(svg, role)
        with svg.group(transform=f"translate({DOCK_KEYS_X}, 0)"):
            if role_spec.prefix_label is not None:
                svg.empty(
                    "rect",
                    width=role_spec.prefix_width,
                    height=KEY_HEIGHT,
                    rx=3,
                    fill=COLOR_SURFACE,
                    stroke=COLOR_DIVIDER,
                )
                svg.text(
                    role_spec.prefix_label,
                    x=role_spec.prefix_width / 2,
                    y=14,
                    text_anchor="middle",
                    font_size=9,
                    font_weight=700,
                    fill=COLOR_MUTED,
                )
            for char in role_spec.chars:
                x = dock_key_local_x(role, char)
                with svg.group(transform=f"translate({x:.1f}, 0)"):
                    if highlight_times(role, char) is not None:
                        draw_highlighted_key(svg, char, role, role_spec.key_width, role_spec.highlight_font_size)
                    else:
                        draw_plain_key(svg, char, role_spec)


def draw_jamo_dock(svg):
    with svg.group(transform=f"translate({MARGIN}, {DOCK_Y})"):
        draw_section_shell(svg, DOCK_HEIGHT)
        svg.text(
            f"{JAMO_SYMBOL_COUNT} POSITIONAL JAMO · REUSABLE ALPHABETIC COMPONENTS",
            x=18,
            y=20,
            font_size=11.5,
            font_weight=700,
            fill="#8b949e",
        )
        draw_section_divider(svg, 28)
        for role in ROLE_ORDER:
            draw_key_row(svg, role)


def _syllable_rows(start):
    return [
        "".join(chr(start + row * DENSE_COLUMN_COUNT + column) for column in range(DENSE_COLUMN_COUNT))
        for row in range(DENSE_ROW_COUNT)
    ]


def draw_dense_rows(svg, rows, start_y):
    with svg.group(
        font_family="monospace, 'Malgun Gothic', 'Noto Sans KR'", font_size=8.5, fill=COLOR_MUTED, opacity=0.65
    ):
        for row, content in enumerate(rows):
            svg.text(
                content,
                x=DENSE_TEXT_X,
                y=start_y + DENSE_ROW_STEP * row,
                textLength=DENSE_TEXT_LENGTH,
                lengthAdjust="spacing",
            )


def draw_dense_syllables(svg):
    visible_count = DENSE_ROW_COUNT * DENSE_COLUMN_COUNT
    upper = _syllable_rows(HANGUL_BASE)
    lower_start = HANGUL_BASE + HANGUL_SYLLABLE_COUNT - visible_count
    lower = _syllable_rows(lower_start)
    truncated_count = HANGUL_SYLLABLE_COUNT - 2 * visible_count
    with svg.group(transform=f"translate({SECTION_INSET_X}, {SCALE_BODY_Y})"):
        svg.empty(
            "rect",
            width=SCALE_MAIN_WIDTH,
            height=SCALE_BODY_HEIGHT,
            rx=6,
            fill=COLOR_SURFACE,
            fill_opacity=0.6,
            stroke=ALERT_FILL,
            stroke_width=0.8,
            stroke_opacity=0.4,
        )
        svg.empty("rect", x=8, y=7, width=220, height=17, rx=3, fill=ALERT_FILL, fill_opacity=0.15)
        svg.text(
            f"{HANGUL_SYLLABLE_COUNT:,} PRECOMPOSED SYLLABLE BLOCKS",
            x=14,
            y=19,
            font_size=9,
            font_weight=700,
            fill=ALERT_TEXT,
        )
        svg.text(
            f"Unicode U+{HANGUL_BASE:04X} ~ U+{HANGUL_BASE + HANGUL_SYLLABLE_COUNT - 1:04X}",
            x=SCALE_MAIN_WIDTH - SCALE_CARD_INSET,
            y=19,
            text_anchor="end",
            font_size=8.5,
            fill=COLOR_MUTED,
        )
        draw_dense_rows(svg, upper, DENSE_UPPER_Y)
        with svg.group(transform=f"translate({SCALE_CARD_INSET}, {DENSE_TRUNCATION_Y})"):
            svg.empty(
                "rect",
                width=SCALE_MAIN_INNER_WIDTH,
                height=DENSE_TRUNCATION_HEIGHT,
                rx=4,
                fill=COLOR_BG,
                stroke=COLOR_BORDER,
                stroke_width=0.8,
            )
            svg.text(
                f"··· [ {truncated_count:,} SYLLABLES TRUNCATED : ONE REGULAR COMPOSITION SPACE ] ···",
                x=SCALE_MAIN_INNER_WIDTH / 2,
                y=15,
                text_anchor="middle",
                font_size=9,
                font_weight=600,
                fill=COLOR_MUTED,
            )
        draw_dense_rows(svg, lower, DENSE_LOWER_Y)
        svg.empty(
            "rect",
            x=SCALE_CARD_INSET,
            y=246,
            width=SCALE_MAIN_INNER_WIDTH,
            height=26,
            rx=4,
            fill=COLOR_BG,
            stroke="#da3633",
            stroke_width=0.8,
        )
        svg.text(
            "Unicode precomposition is convenient; the Jamo structure remains algorithmically recoverable",
            x=SCALE_MAIN_CENTER_X,
            y=263,
            text_anchor="middle",
            font_size=9,
            font_weight=700,
            fill="#f85149",
        )


def build_hud_events():
    events = []
    for syllable in SYLLABLES:
        for role, char, seconds in syllable.injections:
            events.append((seconds, f"INJECT {char}", JAMO_ROLES[role].stroke, False))
        events.append(
            (syllable.assemble_seconds, f"ASSEMBLE → {syllable.char}", JAMO_ROLES["initial"].label_color, True)
        )
    events.append((COMPLETE_SECONDS, f"[OK] ✨ {SAMPLE_WORD} COMPLETE", JAMO_ROLES["final"].stroke, True))
    return tuple(events)


def draw_summary_and_hud(svg):
    blue = JAMO_ROLES["initial"]
    vowel = JAMO_ROLES["vowel"]
    green = JAMO_ROLES["final"]
    with svg.group(transform=f"translate({SCALE_ASIDE_X}, {SCALE_BODY_Y})"):
        svg.empty(
            "rect",
            width=SCALE_ASIDE_WIDTH,
            height=SCALE_SUMMARY_HEIGHT,
            rx=6,
            fill="url(#card-glow-blue)",
            stroke=blue.fill,
            stroke_width=1.2,
        )
        svg.empty(
            "rect",
            x=SCALE_ASIDE_INSET,
            y=6,
            width=SCALE_ASIDE_INNER_WIDTH,
            height=18,
            rx=3,
            fill=blue.fill,
            fill_opacity=0.2,
        )
        svg.text(
            f"{JAMO_SYMBOL_COUNT} POSITIONAL JAMO BASIS",
            x=SCALE_ASIDE_CENTER_X,
            y=18,
            text_anchor="middle",
            font_size=9,
            font_weight=800,
            fill=blue.label_color,
        )
        for index, role in enumerate(ROLE_ORDER):
            role_spec = JAMO_ROLES[role]
            count = len(role_spec.chars)
            y = 27 + 17 * index
            svg.empty(
                "rect",
                x=SCALE_ASIDE_INSET,
                y=y,
                width=SCALE_ASIDE_INNER_WIDTH,
                height=14,
                rx=3,
                fill=role_spec.fill,
                fill_opacity=0.15,
                stroke=role_spec.fill,
                stroke_width=0.8,
            )
            svg.text(
                f"{role_spec.label:<7}: {count:2d} SYMBOLS",
                x=13,
                y=y + 10.5,
                font_size=8.5,
                font_weight=700,
                fill=role_spec.stroke,
            )
            svg.text(
                f"{count / JAMO_SYMBOL_COUNT:.1%}",
                x=SCALE_ASIDE_RIGHT_TEXT_X,
                y=y + 10.5,
                text_anchor="end",
                font_size=8.5,
                font_weight=700,
                fill=COLOR_TEXT,
            )
        svg.empty(
            "rect",
            x=SCALE_ASIDE_INSET,
            y=81,
            width=SCALE_ASIDE_INNER_WIDTH,
            height=22,
            rx=4,
            fill=green.fill,
            fill_opacity=0.3,
            stroke=green.label_color,
        )
        svg.text(
            "REUSABLE STRUCTURAL BASIS",
            x=SCALE_ASIDE_CENTER_X,
            y=95,
            text_anchor="middle",
            font_size=9.5,
            font_weight=900,
            fill=green.stroke,
        )

        with svg.group(transform=f"translate(0, {SCALE_HUD_Y})"):
            svg.empty(
                "rect",
                width=SCALE_ASIDE_WIDTH,
                height=SCALE_HUD_HEIGHT,
                rx=6,
                fill=COLOR_PANEL,
                stroke=COLOR_BORDER,
                stroke_width=1.2,
            )
            svg.empty("rect", width=SCALE_ASIDE_WIDTH, height=20, rx=6, fill=COLOR_SURFACE)
            for cx, color in ((10, ALERT_DOT), (18, vowel.dot_color), (26, green.dot_color)):
                svg.empty("circle", cx=cx, cy=10, r=3, fill=color)
            svg.text(
                "LIVE KEYSTREAM HUD",
                x=100,
                y=14,
                text_anchor="middle",
                font_size=8.5,
                font_weight=700,
                fill=COLOR_MUTED,
            )
            with svg.group(font_family="monospace", font_size=8.2, transform="translate(8, 25)"):
                for index, (seconds, message, color, bold) in enumerate(build_hud_events()):
                    start = seconds / ANIMATION_SECONDS
                    with svg.group(opacity=0):
                        svg.animate("opacity", "0;0;1;1;0;0", f"0;{start - 0.001:.4f};{start:.4f};0.916;0.95;1")
                        svg.text(
                            f"> {seconds:0.1f}s: {message}",
                            x=0,
                            y=10 + 13.5 * index,
                            fill=color,
                            font_weight=900 if bold else 400,
                        )


def draw_scale_paradox(svg):
    with svg.group(transform=f"translate({MARGIN}, {SCALE_Y})"):
        draw_section_shell(svg, SCALE_HEIGHT)
        draw_section_header(
            svg,
            f"COMPOSITION SPACE : {HANGUL_SYLLABLE_COUNT:,} PRECOMPOSED BLOCKS FROM {JAMO_SYMBOL_COUNT} POSITIONAL JAMO",
            "#ff7b72",
            "#f85149",
        )
        draw_dense_syllables(svg)
        draw_summary_and_hud(svg)


def draw_showdown(svg):
    with svg.group(transform=f"translate({MARGIN}, {SHOWDOWN_Y})"):
        draw_section_shell(svg, SHOWDOWN_HEIGHT)
        draw_section_header(svg, "HANGUL COMPOSITIONAL BASIS", "#58a6ff", "#388bfd", 10.5)

        roles = (
            ("INITIAL", "19", "ᄒ", JAMO_ROLES["initial"].stroke),
            ("MEDIAL", "21", "ᅡ", JAMO_ROLES["vowel"].stroke),
            ("FINAL", "27 + ∅", "ᆫ", JAMO_ROLES["final"].stroke),
        )
        start_x = 30
        step_x = 138
        for index, (label, count, char, color) in enumerate(roles):
            x = start_x + index * step_x
            svg.text(label, x=x, y=51, font_size=8.5, font_weight=700, fill=COLOR_MUTED)
            svg.text(count, x=x, y=72, font_size=12, font_weight=900, fill=color)
            svg.text(char, x=x + 55, y=71, font_size=21, font_weight=900, fill=COLOR_TEXT)
            if index < 2:
                svg.text("+", x=x + 108, y=70, font_size=16, font_weight=900, fill=COLOR_MUTED)

        svg.text("→", x=445, y=70, font_size=18, font_weight=900, fill=COLOR_MUTED)
        svg.text("한", x=480, y=72, font_size=26, font_weight=900, fill=COLOR_WHITE)
        svg.text(
            f"{JAMO_SYMBOL_COUNT} positional Jamo  →  19 × 21 × 28  →  {HANGUL_SYLLABLE_COUNT:,} blocks",
            x=710,
            y=66,
            text_anchor="end",
            font_size=9.2,
            font_weight=700,
            fill="#79c0ff",
        )


def draw_footer(svg):
    with svg.group(transform=f"translate({MARGIN}, {FOOTER_Y})"):
        svg.empty(
            "rect",
            width=CONTENT_WIDTH,
            height=FOOTER_HEIGHT,
            rx=10,
            fill=COLOR_SURFACE,
            stroke="#1f6feb",
            stroke_width=1.2,
            filter="url(#glow-blue)",
        )
        svg.empty(
            "rect",
            x=FOOTER_INSET_X,
            y=19,
            width=FOOTER_BADGE_WIDTH,
            height=18,
            rx=9,
            fill="#1f6feb",
            fill_opacity=0.2,
            stroke="#388bfd",
            stroke_width=0.8,
        )
        svg.text(
            "💡 KEY POINT",
            x=FOOTER_BADGE_CENTER_X,
            y=32,
            text_anchor="middle",
            font_size=9.5,
            font_weight=800,
            fill="#79c0ff",
        )
        svg.text(
            "Hangul combines alphabetic Jamo with systematic 2D syllable-block assembly.",
            x=FOOTER_TITLE_X,
            y=32,
            font_size=12,
            font_weight=700,
            fill=COLOR_TEXT,
        )
        svg.text(
            "Research question: can explicit structure coexist with strong compression?",
            x=FOOTER_INSET_X,
            y=55,
            font_size=10.5,
            fill=COLOR_SUBTLE,
        )
        svg.text(
            "github.com/nicezic/KOREAN-tokenizer",
            x=FOOTER_RIGHT_X,
            y=55,
            text_anchor="end",
            font_size=8.5,
            font_weight=700,
            fill="#58a6ff",
        )


def build_svg():
    svg = Svg()
    svg.open(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        viewBox=f"0 0 {WIDTH} {HEIGHT}",
        width="100%",
        height="100%",
        font_family="system-ui, -apple-system, 'Segoe UI', Roboto, 'Noto Sans KR', 'Malgun Gothic', sans-serif",
    )
    draw_defs(svg)
    draw_header(svg)
    draw_top_panels(svg)
    draw_flying_tiles(svg)
    draw_jamo_dock(svg)
    draw_scale_paradox(svg)
    draw_showdown(svg)
    draw_footer(svg)
    svg.close("svg")
    return svg.render()


def write_output(svg):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(svg, encoding="utf-8")


def output_is_stale(svg):
    return not OUTPUT_PATH.exists() or OUTPUT_PATH.read_text(encoding="utf-8") != svg


def main():
    parser = argparse.ArgumentParser(description="Generate the Hangul Jamo SVG used by the README.")
    parser.add_argument(
        "--check", action="store_true", help="Exit non-zero when generated SVG output is missing or stale."
    )
    args = parser.parse_args()

    svg = build_svg()
    if args.check:
        if output_is_stale(svg):
            print(f"stale: {OUTPUT_PATH.relative_to(REPO_ROOT)}")
            raise SystemExit(1)
        print("hangul-jamo.svg is up to date")
        return

    write_output(svg)
    print(OUTPUT_PATH.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
