"""Network checks of the model catalog. Skipped unless pytest runs with --network:

    env/python.exe -m pytest --network tests/test_model_links.py

tools/check_model_links.py prints the same information as a detailed report.
"""

import tempfile
import warnings
from pathlib import Path

import pytest

from tools.check_model_links import build_report, load_catalog, summarize
from tools.sync_models import supported_models

pytestmark = pytest.mark.network


@pytest.fixture(scope="module")
def report():
    return build_report(load_catalog())


def test_every_catalog_link_downloads(report):
    broken = [
        f"{entry['id']} ({source}): {link['url']} -> {link['status'] or link['error']}"
        for entry in report
        for source, links in entry["sources"].items()
        for link in links
        if not link["ok"]
    ]
    assert not broken, "Broken download links:\n" + "\n".join(broken)


def test_models_missing_from_the_mirror_are_reported(report):
    pending = [e["id"] for e in report if summarize(e).get("mirror") == "not uploaded"]
    uploaded = [e["id"] for e in report if summarize(e).get("mirror") == "uploaded"]
    if pending:
        warnings.warn(f"{len(pending)} model(s) not on the Hugging Face mirror yet: {', '.join(pending)}")
    # Uploaded but still without a Hugging Face source: tools/sync_models.py --write adds it
    assert not uploaded, f"Run tools/sync_models.py --write to add the mirror of: {', '.join(uploaded)}"


def test_catalog_has_every_audio_separator_model():
    pytest.importorskip("audio_separator")
    catalog = {m["filename"] for m in load_catalog()}
    with tempfile.TemporaryDirectory() as tmp:
        missing = [f"{m['name']} ({m['filename']})" for m in supported_models(Path(tmp)) if m["filename"] not in catalog]
    assert not missing, "Run tools/sync_models.py --write to add:\n" + "\n".join(missing)
