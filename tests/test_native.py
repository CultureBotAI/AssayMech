"""Closed assay schemas and native provenance/history boundaries; all fixtures are synthetic."""

import subprocess
from argparse import Namespace
from copy import deepcopy
from pathlib import Path

import pytest
from kg_microbe_history.scaffold import build_record

from assaymech.cli import new_history
from assaymech.validate import (
    load,
    validate_history_links,
    validate_record,
    validate_repository,
)


@pytest.fixture
def record():
    evidence = [{"reference": "https://example.org/source", "title": "Fixture source",
                 "claim": "Synthetic test only", "locator": "fixture section"}]
    return {
        "id": "AssayMech:fixture", "name": "Synthetic fixture",
        "record_kind": "ONTOLOGY_ASSAY_CONCEPT",
        "categories": ["MICROBIAL_CHARACTERIZATION"],
        "description": "Synthetic test only; no scientific assertion.",
        "limitations": ["Synthetic fixture is not a usable assay."],
        "evidence": deepcopy(evidence),
        "ontology_groundings": [{
            "term_id": "METPO:1000001", "term_name": "Synthetic ontology term",
            "entity_type": "CLASS", "relation": "ASSAY_IDENTITY",
            "source_version": "a" * 40, "source_path": "metpo.json",
            "source_url": "https://github.com/berkeleybop/metpo/blob/" + "a" * 40 + "/metpo.json",
            "evidence": deepcopy(evidence),
        }],
        "research_gaps": [{"scope": scope, "reason": "Synthetic fixture has no real sources"}
                          for scope in ("cmmmech", "method", "measurement")],
        "curation_history": [{"timestamp": "2026-11-08T12:00:00Z", "curator": "fixture",
                              "action": "CREATE", "summary": "Create synthetic test",
                              "history_file": "history/records/fixture/session.yaml"}],
    }


@pytest.fixture
def link(record):
    return {
        "corpus": "cmmmech", "identifier": "cmmmech:fixture", "relation": "MEASURES_PROCESS",
        "basis": "Synthetic fixture only", "source_version": "a" * 40,
        "source_path": "data/elements/fixture.yaml",
        "source_url": "https://github.com/CultureBotAI/CMMMech/blob/"
                      + "a" * 40 + "/data/elements/fixture.yaml",
        "target_locator": "/mechanisms/0", "scope": "Synthetic system and measured endpoint",
        "evidence": deepcopy(record["evidence"]),
    }


def operational(record):
    record["record_kind"] = "OPERATIONAL_ASSAY"
    record["method"] = {"summary": "Synthetic method", "evidence": deepcopy(record["evidence"])}
    record["measurement"] = {"target": "Synthetic target", "readout": "Synthetic readout",
                             "evidence": deepcopy(record["evidence"])}
    return record


def test_valid_scoped_assay_and_cmm_link(record, link):
    record["related_records"] = [link]
    validate_record(record)
    operational(record)
    validate_record(record)


@pytest.mark.parametrize("location", ["root", "evidence", "history", "link", "grounding",
                                      "method", "measurement", "control"])
def test_unknown_fields_are_rejected_recursively(record, link, location):
    operational(record)
    record["related_records"] = [link]
    control = {"description": "Synthetic control", "evidence": deepcopy(record["evidence"])}
    record["controls"] = [control]
    targets = {"root": record, "evidence": record["evidence"][0],
               "history": record["curation_history"][0], "link": link,
               "grounding": record["ontology_groundings"][0], "method": record["method"],
               "measurement": record["measurement"], "control": control}
    targets[location]["unknown_field"] = "must not pass"
    with pytest.raises(Exception, match="Additional properties"):
        validate_record(record)


@pytest.mark.parametrize("field,value", [
    ("categories", []), ("evidence", []), ("curation_history", []), ("limitations", []),
    ("record_kind", "ORGANISM_RESULT"), ("name", " "), ("categories", ["VITAMIN"]),
])
def test_invalid_record_shapes(record, field, value):
    record[field] = value
    with pytest.raises(Exception):
        validate_record(record)


@pytest.mark.parametrize("field,value", [
    ("source_version", "main"), ("source_url", "https://github.com/Other/Repo/blob/" + "a" * 40 + "/fixture.yaml"),
    ("source_path", "../escape.yaml"), ("relation", "REQUIRED_BY"),
    ("target_locator", "/mechanisms/-1"), ("scope", " "), ("evidence", []),
])
def test_invalid_links(record, link, field, value):
    link[field] = value
    record["related_records"] = [link]
    with pytest.raises(Exception):
        validate_record(record)


def test_missing_cmm_applicability_is_an_explicit_gap(record):
    record["research_gaps"] = record["research_gaps"][1:]
    with pytest.raises(ValueError, match="CMM applicability"):
        validate_record(record)


