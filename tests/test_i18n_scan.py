import ast
import json
import re

import pytest

from tools import i18n_scan

LANGUAGE_FILES = sorted(i18n_scan.LANG_DIR.glob("*.json"))
PLACEHOLDER = re.compile(r"\{[^{}]*\}")


def test_every_key_used_in_code_exists_in_en_us():
    assert i18n_scan.main(["--check"]) == 0


def test_extract_keys_finds_i18n_and_marker_calls():
    tree = ast.parse('i18n("A")\nN_("B")\nother("C")\ni18n(variable)\nx = f"{i18n(\'D\')}"\n')
    assert i18n_scan.extract_keys(tree) == {"A", "B", "D"}


def test_language_file_names_use_underscores():
    for path in LANGUAGE_FILES:
        assert re.fullmatch(r"[a-z]{2}_[A-Z]{2}", path.stem), path.name


@pytest.fixture(scope="module")
def code_keys():
    return i18n_scan.scan()


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_file_is_a_dict_of_strings(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    bad = [key for key, value in data.items() if not isinstance(value, str) or not value.strip()]
    assert not bad, f"{path.name} has empty or non-string values: {bad}"


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_has_every_key(path, code_keys):
    missing = sorted(code_keys - set(i18n_scan.load_language(path)))
    assert not missing, f"{path.name} is missing {len(missing)} keys:\n" + "\n".join(missing)


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_has_no_unknown_keys(path, code_keys):
    unknown = sorted(set(i18n_scan.load_language(path)) - code_keys)
    assert not unknown, f"{path.name} has keys not used in code (typo or stale):\n" + "\n".join(unknown)


@pytest.mark.parametrize("path", LANGUAGE_FILES, ids=lambda p: p.stem)
def test_language_placeholders_match(path):
    # The translated text goes through str.format(), so it must keep the same {placeholders}
    wrong = {
        key: value
        for key, value in i18n_scan.load_language(path).items()
        if sorted(PLACEHOLDER.findall(key)) != sorted(PLACEHOLDER.findall(value))
    }
    assert not wrong, f"{path.name} changes the placeholders of: {wrong}"
