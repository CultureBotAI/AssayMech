"""Read-only AssayMech release-equivalence receipt, 2026-11-13.

Purpose: close provenance/dependency findings in AssayMech issues #6 and #9.
Inputs: explicit consumer/canonical Git roots, reviewed consumer main SHA,
public release/tag/PR metadata and downloaded release-audit.json bytes.
Output: a new JSON receipt. Existing output is never overwritten.
Historical helpers are read as bytes only; no generation, adoption, runtime,
deployment, merge, Git fetch or publication is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CONSUMER = "CultureBotAI/AssayMech"
CANONICAL = "CultureBotAI/culturebotai-claw"
TAG = "repository-freshness-v1.0.0"
RELEASE_COMMIT = "e43afbf92e7ae0265943ca8a237efe07ecf074fb"
REVIEWED_HEAD = "2ebb7927f818576178172d60be0ca59ac2df1edb"
NATIVE_COMMIT = "59ad5327c4ba979254e018c51f180505e1f515a4"
NATIVE_HEAD = "800cc8f941dcaebbd891d8d390c2c7ebdb5e9b4f"
ARCHIVE_HEAD = "64d62515524f49c821b7a0e5e867eeab0fb8e424"
HISTORICAL_SOURCE = "02554818325cd77ddfb72a45a26b4d1d76d6b136"
AUDIT_SHA256 = "a8851663c30b4e3c684f250f06c59f1223feab6e980653a8344c612a64ad9a55"
CANDIDATE = "workflow/candidates/repository-freshness-v1"
ARCHIVE = "scripts/adhoc/repository-freshness-20261110"
CLOSEOUT = "scripts/adhoc/repository-freshness-closeout-20261113"
DECLARATION = f"src/kg_microbe_governance/releases/{TAG}.json"
POLICY = {
    "schema_version": "1.0.0", "id": "repository-freshness", "version": "1.0.0",
    "tag": TAG, "repository": CANONICAL, "source_pr": 1128, "default_branch": "main",
    "source_rule": "actual_protected_squash_merge", "adoption_authority": False,
}
SOURCES = {
    "contract.yaml": "src/kg_microbe_workflows/templates/repository-freshness-v1.yaml",
    "schema.yaml": "src/kg_microbe_workflows/schema/repository-freshness-v1.yaml",
    "SKILL.md": "src/kg_microbe_skills/canonical/repository-freshness.md",
}
PAYLOADS = (
    DECLARATION, *SOURCES.values(), "src/kg_microbe_workflows/freshness.py",
    "src/kg_microbe_workflows/freshness_cli.py", "src/kg_microbe_workflows/freshness_contract.py",
    "src/kg_microbe_governance/freshness_candidates.py",
    "src/kg_microbe_workflows/freshness_release.py", "scripts/mech_session_supervisor.py",
    "scripts/fleet_pull.py", "plugins/lock_manager.py", "plugins/repository_settings.py",
    "src/kg_microbe_fleet/fleet.yaml", "src/kg_microbe_fleet/__init__.py", "pyproject.toml",
    "uv.lock", "docs/guides/REPOSITORY_FRESHNESS_RELEASE.md",
)
ACTIVE_PATHS = (
    "scripts/.vendored_canon_ref", "workflow/mech-workflow.yaml",
    "workflow/parent/mech-cycle.yaml", "workflow/parent/workflow.yaml",
    ".claude/skills/repository-freshness/SKILL.md",
)


class VerificationError(ValueError):
    """Contradictory evidence: no successful receipt."""


def require(condition, reason):
    if not condition:
        raise VerificationError(reason)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def oid(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value),
            "full immutable Git SHA required")
    return value


def valid_identity(origin, repository):
    require(origin in {f"https://github.com/{repository}", f"https://github.com/{repository}.git",
                       f"git@github.com:{repository}.git"}, "Git origin identity differs")


class Git:
    """Read existing objects; disable hooks, replacements and lazy fetch."""
    def __init__(self, root, repository):
        self.root = root.resolve(strict=True)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_NO_REPLACE_OBJECTS="1", GIT_NO_LAZY_FETCH="1",
                        GIT_GRAFT_FILE=os.devnull, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
        valid_identity(self.text("remote", "get-url", "origin"), repository)
        require(Path(self.text("rev-parse", "--show-toplevel")).resolve() == self.root,
                "supplied root is not the repository root")
        self._trees = {}

    def raw(self, *args):
        try:
            result = subprocess.run(
                ["git", "-c", f"core.hooksPath={os.devnull}", "-c", "gc.auto=0",
                 "-C", str(self.root), *args], env=self.env, capture_output=True,
                check=True, timeout=90,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise VerificationError("required local Git observation unavailable") from exc
        require(len(result.stdout) <= 32_000_000, "Git observation exceeds size bound")
        return result.stdout

    def text(self, *args):
        return self.raw(*args).decode().strip()

    def tree(self, commit):
        if commit in self._trees:
            return self._trees[commit]
        result = {}
        for row in self.raw("ls-tree", "-rz", oid(commit)).split(b"\0"):
            if not row:
                continue
            prefix, path = row.split(b"\t", 1)
            mode, kind, object_id = prefix.decode().split()
            require(kind == "blob" and mode in {"100644", "100755", "120000"},
                    "unsupported Git tree entry")
            name = path.decode()
            require(not Path(name).is_absolute() and ".." not in Path(name).parts,
                    "unsafe Git tree path")
            result[name] = (mode, object_id)
        self._trees[commit] = result
        return result

    def blob(self, commit, path):
        entry = self.tree(commit).get(path)
        require(entry is not None and entry[0] in {"100644", "100755"},
                "required regular Git blob missing: " + path)
        return entry[0], self.raw("cat-file", "blob", entry[1])

    def first_parent_contains(self, main, commit):
        return oid(commit) in self.text(
            "rev-list", "--first-parent", "--max-count=100000", oid(main)
        ).splitlines()


class GitHub:
    """Only GET requests; never mutate remote state."""
    def raw(self, endpoint, *, binary=False):
        require(endpoint.startswith("repos/"), "unexpected API endpoint")
        args = ["gh", "api", "--method", "GET", endpoint]
        if binary:
            args += ["-H", "Accept: application/octet-stream"]
        try:
            result = subprocess.run(args, capture_output=True, check=True, timeout=90)
        except (OSError, subprocess.SubprocessError) as exc:
            raise VerificationError("public GitHub observation unavailable") from exc
        require(len(result.stdout) <= 16_000_000, "API observation exceeds size bound")
        return result.stdout

    def get(self, endpoint):
        return strict_json(self.raw(endpoint))

    def assets(self, release_id):
        result = []
        for page in range(1, 11):
            rows = self.get(f"repos/{CANONICAL}/releases/{release_id}/assets"
                            f"?per_page=100&page={page}")
            require(isinstance(rows, list), "invalid release asset page")
            result.extend(rows)
            if len(rows) < 100:
                return result
        raise VerificationError("release assets pagination incomplete")


def checked_pr(api, number, merge, head):
    pr = api.get(f"repos/{CANONICAL}/pulls/{number}")
    require(pr.get("number") == number and pr.get("state") == "closed"
            and pr.get("merged") is True and pr.get("merged_at")
            and pr.get("merge_commit_sha") == merge and pr.get("head", {}).get("sha") == head
            and pr.get("head", {}).get("repo", {}).get("full_name") == CANONICAL
            and pr.get("base", {}).get("ref") == "main"
            and pr.get("base", {}).get("repo", {}).get("full_name") == CANONICAL,
            "merged source PR identity differs")
    return {"number": number, "merge_commit": merge, "reviewed_head": head,
            "merged_at": pr["merged_at"]}


def verify_publication(git, api):
    """Bind downloaded audit bytes, full source tree and all 18 payloads."""
    tag_endpoint = f"repos/{CANONICAL}/git/ref/tags/{TAG}"
    ref = api.get(tag_endpoint)
    obj = ref.get("object", {})
    for _ in range(4):
        if obj.get("type") == "commit":
            break
        require(obj.get("type") == "tag", "unexpected release tag object")
        obj = api.get(f"repos/{CANONICAL}/git/tags/{oid(obj['sha'])}")["object"]
    require(obj.get("type") == "commit" and obj.get("sha") == RELEASE_COMMIT,
            "release tag differs from actual approved source")
    endpoint = f"repos/{CANONICAL}/releases/tags/{TAG}"
    release = api.get(endpoint)
    require(release.get("tag_name") == TAG and release.get("draft") is False
            and release.get("prerelease") is False and release.get("published_at")
            and release.get("target_commitish") == RELEASE_COMMIT
            and release.get("html_url") == f"https://github.com/{CANONICAL}/releases/tag/{TAG}",
            "published release metadata differs")
    assets = api.assets(release["id"])
    matches = [a for a in assets if a.get("name") == "release-audit.json"]
    require(len(matches) == 1, "release must contain one audit asset")
    asset = matches[0]
    raw = api.raw(f"repos/{CANONICAL}/releases/assets/{asset['id']}", binary=True)
    require(sha256(raw) == AUDIT_SHA256 and asset.get("digest") == "sha256:" + sha256(raw)
            and asset.get("size") == len(raw), "downloaded release audit digest differs")
    audit = strict_json(raw)
    require(raw == encoded(audit) and audit.get("declaration") == POLICY
            and audit.get("kind") == "verified_freshness_release_source"
            and audit.get("source_commit") == RELEASE_COMMIT
            and audit.get("reviewed_head") == REVIEWED_HEAD
            and audit.get("installed") is False and audit.get("adopted") is False
            and audit.get("release_immutability_claimed") is False
            and audit.get("tag_protection_claimed") is False,
            "release audit identity or authority differs")
    require(git.text("rev-parse", RELEASE_COMMIT + "^{tree}") == oid(audit["source_tree"]),
            "full release source tree differs")
    require(git.text("rev-list", "--parents", "-n", "1", RELEASE_COMMIT).split()
            == [RELEASE_COMMIT, oid(audit["reviewed_base"])], "release merge parent differs")
    require(set(audit["payloads"]) == set(PAYLOADS), "release payload inventory differs")
    for path in PAYLOADS:
        mode, content = git.blob(RELEASE_COMMIT, path)
        require(audit["payloads"][path] == {
            "mode": mode, "bytes": len(content), "sha256": sha256(content),
        }, "release payload differs: " + path)
    require(strict_json(git.blob(RELEASE_COMMIT, DECLARATION)[1]) == POLICY,
            "source declaration differs")
    source_pr = checked_pr(api, 1128, RELEASE_COMMIT, REVIEWED_HEAD)
    require(source_pr["merged_at"] == audit["merged_at"], "source merge time differs")
    native_pr = checked_pr(api, 1165, NATIVE_COMMIT, NATIVE_HEAD)
    main_endpoint = f"repos/{CANONICAL}/commits/main"
    main = oid(api.get(main_endpoint)["sha"])
    for commit in (RELEASE_COMMIT, NATIVE_COMMIT, oid(audit["observed_main"])):
        require(git.first_parent_contains(main, commit), "dependency absent from canonical main")
    require(api.get(tag_endpoint) == ref and api.get(endpoint) == release
            and api.get(main_endpoint)["sha"] == main and api.assets(release["id"]) == assets,
            "canonical observations changed; retry")
    require(checked_pr(api, 1128, RELEASE_COMMIT, REVIEWED_HEAD) == source_pr
            and checked_pr(api, 1165, NATIVE_COMMIT, NATIVE_HEAD) == native_pr,
            "merged dependencies changed; retry")
    return {"tag": TAG, "source_commit": RELEASE_COMMIT, "source_tree": audit["source_tree"],
            "observed_main": main, "release_id": release["id"],
            "published_at": release["published_at"], "url": release["html_url"],
            "asset_id": asset["id"], "audit_sha256": sha256(raw), "audit_bytes": len(raw),
            "payloads": audit["payloads"], "source_pr": source_pr, "native_pr": native_pr,
            "release_immutable_observed": release.get("immutable"),
            "tag_protection_claimed": False, "release_immutability_claimed": False}


def disk_entry(root, name):
    """Read exact files/modes without following symlink parent directories."""
    path = root / name
    for parent in path.relative_to(root).parents:
        require(not (root / parent).is_symlink(), "symlinked parent is not audit input")
    if not path.exists() and not path.is_symlink():
        return None
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        return "120000", os.readlink(path).encode()
    require(stat.S_ISREG(mode), "audit input is not a regular file")
    return ("100755" if mode & 0o111 else "100644"), path.read_bytes()


def verify_candidate(repository, canonical):
    provenance_path = ARCHIVE + "/provenance.json"
    archived = repository.blob(ARCHIVE_HEAD, provenance_path)[1]
    require(disk_entry(repository.root, provenance_path) == ("100644", archived),
            "original provenance bytes changed")
    provenance = strict_json(archived)
    require(provenance["repository"] == CONSUMER
            and provenance["canonical_source"]["source_commit"] == HISTORICAL_SOURCE,
            "historical provenance identity differs")
    names = set(SOURCES) | {"proposal.json"}
    require(set(provenance["candidate_sha256"]) == names
            and {p.name for p in (repository.root / CANDIDATE).iterdir()} == names,
            "candidate inventory differs, including hidden files")
    for name, expected in provenance["candidate_sha256"].items():
        observed = disk_entry(repository.root, CANDIDATE + "/" + name)
        require(observed is not None and observed[0] == "100644"
                and sha256(observed[1]) == expected
                and observed == repository.blob(ARCHIVE_HEAD, CANDIDATE + "/" + name),
                "historical candidate changed: " + name)
    for name, expected in provenance["original_helpers_sha256"].items():
        observed = disk_entry(repository.root, ARCHIVE + "/" + name)
        require(observed is not None and sha256(observed[1]) == expected
                and observed == repository.blob(ARCHIVE_HEAD, ARCHIVE + "/" + name),
                "historical helper changed: " + name)
    for path, expected in provenance["canonical_source"]["source_sha256"].items():
        historical = canonical.blob(HISTORICAL_SOURCE, path)
        require(sha256(historical[1]) == expected
                and historical == canonical.blob(RELEASE_COMMIT, path),
                "historical source differs from release: " + path)
    require(canonical.text("rev-parse", HISTORICAL_SOURCE + "^{tree}")
            == provenance["canonical_source"]["source_tree"], "historical source tree differs")
    for name, source in SOURCES.items():
        released = canonical.blob(RELEASE_COMMIT, source)[1]
        if name == "SKILL.md":
            released = released.replace(b"{{ display_name }}", b"AssayMech").replace(
                b"{{ github }}", CONSUMER.encode())
        require(disk_entry(repository.root, CANDIDATE + "/" + name)[1] == released,
                "rendered candidate differs from released source: " + name)
    proposal = strict_json(disk_entry(repository.root, CANDIDATE + "/proposal.json")[1])
    require(proposal.get("authority") == "proposal_only" and proposal.get("installed") is False
            and proposal.get("adopted") is False
            and proposal.get("state") == "blocked_on_canonical_release"
            and proposal["canonical_source"].get("released") is False
            and proposal["canonical_source"].get("repository") == CANONICAL
            and proposal["canonical_source"].get("reviewed_source_commit") == HISTORICAL_SOURCE
            and proposal.get("github_repository") == CONSUMER,
            "historical proposal authority or identity differs")
    return {"archived_head": ARCHIVE_HEAD, "historical_source_commit": HISTORICAL_SOURCE,
            "candidate_sha256": provenance["candidate_sha256"],
            "helpers_sha256": provenance["original_helpers_sha256"],
            "provenance_sha256": sha256(archived),
            "historical_source_sha256": provenance["canonical_source"]["source_sha256"],
            "proposal_state_preserved": proposal["state"], "proposal_released_preserved": False}


def verify_main_preserved(repository, api, base):
    endpoint = f"repos/{CONSUMER}/commits/main"
    require(oid(api.get(endpoint)["sha"]) == oid(base), "consumer main differs from reviewed base")
    head = oid(repository.text("rev-parse", "HEAD"))
    require(repository.text("merge-base", base, head) == base, "reviewed main is not integrated")
    inventory = {}
    tree = repository.tree(base)
    for path, (mode, object_id) in tree.items():
        raw = repository.raw("cat-file", "blob", object_id)
        require(disk_entry(repository.root, path) == (mode, raw),
                "published main file changed: " + path)
        inventory[path] = {"mode": mode, "sha256": sha256(raw)}
    active = {}
    for path in ACTIVE_PATHS:
        value = disk_entry(repository.root, path)
        require(path in tree or value is None, "new active workflow/skill path exists")
        active[path] = None if value is None else sha256(value[1])
    require(api.get(endpoint)["sha"] == base, "consumer main changed; retry")
    return {"base_commit": base, "head_at_verification": head,
            "base_tree": repository.text("rev-parse", base + "^{tree}"),
            "all_main_blobs_and_modes_preserved": True, "file_count": len(inventory),
            "inventory_sha256": sha256(encoded(inventory)), "active_paths_sha256": active}


def verify(repository, canonical, api, base):
    publication = verify_publication(canonical, api)
    candidate = verify_candidate(repository, canonical)
    preserved = verify_main_preserved(repository, api, base)
    return {"schema_version": "1.0.0", "kind": "verified_release_equivalent_inert_candidate",
            "observed_at": datetime.now(timezone.utc).isoformat(), "repository": CONSUMER,
            "helper_sha256": sha256(Path(__file__).read_bytes()),
            "authority": "verification_only", "installed": False, "adopted": False,
            "canonical_release_prerequisite_satisfied": True,
            "canonical_publication": publication, "historical_candidate": candidate,
            "consumer_preservation": preserved,
            "remaining_requirements": ["independent final-head review and green consumer checks",
                                       "reviewed consumer merge",
                                       "separate approved immutable boundary adoption",
                                       "verified cycle boundary with exact predecessor closure",
                                       "separate reviewed live control deployment"],
            "runtime_authority_granted": False}


def write_receipt(output, value, repository_root, canonical_root):
    resolved = output.resolve()
    require(not resolved.is_relative_to(canonical_root.resolve()),
            "output cannot modify canonical source")
    if resolved.is_relative_to(repository_root.resolve()):
        require(resolved.is_relative_to((repository_root / CLOSEOUT).resolve()),
                "in-repository output must be in the dedicated closeout directory")
    require(not output.exists() and not output.is_symlink(), "receipt output already exists")
    with output.open("xb") as stream:
        stream.write(encoded(value))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        require(not args.output.exists() and not args.output.is_symlink(),
                "receipt output already exists")
        repository = Git(args.repository_root, CONSUMER)
        canonical = Git(args.canonical_root, CANONICAL)
        result = verify(repository, canonical, GitHub(), oid(args.base_commit))
        write_receipt(args.output, result, repository.root, canonical.root)
        print(json.dumps({"status": "verified", "installed": False, "adopted": False,
                          "audit_sha256": result["canonical_publication"]["audit_sha256"]}))
        return 0
    except (VerificationError, OSError, ValueError, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, VerificationError) else type(exc).__name__
        print(json.dumps({"status": "hold", "reason": reason}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
