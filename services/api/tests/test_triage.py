"""Report AI v1 rules — core cases. M4 adds the 60+ sample suite (ml/report_ai/tests/samples.jsonl)."""

import pytest

from app.config import get_settings
from app.geo.static import load_geography
from app.reports.triage import analyze_report, detect_language, has_term

GEO = load_geography(get_settings().seed_dir)


def run(text):
    return analyze_report(text, GEO.place_names, GEO.aliases)


def test_prd_example():
    t = run(
        "Rushikulya water entered our village near Purushottampur, waist deep, 30 families stuck on roof. "
        "Need boat"
    )
    assert t.place == "purushottampur"
    assert "flood" in t.hazards
    assert "rescue" in t.needs
    assert t.people_count == 120
    assert t.severity == 5
    assert t.language == "en"
    assert t.confidence == 0.95  # 0.35 + 0.2 place + 0.15*2 hazards (flood, wind via "roof") + 0.1*1 need


@pytest.mark.parametrize(
    "text,place",
    [
        ("Water near Gopalpur beach", "rangeilunda"),
        ("Berhampur roads flooded", "kukudakhandi"),
        ("Brahmapur bus stand under water", "kukudakhandi"),
        ("Chatrapur tree fell", "chhatrapur"),
        ("flood at rushikulya mouth", "ganjam"),
        ("Khalikote huts collapsed", "khallikote"),
        ("Hinjili canal overflow", "hinjilicut"),
        ("ପୁରୁଷୋତ୍ତମପୁର ରେ ବନ୍ୟା", "purushottampur"),
        ("no place here, just rain", None),
    ],
)
def test_place_extraction(text, place):
    assert run(text).place == place


def test_short_stems_need_whole_words():
    assert not has_term("polasara fields", "pole")
    assert has_term("electric pole down", "pole")
    assert has_term("poles down", "pole")
    assert has_term("inundated", "inundat")
    t = run("Polasara fields submerged")
    assert t.hazards == ["flood"]


def test_languages():
    assert detect_language("ସାନଖେମୁଣ୍ଡି ଗାଁରେ ବନ୍ୟା") == "or"
    assert detect_language("गांव में बाढ़ आ गई") == "hi"
    assert detect_language("Aska mein paani bhar gaya, 20 log fase hain, bachao") == "hi"
    assert detect_language("Sanakhemundi re bonya pani") == "or"
    assert detect_language("Road blocked by fallen tree") == "en"


def test_severity_rules():
    assert run("nothing much").severity == 1
    assert run("some water on the road").severity == 2
    assert run("water knee deep").severity == 3
    assert run("water waist deep").severity == 4
    assert run("water chest deep").severity == 5
    assert run("bridge washed away, village cut off").severity >= 4
    assert run("two people injured").severity >= 4
    assert run("water knee deep, 5 people").severity == 4  # +1 for people count


def test_hindi_devanagari_and_needs():
    t = run("पानी घर में, बाढ़ है")
    assert t.hazards == ["flood"]
    t = run("Aska mein paani bhar gaya, 20 log fase hain, bachao")
    assert t.place == "aska"
    assert t.people_count == 20
    assert "rescue" in t.needs
