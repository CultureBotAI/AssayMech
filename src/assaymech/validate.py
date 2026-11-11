"""Closed LinkML validation plus offline provenance and history invariants."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from functools import lru_cache
from importlib.resources import files
from pathlib import Path, PurePosixPath

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from linkml.generators.jsonschemagen import JsonSchemaGenerator

CORPORA = {"cmmmech": "CultureBotAI/CMMMech"}
METPO_REPOSITORY = "berkeleybop/metpo"
GROUNDING_TYPES = {
    "ASSAY_IDENTITY": "CLASS",
    "MEASURES_PHENOTYPE": "CLASS",
    "TESTS_PREDICATE": "OBJECT_PROPERTY",
}


class StrictLoader(yaml.SafeLoader):
    """Reject duplicate keys and retain timestamp strings for schema validation."""


StrictLoader.yaml_implicit_resolvers = {
    key: [(tag, pattern) for tag, pattern in values if tag != "tag:yaml.org,2002:timestamp"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def _mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError(f"duplicate or non-string YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load(text: str) -> dict:
    value = yaml.load(text, Loader=StrictLoader)
    if not isinstance(value, dict):
        raise ValueError("document must be an object")
    return value


@lru_cache(maxsize=2)
def validator(kind: str = "AssayRecord") -> Draft202012Validator:
    schema = files("assaymech").joinpath("schema/assaymech.yaml")
    generated = json.loads(JsonSchemaGenerator(
        str(schema), top_class=kind, not_closed=False, include_null=False
    ).serialize())
    Draft202012Validator.check_schema(generated)
    return Draft202012Validator(generated, format_checker=FormatChecker())


def relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (not value or not path.parts or path.is_absolute() or ".." in path.parts
            or str(path) != value or any(c in value for c in "\\\n\r?#")):
        raise ValueError(f"unsafe repository-relative path: {value!r}")
    return path


def utc_timestamp(value: str) -> None:
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)", value):
        raise ValueError(f"timestamp must be a full UTC timestamp in 2000..2099: {value}")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must use UTC")


def _nonempty(value) -> None:
    if isinstance(value, str) and not value.strip():
        raise ValueError("strings must not be empty or whitespace")
    if isinstance(value, dict):
        for item in value.values():
            _nonempty(item)
    elif isinstance(value, list):
        for item in value:
            _nonempty(item)


def validate_history(record: dict) -> None:
    validator("HistoryRecord").validate(record)
    _nonempty(record)
    if record["history_version"] != 1:
        raise ValueError("history_version must be 1")
    utc_timestamp(record["session"]["timestamp"])
    relative_path(record["target"]["path"])


def _source_binding(source: dict, repository: str) -> None:
    relative_path(source["source_path"])
    expected = (f"https://github.com/{repository}/blob/"
                f"{source['source_version']}/{source['source_path']}")
    if source["source_url"] != expected:
        raise ValueError("source URL must identify the declared repository, commit and path")


def json_pointer(value: str) -> None:
    if not value.startswith("/") or len(value.split("/")) < 3:
        raise ValueError("target locator must identify a nested source entity by JSON Pointer")
    for token in value[1:].split("/"):
        if not token or re.search(r"~(?![01])", token):
            raise ValueError("invalid JSON Pointer token or escape")
        if token == "-" or (re.fullmatch(r"-?[0-9]+", token)
                             and not re.fullmatch(r"0|[1-9][0-9]*", token)):
            raise ValueError("JSON Pointer array indexes must be nonnegative canonical integers")


def validate_record(record: dict) -> None:
    validator().validate(record)
    _nonempty(record)
    if len(record["categories"]) != len(set(record["categories"])):
        raise ValueError("duplicate assay category")
    groundings = record.get("ontology_groundings", [])
    links = record.get("related_records", [])
    gaps = {gap["scope"] for gap in record.get("research_gaps", [])}
    if not groundings and "metpo" not in gaps:
        raise ValueError("METPO needs an evidence-backed grounding or an explicit research gap")
    if not links and "cmmmech" not in gaps:
        raise ValueError("CMM applicability needs an evidence-backed link or an explicit research gap")
    if record["record_kind"] == "ONTOLOGY_ASSAY_CONCEPT":
        if not any(g["relation"] == "ASSAY_IDENTITY" for g in groundings):
            raise ValueError("ontology assay concepts require an ASSAY_IDENTITY grounding")
    elif not record.get("method") or not record.get("measurement"):
        raise ValueError("operational assays require a sourced method and measurement")
    for name in ("method", "measurement"):
        if not record.get(name) and name not in gaps:
            raise ValueError(f"missing {name} must be an explicit research gap")
    seen = set()
    for grounding in groundings:
        if grounding["entity_type"] != GROUNDING_TYPES[grounding["relation"]]:
            raise ValueError("grounding relation is incompatible with ontology entity type")
        _source_binding(grounding, METPO_REPOSITORY)
        key = tuple(grounding[field] for field in
                    ("term_id", "relation", "source_version", "source_path"))
        if key in seen:
            raise ValueError("duplicate ontology grounding")
        seen.add(key)
    seen = set()
    for link in links:
        _source_binding(link, CORPORA[link["corpus"]])
        json_pointer(link["target_locator"])
        key = tuple(link[field] for field in
                    ("corpus", "identifier", "relation", "source_version", "source_path",
                     "target_locator"))
        if key in seen:
            raise ValueError("duplicate cross-corpus link")
        seen.add(key)
    seen_history = set()
    for event in record["curation_history"]:
        utc_timestamp(event["timestamp"])
        path = relative_path(event["history_file"])
        if path.parts[:2] != ("history", "records") or path.suffix != ".yaml":
            raise ValueError("history_file must name a record sidecar under history/records")
        if event["history_file"] in seen_history:
            raise ValueError("duplicate curation history sidecar")
        seen_history.add(event["history_file"])


def validate_path_components(root: Path, relative: str) -> None:
    """Reject directory aliases before reading or staging a corpus path."""
    path = relative_path(relative)
    current = root
    for index, part in enumerate(path.parts):
        current = current / part
        if current.is_symlink() or not current.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"record/history path must not include a symlink or escape: {relative}")
        if index < len(path.parts) - 1 and current.exists() and not current.is_dir():
            raise ValueError(f"record/history parent must be a directory: {relative}")


def validate_inventory_roots(root: Path) -> None:
    for relative in ("data", "data/assays", "history"):
        directory = root / relative
        if directory.is_symlink() or not directory.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"inventory/history root must not be a symlink or escape: {relative}")
        if not directory.is_dir():
            raise ValueError(f"required inventory or history directory is missing: {relative}")


def validate_history_links(root: Path, record: dict, record_path: str, proposed=None) -> set[str]:
    proposed = proposed or {}
    referenced = set()
    for event in record["curation_history"]:
        relative = event["history_file"]
        validate_path_components(root, relative)
        source = root / relative
        sidecar = proposed.get(relative)
        if sidecar is None:
            sidecar = load(source.read_text())
        validate_history(sidecar)
        if sidecar["target"]["path"] != record_path:
            raise ValueError("history sidecar target differs from record path")
        if sidecar["session"]["id"] != Path(relative).stem:
            raise ValueError("history session ID differs from filename")
        if sidecar["session"]["timestamp"] != event["timestamp"]:
            raise ValueError("inline event and history timestamp differ")
        if event["curator"] not in {actor["name"] for actor in sidecar["session"]["actors"]}:
            raise ValueError("inline curator missing from history actors")
        if not any(item["summary"] == event["summary"] and item["type"] == event["action"]
                   for item in sidecar["events"]):
            raise ValueError("inline event differs from canonical history event")
        referenced.add(relative)
    return referenced


def validate_repository(root: Path) -> int:
    validator()
    validator("HistoryRecord")
    validate_inventory_roots(root)
    ids = set()
    referenced = set()
    paths = sorted((root / "data/assays").glob("*.yaml"))
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"record must not be a symlink: {path}")
        record = load(path.read_text())
        validate_record(record)
        if record["id"] in ids:
            raise ValueError(f"duplicate record identifier: {record['id']}")
        if path.stem != record["id"].split(":", 1)[1]:
            raise ValueError("record filename must match its identifier slug")
        ids.add(record["id"])
        referenced |= validate_history_links(root, record, str(path.relative_to(root)))
    sidecars = {str(path.relative_to(root)) for path in (root / "history").rglob("*.yaml")}
    if sidecars != referenced:
        raise ValueError(f"unreferenced or missing history sidecars: {sorted(sidecars ^ referenced)}")
    return len(paths)