def test_missing_metpo_mapping_is_explicit_and_not_an_assay_identity(record):
    operational(record)
    record.pop("ontology_groundings")
    with pytest.raises(ValueError, match="METPO needs"):
        validate_record(record)
    record["research_gaps"].append({"scope": "metpo", "reason": "No exact ontology mapping"})
    validate_record(record)
    record["record_kind"] = "ONTOLOGY_ASSAY_CONCEPT"
    with pytest.raises(ValueError, match="ASSAY_IDENTITY"):
        validate_record(record)


@pytest.mark.parametrize("relation,wrong_type", [
    ("ASSAY_IDENTITY", "OBJECT_PROPERTY"), ("MEASURES_PHENOTYPE", "OBJECT_PROPERTY"),
    ("TESTS_PREDICATE", "CLASS"),
])
def test_grounding_relation_requires_compatible_entity_type(record, relation, wrong_type):
    operational(record)
    grounding = record["ontology_groundings"][0]
    grounding.update(relation=relation, entity_type=wrong_type)
    with pytest.raises(ValueError, match="incompatible with ontology entity type"):
        validate_record(record)
    grounding["entity_type"] = "CLASS" if relation != "TESTS_PREDICATE" else "OBJECT_PROPERTY"
    validate_record(record)


def test_measured_phenotype_is_not_an_assay_identity(record):
    record["ontology_groundings"][0]["relation"] = "MEASURES_PHENOTYPE"
    with pytest.raises(ValueError, match="ASSAY_IDENTITY"):
        validate_record(record)
    operational(record)
    validate_record(record)


@pytest.mark.parametrize("field", ["method", "measurement"])
def test_operational_assay_requires_sourced_method_and_readout(record, field):
    operational(record)
    record.pop(field)
    with pytest.raises(ValueError, match="operational assays require"):
        validate_record(record)


def test_metpo_source_is_bound_to_repository_revision_and_path(record):
    record["ontology_groundings"][0]["source_version"] = "b" * 40
    with pytest.raises(ValueError, match="source URL must identify"):
        validate_record(record)


def test_duplicate_grounding_is_rejected(record):
    record["ontology_groundings"].append(deepcopy(record["ontology_groundings"][0]))
    with pytest.raises(ValueError, match="duplicate ontology"):
        validate_record(record)


def test_distinct_cmm_mechanisms_are_separate_links(record, link):
    second = deepcopy(link)
    second["target_locator"] = "/mechanisms/1"
    record["related_records"] = [link, second]
    validate_record(record)
    record["related_records"].append(deepcopy(link))
    with pytest.raises(ValueError, match="duplicate cross-corpus"):
        validate_record(record)


@pytest.mark.parametrize("pointer", ["/mechanisms/-1", "/mechanisms/01", "/mechanisms/-",
                                    "/mechanisms/0/invalid~2escape", "/mechanisms"])
def test_invalid_target_json_pointer_is_rejected(record, link, pointer):
    link["target_locator"] = pointer
    record["related_records"] = [link]
    with pytest.raises(ValueError, match="JSON Pointer"):
        validate_record(record)


@pytest.mark.parametrize("timestamp", ["2206-11-08T12:00:00Z", "2026-11-08", "2026-11-08T12:00:00",
                                       "2026-02-30T12:00:00Z", "2026-11-08T12:00:00+01:00"])
def test_invalid_timestamps(record, timestamp):
    record["curation_history"][0]["timestamp"] = timestamp
    with pytest.raises(Exception):
        validate_record(record)


def test_duplicate_yaml_keys_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        load("id: one\nid: two\n")


def test_missing_and_wrong_history_target_fail(tmp_path, record):
    with pytest.raises(FileNotFoundError):
        validate_history_links(tmp_path, record, "data/assays/fixture.yaml")
    sidecar = build_record(kind="record", slug="fixture", target_path="data/assays/other.yaml",
                           session_id="session", timestamp="2026-11-08T12:00:00Z",
                           summary="Create synthetic test", details="Synthetic fixture only",
                           event="CREATE", actor_name="fixture", actor_type="human")
    with pytest.raises(ValueError, match="target differs"):
        validate_history_links(tmp_path, record, "data/assays/fixture.yaml",
                               {"history/records/fixture/session.yaml": sidecar})


