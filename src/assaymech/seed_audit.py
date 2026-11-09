"""Read-only source-binding checks for the bounded initial assay seed.

Checks retained identities, source roles, locators, study bindings and projection
hashes. It does not independently establish scientific truth, authenticate the
upstream server, or turn curator paraphrases into verbatim source material.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from .validate import load, relative_path

# This is the reviewed initial identity set, not a classifier for arbitrary METPO.
ASSAY_IDS = {
    "METPO:1005010", "METPO:1005013", "METPO:1005016",
    "METPO:1007080", "METPO:1007081", "METPO:1007082",
}
OUTCOME_IDS = {f"METPO:{n}" for n in
               (1005011, 1005012, 1005014, 1005015, 1005017, 1005018,
                1007083, 1007084, 1007085, 1007086, 1007087, 1007088)}
PREDICATE_IDS = {"METPO:2000017", "METPO:2000210"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def locator_value(projection, locator):
    if locator.startswith("/"):
        for token in locator[1:].split("/"):
            require(bool(token) and re.search(r"~(?![01])", token) is None,
                    "invalid source JSON Pointer")
            if re.fullmatch(r"-?[0-9]+", token) or token == "-":
                require(re.fullmatch(r"0|[1-9][0-9]*", token),
                        "source array index must be canonical and nonnegative")
    else:
        require(locator.startswith(("html:#", "xlsx:")), "unsupported source locator")
    require(locator in projection["locators"], f"source locator not retained: {locator}")
    return projection["locators"][locator]


def evidence_items(value):
    if isinstance(value, dict):
        if {"reference", "title", "claim", "locator"} <= value.keys():
            yield value
        else:
            for child in value.values():
                yield from evidence_items(child)
    elif isinstance(value, list):
        for child in value:
            yield from evidence_items(child)


def audit(records, catalogue, projections, roles, selection):
    require(catalogue.get("format_version") == 1, "unsupported source catalogue")
    sources = {}
    source_ids = set()
    for source in catalogue["sources"]:
        ref = source["reference"]
        require(ref not in sources and source["source_id"] not in source_ids,
                "duplicate source reference or ID")
        source_ids.add(source["source_id"])
        require(re.fullmatch(r"[0-9a-f]{64}", source["original_sha256"]),
                "invalid original-source digest")
        require(source["original_bytes"] > 0 and source["projection_kind"],
                "missing projection provenance")
        require(source.get("source_license") or source.get("rights_note"),
                "missing source rights provenance")
        projection = projections[source["projection"]]
        require(projection["source_id"] == source["source_id"]
                and projection["reference"] == ref, "projection identity differs")
        sources[ref] = (source, projection)

    def evidence(entries):
        values = []
        for entry in entries:
            require(entry["reference"] in sources, "evidence source not retained")
            source, projection = sources[entry["reference"]]
            require(entry.get("source_license") == source.get("source_license"),
                    "evidence licence differs from this source's verified licence")
            values.append(locator_value(projection, entry["locator"]))
        return values

    def source_for(binding):
        ref = binding["source_url"]
        require(ref in sources, "bound source not retained")
        source, projection = sources[ref]
        require(source.get("source_version") == binding["source_version"]
                and source.get("source_path") == binding["source_path"],
                "source commit or path differs")
        return source, projection

    metpo_ref = roles["source_reference"]
    require(metpo_ref in sources, "METPO role source missing")
    metpo = sources[metpo_ref][1]
    row_by_id = {}
    expected_roles = {**dict.fromkeys(ASSAY_IDS, "ASSAY_IDENTITY"),
                      **dict.fromkeys(OUTCOME_IDS, "OUTCOME_CONCEPT"),
                      **dict.fromkeys(PREDICATE_IDS, "TESTS_PREDICATE"),
                      "METPO:1000697": "MEASURES_PHENOTYPE"}
    for row in roles["rows"]:
        tid = row["term_id"]
        require(tid not in row_by_id, "duplicate METPO role row")
        node = locator_value(metpo, row["source_locator"])
        require(node["id"] == "https://w3id.org/metpo/" + tid.split(":")[1]
                and node["lbl"] == row["term_name"]
                and node["type"] == row["source_entity_type"]
                and node.get("propertyType") == row["property_type"],
                "METPO role row differs from source")
        require(row["curated_role"] == expected_roles.get(tid),
                "METPO semantic role differs from reviewed seed scope")
        require(not node.get("meta", {}).get("deprecated", False), "deprecated METPO term")
        seeded = tid in ASSAY_IDS | PREDICATE_IDS
        require((row["disposition"] == "SEEDED") == seeded
                and bool(row["seed_ids"]) == seeded, "METPO role disposition differs")
        row_by_id[tid] = row
    require(set(row_by_id) == set(expected_roles), "METPO role inventory coverage differs")
    require(set(selection["ontology_identity_ids"]) == ASSAY_IDS,
            "seed identity selection differs")
    bindings = {b["record_id"]: b for b in selection["operational_bindings"]}
    require(len(bindings) == len(selection["operational_bindings"]), "duplicate operational binding")
    ids = set()
    link_count = 0
    for record in records:
        rid = record["id"]
        require(rid not in ids, "duplicate assay ID")
        ids.add(rid)
        evidence(list(evidence_items(record)))
        for grounding in record.get("ontology_groundings", []):
            source, projection = source_for(grounding)
            require(source["reference"] == metpo_ref, "grounding uses another METPO source")
            row = row_by_id.get(grounding["term_id"])
            require(row is not None, "METPO term outside reviewed seed inventory")
            require(row["curated_role"] == grounding["relation"],
                    "METPO grounding role is not supported by the selected source concept")
            require(rid in row["seed_ids"], "METPO grounding belongs to another seed assay")
            node = locator_value(projection, row["source_locator"])
            source_type = "OBJECT_PROPERTY" if node.get("propertyType") == "OBJECT" else node["type"]
            require(grounding["term_name"] == node["lbl"]
                    and grounding["entity_type"] == source_type, "METPO label or entity type differs")
            require(any(e["reference"] == source["reference"]
                        and e["locator"] == row["source_locator"]
                        for e in grounding["evidence"]), "grounding evidence does not select its own term")
        if record["record_kind"] == "ONTOLOGY_ASSAY_CONCEPT":
            require(any(g["relation"] == "ASSAY_IDENTITY"
                        for g in record.get("ontology_groundings", [])), "assay identity missing")
            require(rid not in bindings, "operational seed declared as ontology concept")
        else:
            require(rid in bindings, "operational seed has no reviewed study binding")
            binding = bindings[rid]
            primary_ref = binding["primary_reference"]
            for part in [record, record["method"], record["measurement"]]:
                require(any(e["reference"] == primary_ref for e in part["evidence"]),
                        "operational method or measurement cites a different study")
            actual_targets = {(link["identifier"], link["target_locator"])
                              for link in record.get("related_records", [])}
            expected_targets = {(t["identifier"], t["target_locator"])
                                for t in binding["cmm_targets"]}
            require(actual_targets == expected_targets, "operational CMM targets differ from reviewed scope")
        for link in record.get("related_records", []):
            source, projection = source_for(link)
            require(locator_value(projection, "/id") == link["identifier"], "CMM parent ID differs")
            mechanism = locator_value(projection, link["target_locator"])
            require(isinstance(mechanism, dict) and {"id", "process", "evidence"} <= mechanism.keys(),
                    "CMM target is not the selected mechanism")
            require(any(e["reference"] == source["reference"]
                        and e["locator"] == link["target_locator"] for e in link["evidence"]),
                    "CMM evidence does not select its own target mechanism")
            refs = {entry["source_ref"] for entry in mechanism["evidence"]}
            bibliography = [v for k, v in projection["locators"].items() if k.startswith("/sources/")]
            primary_ref = bindings[rid]["primary_reference"]
            primary = sources[primary_ref][0]
            require(any(e["reference"] == primary_ref for e in link["evidence"]),
                    "CMM link lacks evidence from its assay's primary study")
            primary_id = primary.get("cmm_source_id")
            require(primary_id in refs, "CMM mechanism does not cite this primary study")
            aliases = {primary_ref}
            if primary.get("doi"):
                aliases.add("https://doi.org/" + primary["doi"])
            require(any(b["id"] == primary_id and b["url"] in aliases for b in bibliography),
                    "CMM bibliography does not bind the cited study")
            link_count += 1
    require(ids == set(selection["record_ids"]), "seed record selection coverage differs")
    for row in roles["rows"]:
        require(set(row["seed_ids"]) <= ids, "role inventory references an absent assay")
    return dict(records=len(records), metpo_role_rows=len(row_by_id),
                sources=len(sources), cmm_links=link_count)


def load_inputs(root):
    catalogue = load((root / "curation/source-catalogue.json").read_text())
    projections = {}
    for source in catalogue["sources"]:
        relative_path(source["projection"])
        path = root / source["projection"]
        require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),
                "projection must stay within repository")
        payload = path.read_bytes()
        require(hashlib.sha256(payload).hexdigest() == source["projection_sha256"],
                "source projection checksum differs")
        projections[source["projection"]] = load(payload.decode())
    records = [load(p.read_text()) for p in sorted((root / "data/assays").glob("*.yaml"))]
    roles = load((root / "curation/metpo-role-inventory.json").read_text())
    selection = load((root / "curation/seed-selection.json").read_text())
    return records, catalogue, projections, roles, selection


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        print(json.dumps(audit(*load_inputs(args.root)), sort_keys=True))
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"seed audit failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
