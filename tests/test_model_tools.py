"""Offline tests of tools/check_model_links.py and tools/sync_models.py (no network: links are faked)."""

from tools.check_model_links import (
    GITHUB_MODEL_CONFIGS, HF_MIRROR, LinkResult, build_report, huggingface_urls, model_files, print_report, summarize,
)
from tools.sync_models import arch_for, id_for, plan, working_sources

GH = GITHUB_MODEL_CONFIGS


def fake_checker(working: set[str]):
    return lambda url: LinkResult(url, url in working, 200 if url in working else 404)


def roformer(filename, sources=None, model_id=None):
    return {"id": model_id or filename, "arch": "roformer", "filename": filename, "sources": sources or {}}


def test_files_and_mirror_paths():
    model = roformer("a b.ckpt", {"github": [f"{GH}/a%20b.ckpt", f"{GH}/a.yaml"]})
    assert model_files(model) == ["a%20b.ckpt", "a.yaml"]
    assert huggingface_urls({"arch": "mdxnet"}, ["x.onnx"]) == [f"{HF_MIRROR}/mdx-net/x.onnx"]
    assert huggingface_urls({"arch": "vrarch"}, ["1 x.pth"]) == [f"{HF_MIRROR}/vr-arch/1%20x.pth"]
    assert huggingface_urls({"arch": "demucs"}, ["x.yaml"]) == []
    assert huggingface_urls(roformer("none.ckpt")) == []


def test_report(capsys):
    ok = roformer("ok.ckpt", {"github": [f"{GH}/ok.ckpt"], "huggingface": [f"{HF_MIRROR}/roformers/ok.ckpt"]})
    broken = roformer("broken.ckpt", {"github": [f"{GH}/broken.ckpt"], "huggingface": [f"{HF_MIRROR}/roformers/broken.ckpt"]})
    pending = roformer("pending.ckpt", {"github": [f"{GH}/pending.ckpt", f"{GH}/shared.yaml"]})
    uploaded = roformer("up.ckpt", {"github": [f"{GH}/up.ckpt"]})
    working = {f"{GH}/ok.ckpt", f"{HF_MIRROR}/roformers/ok.ckpt", f"{GH}/broken.ckpt", f"{GH}/pending.ckpt",
               f"{GH}/shared.yaml", f"{HF_MIRROR}/roformers/shared.yaml", f"{GH}/up.ckpt", f"{HF_MIRROR}/roformers/up.ckpt"}

    report = build_report([ok, broken, pending, uploaded], checker=fake_checker(working), workers=2)

    assert [summarize(e) for e in report] == [
        {"github": "ok", "huggingface": "ok"},
        {"github": "ok", "huggingface": "broken"},
        {"github": "ok", "huggingface": "none", "mirror": "not uploaded"},
        {"github": "ok", "huggingface": "none", "mirror": "uploaded"},
    ]
    assert print_report(report) == 1
    out = capsys.readouterr().out
    assert "ok.ckpt]" not in out  # working models are only listed with --verbose
    assert f"BROKEN 404" in out and "NOT on the mirror" in out and "run tools/sync_models.py --write" in out


def test_arch_and_id():
    assert arch_for("MDXC", "Roformer Model: BS Roformer | Karaoke by anvuew") == "roformer"
    assert arch_for("MDXC", "MDX23C Model: MDX23C-InstVoc HQ") == "mdx23c"
    assert (arch_for("MDX", "x"), arch_for("VR", "x"), arch_for("Demucs", "x")) == ("mdxnet", "vrarch", "demucs")
    assert id_for("roformer", "Roformer Model: BS Roformer | Karaoke by anvuew", "f.ckpt") == "BS Roformer | Karaoke by anvuew"
    assert id_for("mdxnet", "MDX-Net Model: UVR-MDX-NET Inst HQ 3", "UVR-MDX-NET-Inst_HQ_3.onnx") == "UVR-MDX-NET-Inst_HQ_3.onnx"


def test_working_sources():
    files = ["m.ckpt", "m.yaml"]
    uvr_yaml = "https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/mdx_model_data/mdx_c_configs/m.yaml"
    checker = fake_checker({f"{GH}/m.ckpt", uvr_yaml, f"{HF_MIRROR}/roformers/m.ckpt"})
    # GitHub falls back to UVR's repo; Hugging Face is left out until every file is on the mirror
    assert working_sources("roformer", files, checker) == {"github": [f"{GH}/m.ckpt", uvr_yaml]}
    assert working_sources("roformer", files, fake_checker(set())) == {}
    assert working_sources("demucs", ["https://dl.fbaipublicfiles.com/x.th", "x.yaml"], checker) == {}


def test_plan_inserts_after_upstream_predecessor_and_fills_sources():
    catalog = [
        roformer("a.ckpt", {"github": [f"{GH}/a.ckpt"], "huggingface": [f"{HF_MIRROR}/roformers/a.ckpt"]}),
        roformer("c.ckpt", {"github": [f"{GH}/c.ckpt"]}),
        roformer("sw.ckpt"),
        {"id": "x.onnx", "arch": "mdxnet", "filename": "x.onnx", "sources": {}},
    ]
    upstream = [
        {"name": "Roformer Model: A", "type": "MDXC", "filename": "a.ckpt", "files": ["a.ckpt"]},
        {"name": "Roformer Model: New B", "type": "MDXC", "filename": "b.ckpt", "files": ["b.ckpt"]},
        {"name": "Roformer Model: C", "type": "MDXC", "filename": "c.ckpt", "files": ["c.ckpt"]},
        {"name": "Roformer Model: SW", "type": "MDXC", "filename": "sw.ckpt", "files": ["sw.ckpt"]},
        {"name": "MDX-Net Model: Y", "type": "MDX", "filename": "y.onnx", "files": ["y.onnx"]},
    ]
    working = {f"{GH}/b.ckpt", f"{HF_MIRROR}/roformers/b.ckpt", f"{HF_MIRROR}/roformers/c.ckpt", f"{GH}/sw.ckpt",
               f"{GH}/y.onnx"}

    models, changes = plan(catalog, upstream, fake_checker(working))

    assert [m["filename"] for m in models] == ["a.ckpt", "b.ckpt", "c.ckpt", "sw.ckpt", "x.onnx", "y.onnx"]
    assert models[1] == {"id": "New B", "arch": "roformer", "filename": "b.ckpt",
                         "sources": {"github": [f"{GH}/b.ckpt"], "huggingface": [f"{HF_MIRROR}/roformers/b.ckpt"]}}
    assert models[2]["sources"]["huggingface"] == [f"{HF_MIRROR}/roformers/c.ckpt"]
    assert models[3]["sources"] == {"github": [f"{GH}/sw.ckpt"]}
    assert models[5]["sources"] == {"github": [f"{GH}/y.onnx"]}
    assert changes == [
        "fill huggingface of [roformer] c.ckpt",
        "fill github of [roformer] sw.ckpt",
        "add [roformer] New B",
        "add [mdxnet] y.onnx (no huggingface source yet)",
    ]
    assert catalog[1]["sources"] == {"github": [f"{GH}/c.ckpt"]}  # the input is not modified
    assert plan(models, upstream, fake_checker(working))[1] == []
