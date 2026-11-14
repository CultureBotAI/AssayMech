"""Offline adversarial checks for issues #6/#9/#10; no historical helper is imported."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts/adhoc/repository-freshness-closeout-20261113/verify_release.py"
spec = importlib.util.spec_from_file_location("assay_release_verification", HELPER)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
V = verifier
BASE = "a" * 40
HEAD = "b" * 40
TREE = "c" * 40


class FakeGit:
    def __init__(self, root=None):
        self.root = root
        self.blobs = {}
        self.texts = {}
        self.entries = {}
        self.objects = {}
        self.ancestry = True

    def blob(self, commit, path):
        return self.blobs[commit, path]

    def text(self, *args):
        return self.texts[args]

    def first_parent_contains(self, main, commit):
        return self.ancestry

    def tree(self, commit):
        return self.entries

    def raw(self, *args):
        assert args[:2] == ("cat-file", "blob")
        return self.objects[args[2]]


class FakeAPI:
    def __init__(self):
        self.values = {}
        self.asset_rows = []
        self.asset_bytes = b""
        self.calls = []

    def get(self, endpoint):
        self.calls.append(endpoint)
        return copy.deepcopy(self.values[endpoint])

    def assets(self, release_id):
        return copy.deepcopy(self.asset_rows)

    def raw(self, endpoint, *, binary=False):
        assert binary
        return self.asset_bytes


@pytest.fixture
def publication(monkeypatch):
    git, api = FakeGit(), FakeAPI()
    for path in V.PAYLOADS:
        content = V.encoded(V.POLICY) if path == V.DECLARATION else (path + "\n").encode()
        git.blobs[V.RELEASE_COMMIT, path] = ("100644", content)
    audit = {
        "declaration": V.POLICY, "kind": "verified_freshness_release_source",
        "source_commit": V.RELEASE_COMMIT, "reviewed_head": V.REVIEWED_HEAD,
        "reviewed_base": BASE, "source_tree": TREE, "observed_main": HEAD,
        "installed": False, "adopted": False, "release_immutability_claimed": False,
        "tag_protection_claimed": False, "merged_at": "2026-11-10T11:13:16Z",
        "payloads": {
            path: {"mode": mode, "bytes": len(raw), "sha256": V.sha256(raw)}
            for (_, path), (mode, raw) in git.blobs.items()
        },
    }
    api.asset_bytes = V.encoded(audit)
    monkeypatch.setattr(V, "AUDIT_SHA256", V.sha256(api.asset_bytes))
    api.asset_rows = [{"name": "release-audit.json", "id": 2,
                       "size": len(api.asset_bytes), "digest": "sha256:" + V.AUDIT_SHA256}]
    api.values[f"repos/{V.CANONICAL}/git/ref/tags/{V.TAG}"] = {
        "object": {"type": "commit", "sha": V.RELEASE_COMMIT}}
    api.values[f"repos/{V.CANONICAL}/releases/tags/{V.TAG}"] = {
        "tag_name": V.TAG, "draft": False, "prerelease": False,
        "published_at": "2026-11-10T22:32:19Z", "target_commitish": V.RELEASE_COMMIT,
        "html_url": f"https://github.com/{V.CANONICAL}/releases/tag/{V.TAG}", "id": 1,
    }
    api.values[f"repos/{V.CANONICAL}/commits/main"] = {"sha": HEAD}
    for number, merge, head in [(1128, V.RELEASE_COMMIT, V.REVIEWED_HEAD),
                                (1165, V.NATIVE_COMMIT, V.NATIVE_HEAD)]:
        api.values[f"repos/{V.CANONICAL}/pulls/{number}"] = {
            "number": number, "state": "closed", "merged": True,
            "merged_at": "2026-11-10T11:13:16Z", "merge_commit_sha": merge,
            "head": {"sha": head, "repo": {"full_name": V.CANONICAL}},
            "base": {"ref": "main", "repo": {"full_name": V.CANONICAL}},
        }
    git.texts["rev-parse", V.RELEASE_COMMIT + "^{tree}"] = TREE
    git.texts["rev-list", "--parents", "-n", "1", V.RELEASE_COMMIT] = (
        V.RELEASE_COMMIT + " " + BASE)
    return git, api


def test_publication_checks_all_payloads_and_merged_native_dependency(publication):
    git, api = publication
    result = V.verify_publication(git, api)
    assert len(result["payloads"]) == 18
    assert result["native_pr"]["merge_commit"] == V.NATIVE_COMMIT
    assert result["source_commit"] == V.RELEASE_COMMIT
    assert result["tag_protection_claimed"] is False
    assert result["release_immutability_claimed"] is False


def test_downloaded_asset_tampering_is_rejected(publication):
    git, api = publication
    changed = V.strict_json(api.asset_bytes)
    changed["observation_notes"] = "tampered asset"
    api.asset_bytes = V.encoded(changed)
    api.asset_rows[0]["size"] = len(api.asset_bytes)
    api.asset_rows[0]["digest"] = "sha256:" + V.sha256(api.asset_bytes)
    with pytest.raises(V.VerificationError, match="downloaded release audit digest"):
        V.verify_publication(git, api)


def test_release_schema_git_blob_tampering_is_rejected(publication):
    git, api = publication
    git.blobs[V.RELEASE_COMMIT, V.SOURCES["schema.yaml"]] = ("100644", b"changed\n")
    with pytest.raises(V.VerificationError, match="release payload differs"):
        V.verify_publication(git, api)


def test_false_tag_is_rejected(publication):
    git, api = publication
    api.values[f"repos/{V.CANONICAL}/git/ref/tags/{V.TAG}"]["object"]["sha"] = HEAD
    with pytest.raises(V.VerificationError, match="release tag differs"):
        V.verify_publication(git, api)


def test_wrong_source_repository_is_rejected(publication):
    git, api = publication
    api.values[f"repos/{V.CANONICAL}/pulls/1128"]["head"]["repo"]["full_name"] = "fork/claw"
    with pytest.raises(V.VerificationError, match="PR identity differs"):
        V.verify_publication(git, api)


def test_false_full_source_tree_is_rejected(publication):
    git, api = publication
    git.texts["rev-parse", V.RELEASE_COMMIT + "^{tree}"] = BASE
    with pytest.raises(V.VerificationError, match="source tree differs"):
        V.verify_publication(git, api)


def test_native_merge_must_be_ancestor_of_current_main(publication):
    git, api = publication
    git.first_parent_contains = lambda main, commit: commit != V.NATIVE_COMMIT
    with pytest.raises(V.VerificationError, match="dependency absent"):
        V.verify_publication(git, api)


def test_asset_inventory_change_during_readback_is_rejected(publication):
    git, api = publication
    rows = copy.deepcopy(api.asset_rows)
    observations = iter([rows, []])
    api.assets = lambda release_id: next(observations)
    with pytest.raises(V.VerificationError, match="observations changed"):
        V.verify_publication(git, api)


def test_wrong_git_identity_is_rejected():
    with pytest.raises(V.VerificationError, match="origin identity differs"):
        V.valid_identity("https://github.com/other/AssayMech.git", V.CONSUMER)


@pytest.fixture
def candidate(tmp_path):
    repository, canonical = FakeGit(tmp_path), FakeGit()
    source_values = {
        V.SOURCES["contract.yaml"]: b"candidate_authority: proposal_only\n",
        V.SOURCES["schema.yaml"]: b"name: repository_freshness\n",
        V.SOURCES["SKILL.md"]: b"{{ display_name }} in {{ github }}\n",
    }
    for path, raw in source_values.items():
        for commit in (V.HISTORICAL_SOURCE, V.RELEASE_COMMIT):
            canonical.blobs[commit, path] = ("100644", raw)
    canonical.texts["rev-parse", V.HISTORICAL_SOURCE + "^{tree}"] = TREE
    proposal = {
        "authority": "proposal_only", "installed": False, "adopted": False,
        "state": "blocked_on_canonical_release", "github_repository": V.CONSUMER,
        "canonical_source": {
            "released": False, "repository": V.CANONICAL,
            "reviewed_source_commit": V.HISTORICAL_SOURCE,
        },
    }
    candidate_bytes = {"proposal.json": V.encoded(proposal)}
    for name, path in V.SOURCES.items():
        candidate_bytes[name] = source_values[path].replace(
            b"{{ display_name }}", b"AssayMech").replace(b"{{ github }}", V.CONSUMER.encode())
    helpers = {name: b"# archival fixture; must not execute\n" for name in (
        "prepare_consumer.py", "verify_candidate.py", "final_inventory.py")}
    provenance = {
        "repository": V.CONSUMER,
        "canonical_source": {"source_commit": V.HISTORICAL_SOURCE, "source_tree": TREE,
                             "source_sha256": {p: V.sha256(b) for p, b in source_values.items()}},
        "candidate_sha256": {p: V.sha256(b) for p, b in candidate_bytes.items()},
        "original_helpers_sha256": {p: V.sha256(b) for p, b in helpers.items()},
    }
    files = {V.CANDIDATE + "/" + p: b for p, b in candidate_bytes.items()}
    files.update({V.ARCHIVE + "/" + p: b for p, b in helpers.items()})
    files[V.ARCHIVE + "/provenance.json"] = V.encoded(provenance)
    for path, raw in files.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        repository.blobs[V.ARCHIVE_HEAD, path] = ("100644", raw)
    return repository, canonical


def test_candidate_receipt_preserves_original_unreleased_state(candidate):
    repository, canonical = candidate
    before = (repository.root / V.CANDIDATE / "proposal.json").read_bytes()
    result = V.verify_candidate(repository, canonical)
    assert result["proposal_state_preserved"] == "blocked_on_canonical_release"
    assert result["proposal_released_preserved"] is False
    assert (repository.root / V.CANDIDATE / "proposal.json").read_bytes() == before


@pytest.mark.parametrize("name", ["schema.yaml", "proposal.json", "SKILL.md"])
def test_changed_candidate_rejected_before_receipt(candidate, name):
    repository, canonical = candidate
    (repository.root / V.CANDIDATE / name).write_bytes(b"tampered\n")
    with pytest.raises(V.VerificationError, match="historical candidate changed"):
        V.verify_candidate(repository, canonical)


def test_hidden_extra_candidate_file_is_rejected(candidate):
    repository, canonical = candidate
    (repository.root / V.CANDIDATE / ".ignored").write_bytes(b"extra")
    with pytest.raises(V.VerificationError, match="inventory differs"):
        V.verify_candidate(repository, canonical)


def test_changed_historical_provenance_is_rejected(candidate):
    repository, canonical = candidate
    path = repository.root / V.ARCHIVE / "provenance.json"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(V.VerificationError, match="provenance bytes changed"):
        V.verify_candidate(repository, canonical)


@pytest.fixture
def baseline(tmp_path):
    repository, api = FakeGit(tmp_path), FakeAPI()
    for i, path in enumerate(["data/assays/seed.yaml", "src/schema.yaml",
                              "scripts/.vendored_canon_ref", "uv.lock"]):
        raw = (path + "\n").encode()
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        object_id = f"{i:040x}"
        repository.entries[path] = ("100644", object_id)
        repository.objects[object_id] = raw
    repository.texts["rev-parse", "HEAD"] = HEAD
    repository.texts["merge-base", BASE, HEAD] = BASE
    repository.texts["rev-parse", BASE + "^{tree}"] = TREE
    api.values[f"repos/{V.CONSUMER}/commits/main"] = {"sha": BASE}
    return repository, api


def test_all_published_main_blobs_are_compared(baseline):
    repository, api = baseline
    result = V.verify_main_preserved(repository, api, BASE)
    assert result["file_count"] == 4
    assert result["all_main_blobs_and_modes_preserved"] is True
    assert result["active_paths_sha256"]["workflow/mech-workflow.yaml"] is None


@pytest.mark.parametrize("path", ["data/assays/seed.yaml", "src/schema.yaml", "uv.lock"])
def test_modified_main_data_schema_or_dependency_rejected(baseline, path):
    repository, api = baseline
    (repository.root / path).write_bytes(b"changed\n")
    with pytest.raises(V.VerificationError, match="published main file changed"):
        V.verify_main_preserved(repository, api, BASE)


def test_ignored_active_workflow_is_rejected(baseline):
    repository, api = baseline
    path = repository.root / "workflow/mech-workflow.yaml"
    path.parent.mkdir()
    path.write_bytes(b"installed: true\n")
    with pytest.raises(V.VerificationError, match="new active workflow"):
        V.verify_main_preserved(repository, api, BASE)


def test_runtime_authority_is_not_added(monkeypatch):
    monkeypatch.setattr(V, "verify_publication", lambda *args: {"proof": "fixture"})
    monkeypatch.setattr(V, "verify_candidate", lambda *args: {"proposal_released_preserved": False})
    monkeypatch.setattr(V, "verify_main_preserved", lambda *args: {"preserved": True})
    receipt = V.verify(None, None, None, BASE)
    assert receipt["authority"] == "verification_only"
    assert receipt["installed"] is False
    assert receipt["adopted"] is False
    assert receipt["runtime_authority_granted"] is False
    assert "separate approved immutable boundary adoption" in receipt["remaining_requirements"]
    assert receipt["helper_sha256"] == V.sha256(HELPER.read_bytes())


def test_receipt_is_exclusive_and_cannot_target_candidate_or_canonical(tmp_path):
    repository, canonical = tmp_path / "consumer", tmp_path / "canonical"
    repository.mkdir()
    canonical.mkdir()
    output = tmp_path / "receipt.json"
    V.write_receipt(output, {"authority": "verification_only"}, repository, canonical)
    saved = output.read_bytes()
    with pytest.raises(V.VerificationError, match="already exists"):
        V.write_receipt(output, {}, repository, canonical)
    assert output.read_bytes() == saved
    for invalid in [repository / V.CANDIDATE / "extra.json", canonical / "extra.json"]:
        with pytest.raises(V.VerificationError):
            V.write_receipt(invalid, {}, repository, canonical)
        assert not invalid.exists()


def test_json_duplicate_keys_are_rejected():
    with pytest.raises(V.VerificationError, match="duplicate JSON key"):
        V.strict_json(b'{"installed": false, "installed": true}')


def test_cli_failure_is_nonzero_and_writes_nothing(tmp_path, capsys):
    output = tmp_path / "receipt.json"
    result = V.main(["--repository-root", str(tmp_path), "--canonical-root", str(tmp_path),
                     "--base-commit", BASE, "--output", str(output)])
    assert result == 1
    assert json.loads(capsys.readouterr().out)["status"] == "hold"
    assert not output.exists()


def test_committed_receipt_binds_helper_candidates_and_runtime_hold():
    receipt = V.strict_json((ROOT / V.CLOSEOUT / "verification.json").read_bytes())
    assert receipt["helper_sha256"] == V.sha256(HELPER.read_bytes())
    assert receipt["canonical_publication"]["audit_sha256"] == V.AUDIT_SHA256
    assert receipt["canonical_publication"]["source_commit"] == V.RELEASE_COMMIT
    assert set(receipt["canonical_publication"]["payloads"]) == set(V.PAYLOADS)
    for name, expected in receipt["historical_candidate"]["candidate_sha256"].items():
        assert V.sha256((ROOT / V.CANDIDATE / name).read_bytes()) == expected
    assert receipt["installed"] is False
    assert receipt["adopted"] is False
    assert receipt["runtime_authority_granted"] is False


@pytest.mark.parametrize(("guard", "replacement", "test"), [
    ("obj.get(\"type\") == \"commit\" and obj.get(\"sha\") == RELEASE_COMMIT",
     "True", "test_false_tag_is_rejected"),
    ("sha256(raw) == AUDIT_SHA256", "True",
     "test_downloaded_asset_tampering_is_rejected"),
    ("require(disk_entry(repository.root, path) == (mode, raw),",
     "require(True,", "test_modified_main_data_schema_or_dependency_rejected"),
])
def test_fresh_process_mutations_remove_real_protection(guard, replacement, test):
    # Mutation exists only in fresh-process memory. The actual helper and receipt
    # remain unchanged, so concurrent read-only review sees the exact source.
    runner = r"""
import pathlib, sys, types
import pytest
helper, test_file, guard, replacement, selected = sys.argv[1:]
source = pathlib.Path(helper).read_text()
assert source.count(guard) == 1
mutant = types.ModuleType("mutated_release_verifier")
mutant.__file__ = helper
exec(compile(source.replace(guard, replacement), helper, "exec"), mutant.__dict__)
class Plugin:
    def pytest_collection_modifyitems(self, items):
        for item in items:
            item.module.V = mutant
raise SystemExit(pytest.main([test_file + "::" + selected, "-q",
                             "-p", "no:cacheprovider"], plugins=[Plugin()]))
"""
    result = subprocess.run([sys.executable, "-c", runner, str(HELPER), __file__,
                             guard, replacement, test], capture_output=True, text=True,
                            timeout=60)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "DID NOT RAISE" in result.stdout, result.stdout + result.stderr