def test_deleted_inventory_directory_is_not_an_empty_corpus(tmp_path):
    with pytest.raises(ValueError, match="required inventory"):
        validate_repository(tmp_path)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for args in (["init"], ["config", "user.name", "Fixture"],
                 ["config", "user.email", "fixture@example.invalid"],
                 ["remote", "add", "origin", "https://github.com/CultureBotAI/AssayMech.git"],
                 ["commit", "--allow-empty", "-m", "Fixture"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    (root / "data/assays").mkdir(parents=True)
    (root / "history").mkdir()
    return root


def test_history_writer_dry_run_apply_and_append_only(repo, record):
    import json
    record.pop("curation_history")
    source = repo / "input.yaml"
    source.write_text(json.dumps(record))
    args = Namespace(record="data/assays/fixture.yaml", input=str(source), actor="fixture",
                     actor_type="human", summary="Create synthetic test", details="Fixture only",
                     action="CREATE", model=None, agent_tool=None, apply=False)
    result = new_history(repo, args)
    assert result["applied"] is False
    assert not (repo / args.record).exists()
    assert not list((repo / "history").rglob("*.yaml"))
    args.apply = True
    new_history(repo, args)
    assert validate_repository(repo) == 1
    saved = load((repo / args.record).read_text())
    assert {key: value for key, value in saved.items() if key != "curation_history"} == record
    original_event = deepcopy(saved["curation_history"][0])
    source.write_text(json.dumps(saved))
    args.action = "EDIT"
    new_history(repo, args)
    updated = load((repo / args.record).read_text())
    assert updated["curation_history"][0] == original_event
    assert len(updated["curation_history"]) == 2
    assert validate_repository(repo) == 1
    updated["curation_history"] = []
    source.write_text(json.dumps(updated))
    with pytest.raises(ValueError, match="preserve existing"):
        new_history(repo, args)
    assert len(list((repo / "history").rglob("*.yaml"))) == 2


def test_history_writer_invalid_input_changes_nothing(repo, record):
    import json
    record.pop("curation_history")
    record["evidence"] = []
    source = repo / "input.yaml"
    source.write_text(json.dumps(record))
    args = Namespace(record="data/assays/fixture.yaml", input=str(source), actor="fixture",
                     actor_type="human", summary="Create synthetic test", details="Fixture only",
                     action="CREATE", model=None, agent_tool=None, apply=True)
    with pytest.raises(Exception):
        new_history(repo, args)
    assert not (repo / args.record).exists()
    assert not list((repo / "history").rglob("*.yaml"))


def test_native_ci_runs_required_gate_on_pr_push_and_merge_group():
    root = Path(__file__).resolve().parents[1]
    # BaseLoader retains YAML's literal 'on' key.
    import yaml
    workflow = yaml.load((root / ".github/workflows/validate-strict.yaml").read_text(),
                         Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"pull_request", "push", "merge_group"}
    assert workflow["on"]["pull_request"] == {}
    assert workflow["on"]["merge_group"]["types"] == ["checks_requested"]
    job = workflow["jobs"]["validate-strict"]
    assert "if" not in job
    commands = [step.get("run") for step in job["steps"]]
    assert "just check" in commands and "just check-vendored" in commands


def test_pin_and_installed_dependency_share_revision():
    import tomllib
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text())
    assert config["tool"]["uv"]["sources"]["kg-microbe-orchestration"]["rev"] == (
        root / "scripts/.vendored_canon_ref").read_text().strip()


@pytest.mark.parametrize("relative", ["data", "data/assays", "history"])
@pytest.mark.parametrize("external", [False, True])
def test_symlinked_inventory_and_history_roots_are_rejected(tmp_path, relative, external):
    root = tmp_path / "repo"
    (root / "data/assays").mkdir(parents=True)
    (root / "history").mkdir()
    source = root / relative
    destination = tmp_path / "outside" if external else root / "alternate"
    source.rename(destination)
    source.symlink_to(destination, target_is_directory=True)
    assert source.is_symlink() and source.is_dir()
    assert source.resolve().is_relative_to(root) is not external
    with pytest.raises(ValueError, match="must not be a symlink or escape"):
        validate_repository(root)


def test_valid_empty_scaffold_directories_pass(tmp_path):
    (tmp_path / "data/assays").mkdir(parents=True)
    (tmp_path / "history").mkdir()
    assert validate_repository(tmp_path) == 0


@pytest.mark.parametrize("relative", ["data", "data/assays", "history", "history/records",
                                      "history/records/fixture"])
@pytest.mark.parametrize("external", [False, True])
@pytest.mark.parametrize("apply", [False, True])
def test_history_writer_rejects_all_symlink_directories_before_staging(repo, record,
                                                                    relative, external, apply):
    import json
    source_directory = repo / relative
    source_directory.mkdir(parents=True, exist_ok=True)
    alternate = repo.parent / "external-alternate" if external else repo / "internal-alternate"
    source_directory.rename(alternate)
    source_directory.symlink_to(alternate, target_is_directory=True)
    assert source_directory.is_symlink() and source_directory.is_dir()
    record.pop("curation_history")
    source = repo / "input.yaml"
    source.write_text(json.dumps(record))
    args = Namespace(record="data/assays/fixture.yaml", input=str(source), actor="fixture",
                     actor_type="human", summary="Create synthetic test", details="Fixture only",
                     action="CREATE", model=None, agent_tool=None, apply=apply)
    with pytest.raises(Exception):  # Refusal and unchanged state, not exception wording.
        new_history(repo, args)
    assert not (repo / args.record).exists()
    assert not list(alternate.rglob("*.yaml"))
    assert not list((repo / "history").rglob("*.yaml"))
    assert not (repo / "workspace").exists()
