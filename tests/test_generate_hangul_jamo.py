import xml.etree.ElementTree as ET

from generate_hangul_jamo import (
    CONTENT_WIDTH,
    DOCK_Y,
    FOOTER_INSET_X,
    FOOTER_RIGHT_X,
    JAMO_ROLES,
    OUTPUT_PATH,
    PANEL_INSET_X,
    ROLE_ORDER,
    SCALE_BODY_HEIGHT,
    SCALE_HUD_HEIGHT,
    SCALE_HUD_Y,
    SECTION_GAP,
    SHOWDOWN_CARD_CENTER_Y,
    SHOWDOWN_CARD_HEIGHT,
    SHOWDOWN_CARD_Y,
    SYLLABLE_BOX_INSET,
    SYLLABLE_FINAL_BOX_WIDTH,
    SYLLABLE_ROLE_BOXES,
    SYLLABLE_SLOT_WIDTH,
    SYLLABLES,
    TOP_ITEM_GAP,
    TOP_PANELS_HEIGHT,
    TOP_PANELS_Y,
    build_hud_events,
    build_svg,
    syllable_slot_x,
)


def test_build_svg_is_valid_and_named():
    svg = build_svg()
    root = ET.fromstring(svg)

    assert root.tag.endswith("svg")
    assert OUTPUT_PATH.name == "hangul-jamo.svg"
    assert "'Segoe UI'" in svg
    assert "&#x27;" not in svg


def test_layout_relations_are_derived():
    assert DOCK_Y == TOP_PANELS_Y + TOP_PANELS_HEIGHT + SECTION_GAP
    assert SCALE_HUD_Y + SCALE_HUD_HEIGHT == SCALE_BODY_HEIGHT
    assert SHOWDOWN_CARD_CENTER_Y == SHOWDOWN_CARD_Y + SHOWDOWN_CARD_HEIGHT / 2
    assert FOOTER_RIGHT_X == CONTENT_WIDTH - FOOTER_INSET_X

    assert syllable_slot_x(SYLLABLES[0]) == PANEL_INSET_X
    assert syllable_slot_x(SYLLABLES[1]) == PANEL_INSET_X + SYLLABLE_SLOT_WIDTH + TOP_ITEM_GAP
    assert SYLLABLE_ROLE_BOXES["initial"][2] == SYLLABLE_ROLE_BOXES["vowel"][2]
    assert SYLLABLE_FINAL_BOX_WIDTH == SYLLABLE_SLOT_WIDTH - 2 * SYLLABLE_BOX_INSET


def test_role_order_and_hud_scenario_have_single_sources():
    events = build_hud_events()

    assert ROLE_ORDER == tuple(JAMO_ROLES)
    assert len(events) == 9
    assert [event[0] for event in events] == sorted(event[0] for event in events)
    assert [event[1] for event in events[:3]] == ["INJECT ㅎ", "INJECT ㅏ", "INJECT ㄴ"]
    assert events[-1][1] == "[OK] ✨ 한글 COMPLETE"
