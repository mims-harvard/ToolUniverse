#!/usr/bin/env python3
"""What a tool's upstream answered, and what the tool passed on to the caller.

WHY THIS EXISTS. "Part of a result returned as all of it" has two axes. The row
axis was swept in #824: search and list tools now report `returned`,
`total_results`, `has_more`, `truncated` and `result_set_complete`. The field
axis -- a wrapper selecting a hand-written subset of each record and returning
it as the record -- can be measured mechanically for the 102 tools with a
declared GraphQL query, because the endpoint can be introspected. For the other
2,786 it cannot: nothing static says what the upstream offers.

This measures it from the call that is already being made. It records every
JSON response at the HTTP layer, runs the tool's own first test_example, and
compares the two.

IT COMPARES VALUES, NOT KEY NAMES. Wrappers rename. ComplexPortal answers
`ac`, `systematicName` and `participants`; the tool returns `complex_id`,
`systematic_name` and `subunits`. A key-name diff calls all three losses. A
value reaching the caller under any name is not a loss, so each upstream field
is scored by whether its own leaf values survive anywhere in the output.

IT REPORTS A FIELD WITH NO SURVIVING VALUE, NOT A LOW RATIO. A ratio flags
pagination, which is the other axis and already disclosed: MediaDive's upstream
answers 3,344 media and the tool returns a page of 20, so `data[].name` scores
20/3344 and reads as a loss while the field is plainly exposed. A field the
wrapper drops has no surviving value at all; a field it exposes has at least the
current page's. `--min-values` then suppresses the other false positive, a
single value that was transformed rather than dropped: ComplexPortal splits
`species` into `species` and `taxonomy_id`, so the combined upstream string
matches nothing.

A FIELD CAN ALSO BE SELECTED AND STILL HAVE NOTHING TO SHOW. The same MediaDive
wrapper does carry `description` and `reference`, but every row matching
'nutrient agar' is null in both, so they scored 0/68 and 0/36 on the first
sampled run and cost real triage time. So zero-survivor fields are split by a
second signal -- whether the field's own name, normalised, reaches the caller.
Named and empty goes to `mapped_but_unseen`; never asked for goes to
`thin_fields`, which is what the sweep reports. Only `link` survives that split
for MediaDive, and `link` really is dropped. The same signal also catches a
transformation the value comparison cannot: Synapse maps `type` through
`_short_type`, turning `org.sagebionetworks.repo.model.FileEntity` into `file`,
so no value matches while the field is there under its own name.

The signal is a key-name match, so on its own a generic name is met by an
unrelated key elsewhere in the output: GEO's esummary carries `accession` twice,
the series' own and `samples[].accession`, and the first vouched for the second
until a leaf name that already reaches the caller from another path stopped
counting as an excuse. Nothing is discarded either way -- a tool with an empty
`thin_fields` and a long `mapped_but_unseen` is still worth a look.

Measured on CPX-1, what survives the two filters is real: the subunit records
drop `participants[].linkedFeatures[].*` -- which region of each subunit binds
which partner -- along with `bioRole` and the ontology ids used for
cross-referencing.

WHAT IT DOES NOT DECIDE. Whether a dropped field matters is the judgement rule
from devtu-silent-failures: it is a defect when the skipped field is the
substance of what the tool's own description promises. A wrapper may select
narrowly on purpose. This script names candidates.

USAGE
    python scripts/audit_upstream_field_coverage.py --pattern complex_portal
    python scripts/audit_upstream_field_coverage.py --tools ClinVar_get_submitted_records
    python scripts/audit_upstream_field_coverage.py --shard 0/8 --json-output cov.json

In the weekly sweep it rides on a call the sweep already makes, so the marginal
cost is the comparison, not the request.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
# Upstream fields are enumerated to MAX_DEPTH, which keeps the report readable.
# What the caller RECEIVED is read much deeper, because a value that reached
# them is a survivor however deep the wrapper nests it -- and wrappers nest
# deeper than the API does. Measured: the by-rsID variation output puts a
# disease's OMIM id at depth 9 (data > entries > features > associations >
# db_references > database), so at a shared limit of 8 its 132 values were
# invisible and all three `dbReferences` fields read as dropped while the
# caller had them.
MAX_DEPTH = 8
SURVIVOR_DEPTH = 24
MIN_VALUE_LENGTH = 2  # one-character values match by accident


def leaf_values(node, out=None, depth=0, limit=SURVIVOR_DEPTH):
    """Scalar leaf values reachable from `node`, as a list of strings."""
    if out is None:
        out = []
    if depth > limit:
        return out
    if isinstance(node, dict):
        for value in node.values():
            leaf_values(value, out, depth + 1, limit)
    elif isinstance(node, list):
        for value in node:
            leaf_values(value, out, depth + 1, limit)
    elif node is None or isinstance(node, bool):
        pass
    else:
        text = str(node).strip()
        if len(text) >= MIN_VALUE_LENGTH:
            out.append(text)
    return out


def leaf_fields(node, prefix="", out=None, depth=0):
    """`{field path: [leaf values]}` for a nested structure.

    List indices are collapsed, so every element of `participants` contributes
    to `participants[].bioRole` rather than to 30 separate paths.
    """
    if out is None:
        out = {}
    if depth > MAX_DEPTH:
        return out
    if isinstance(node, dict):
        for key, value in node.items():
            leaf_fields(value, f"{prefix}.{key}" if prefix else key, out, depth + 1)
    elif isinstance(node, list):
        for value in node:
            leaf_fields(value, f"{prefix}[]", out, depth + 1)
    elif node is None or isinstance(node, bool):
        pass
    else:
        text = str(node).strip()
        if len(text) >= MIN_VALUE_LENGTH:
            out.setdefault(prefix, []).append(text)
    return out


def record_count(node, limit=SURVIVOR_DEPTH):
    """How many records a structure holds: the SHALLOWEST list of dicts in it.

    A proxy, and a deliberately crude one. It exists to tell a response that
    was CUT from one that was not, which is the difference between a field the
    wrapper dropped and a field whose values all sit in rows the caller was
    told it would not get.

    Shallowest, not largest. With the largest, one record carrying a longer
    inner list than the record list itself decided the answer: a MaveDB
    score-set search answers 44 score sets and one of their papers has 100
    authors, so "largest" read the author list as the record count on both
    sides and the comparison said nothing was cut.
    """
    frontier = [node]
    for _ in range(limit):
        if not frontier:
            return 0
        best = 0
        children = []
        for item in frontier:
            if isinstance(item, dict):
                children.extend(item.values())
            elif isinstance(item, list):
                if sum(1 for element in item if isinstance(element, dict)) > 1:
                    best = max(best, len(item))
                children.extend(item)
        if best:
            return best
        frontier = children
    return 0


def normalise_key(name):
    """`max_pH`, `maxPh` and `max-ph` all collapse to one spelling."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def key_names(node, out=None, depth=0, limit=SURVIVOR_DEPTH):
    """Every dict key reachable from `node`, normalised."""
    if out is None:
        out = set()
    if depth > limit:
        return out
    if isinstance(node, dict):
        for key, value in node.items():
            out.add(normalise_key(str(key)))
            key_names(value, out, depth + 1, limit)
    elif isinstance(node, list):
        for value in node:
            key_names(value, out, depth + 1, limit)
    return out


# Paths that are not the record, whatever the API. Each is a structural class
# -- transport, search machinery, link construction, audit trail -- and not a
# guess about whether some field matters. They are reported under
# `not_record_data` rather than dropped, so a wrong call here is visible.
NOT_RECORD_DATA = re.compile(
    r"""(?x)
    (^|\.)_?links?(\.|\[|$)                  # HATEOAS
  | (^|\.)relationships(\.|\[)                # JSON:API relationship stubs
  | (^|\.)data\[\]\.type$                       # JSON:API resource type, which
                                                # restates the endpoint
  | (^|\.)self$
  | [Rr]esourceDescriptorPage                   # URL templates for a curie,
                                                # including Alliance's
                                                # homepageResourceDescriptorPage
  | (^|\.)urlTemplate$ | idPattern$ | idExample$ | resourcePages
  | supplementalData\.distinctFieldValues      # search facet values
  | (^|\.)aggregations(\.|\[)                 # search facet counts
  | (^|\.)facets?(\.|\[)                      # ENCODE portal facet terms
  | (^|\.)facet_fields(\.|\[)                  # Monarch's name for the same
  | (^|\.)facet_groups(\.|\[)                 # how the portal groups them
  | (^|\.)(filters|clear_filters)(\.|\[|$)    # the query as the portal echoes it
  | (^|\.)(columns|sort|notification)(\.|\[|$)  # portal result-table state
  | (^|\.)highlight(s|ing)?(\.|\[)             # search result highlighting
  | (^|\.)subsets?(\.|\[|$)                   # ontology subset tags
  | (^|\.)grouping_key$                        # Monarch's internal row key
  | ((^|\.)|_)namespace$                        # the curie prefix, derivable
  | (^|\.)alternativeUrl$                       # a second link to what url
                                                # already points at
  | _links?(\.|\[)                             # {id, url} link objects beside
                                                # the field they link
  | (^|\.)(created|updated|modified|lastModified|lastUpdated)By(\.|\[|$)
                                                # audit trail
  | (^|\.)(creationDate|modificationDate|dateCreated|dateUpdated)$
                                                # and its timestamps
  | (^|\.)recordType$                          # MaveDB's type discriminator:
                                                # ShortTargetGene,
                                                # PublicationIdentifier,
                                                # ClinicalControlWithClinvarLinks
  | _searchable(\[\])?$ | _closure            # Solr expansions
  | (^|\.)(_score|_version_|maxScore|numFound|QTime|responseHeader)$
    # bigBed display columns. `reserved` is the item RGB -- "0,176,240" for a
    # cCRE whose `cCRE_class` the tool does return -- and thickStart/thickEnd
    # are where the thick box is drawn. `bin` is UCSC's genomic index; a real
    # histogram bin is named bins[] or bin_count, not a bare `bin` beside
    # chromStart.
  | (^|\.)(reserved|thickStart|thickEnd|itemRgb|blockCount|blockSizes|chromStarts|bin)$
  | [Dd]efinition(\[\])?$                     # paragraphs of ontology prose
  | (^|\.)(translationstack|translationset|idlist|uids?|webenv|querykey)(\.|\[|$)
  | (^|\.)(page|per_page|pageSize|page_size|total_pages|pageInfo)(\.|\[|$)
  | (^|\.)@                                   # JSON-LD framing
    # GlyGen serves its own web tables with the record. `section_stats` is the
    # per-table row counts and column list the site renders, `sort_fields` is
    # which of those columns are sortable, and `hit_info.contributions` is the
    # breakdown of a relevance score into field, weight and contribution --
    # why this hit ranked where it did, not anything about the glycan.
  | (^|\.)section_stats(\.|\[)
  | (^|\.)sort_fields(\.|\[|$)
  | (^|\.)hit_info(\.|\[)
    # The bitmask that drives those tables' facet filters:
    # "0001000.1101111.100000.000000000001000000.1100000000000.100.00000".
  | (^|\.)filter_code$
    # PubChem's display order for the references it attaches to a record.
  | (^|\.)SortOrder$
    # Alliance embeds the Java class of each nested object as `type`:
    # "Reference" on an evidenceItem, "Gene" on a subject, "DataProvider" on
    # a provider. Scoped to those containers on purpose -- a bare `type` IS
    # the record elsewhere, as it is on a UDI identifier ("Primary") or an
    # interaction type.
  | (^|\.)(evidenceItem|evidence|dataProvider|subjectGene|objectGene
         |geneAssociationSubject|geneGeneAssociationObject
         |phenotypeAnnotationSubject|expressionAnnotationSubject
         |inferredGene|subject|relation
         |expressionPattern|whenExpressed|whereExpressed
         |crossReferences|references)(\[\])?\.type$
    # The same tag on the allele/model/variant containers of Alliance's
    # allele-and-model response. Anchored on `results[].` rather than added to
    # the list above, because a bare `gene.type` or `allele.type` elsewhere
    # could be a biotype or an allele class rather than a Java class name.
  | ^results\[\]\.(allele|model|gene)\.type$
  | ^results\[\]\.variantList\[\]\.type$
  | (^|\.)variantGenomicLocationAssociationObject\.type$
    # Alliance's own concatenated row key, and the display map it returns
    # keyed by the gene the caller asked about.
  | (^|\.)uniqueId$
  | (^|\.)geneAnnotationsMap(\.|\[)
    # Display variants of a species name Alliance already gives in full, and
    # its provider-side cross-reference stub.
  | (^|\.)taxon\.species\.(abbreviation|displayName|shortName|phylogeneticOrder)$
  | (^|\.)dataProviderCrossReference(\.|\[)
    # Alliance's display ordering, a map keyed by taxon id.
  | (^|\.)speciesOrder(\.|\[)
  | (^|\.)phylogeneticSortingIndex$
    # USDA's per-state map extents. The fact is which states the plant occurs
    # in; the four corners are for drawing the map, like bigBed's thickStart.
  | (^|\.)MapCoordinates\[\]\.(XMin|YMin|XMax|YMax)$
    # cBioPortal's base64 internal row keys, derivable from the sample and
    # study ids it returns beside them, and a colour for its own UI.
  | (^|\.)unique(Patient|Sample)Key$
    # PubChem's drawing of a molecule: the 2D/3D conformer coordinates, the
    # bond table they are drawn from, and the release/version stamp on each
    # computed property. The structure itself is the SMILES and the InChI,
    # which these tools do return.
  | PC_Compounds\[\]\.(coords|bonds|atoms|stereo)(\.|\[)
  | PC_Compounds\[\]\.props\[\]\.urn\.
                                                # (release, version, software,
                                                # source, implementation: the
                                                # stamp on a computed property,
                                                # not the property)
    # MeSH's own term record, fetched only to turn a disease id into a label:
    # its qualifiers ("drug therapy", "genetics") and related terms are not
    # the metabolite-disease association being answered.
  | (^|\.)(qualifiers|terms)\[\]\.(resource|label)$
    # A licence notice on a response block, which several BioThings APIs
    # attach under an underscore-prefixed key.
  | (^|\.)_license$
    # Reactome's own edit log: who changed an instance and when, which is
    # curation history rather than the pathway.
  | (^|\.)updateTrackers(\.|\[)
  | (^|\.)dedicatedColor$
    # ITIS's JSON service stamps the Java class of every nested object onto
    # it: "gov.usgs.itis.itis_service.data.SvcScientificName" on a name,
    # SvcHierarchyRecord on a rank, SvcTaxonPublication on a reference. It is
    # the serialiser's own type tag. Scoped to ITIS's list containers,
    # because `class` elsewhere is a taxonomic rank -- GBIF answers
    # "class": "Aves", which is the record.
  | (^|\.)(scientificNames|commonNames|hierarchyList|synonyms|publications
         |experts|otherSources|geoDivisions|jurisdictionalOrigins|comments
         |acceptedNames|referenceFor)(\[\])?\.class$
    # The Elasticsearch envelope ChEBI's advanced_search returns each hit in:
    # the index it came from (chebi-prod-compounds-07112026), the Lucene doc
    # type, and the internal structure-row ids. `_id` restates the accession
    # the hit already carries and `_score` is the ranking, which the tool now
    # reports as relevance_score.
  | (^|\.)_(index|type)$
  | (^|\.)_source\.structures(\[|$)
    """
)


def is_record_data(field):
    """False when a field path is transport, search machinery or an audit trail."""
    return not NOT_RECORD_DATA.search(field)


def key_names_raw(node, out=None, depth=0, limit=SURVIVOR_DEPTH):
    """Every dict key reachable from `node`, unnormalised."""
    if out is None:
        out = set()
    if depth > limit:
        return out
    if isinstance(node, dict):
        for key, value in node.items():
            out.add(str(key).strip())
            key_names_raw(value, out, depth + 1, limit)
    elif isinstance(node, list):
        for value in node:
            key_names_raw(value, out, depth + 1, limit)
    return out


# A numeric `id` beside one of these is the database's own row number, and the
# identifier that means something is the sibling. `urn` is MaveDB's: every
# record carries both, and only the urn can be passed back to the API.
STUB_SIBLINGS = (
    "link",
    "display_name",
    "format_name",
    "href",
    "url",
    "urn",
    # RGD's accession, which its own REST paths take where `key` is only a
    # row number.
    "rgdId",
)


# The field names a database uses for its own row number, beside the
# identifier that means something. RGD answers both on every record: `key` is
# the row and `rgdId` is the accession its own URLs take.
SURROGATE_NAMES = ("id", "key")


def surrogate_id_paths(node, prefix="", out=None, depth=0):
    """Paths of a bare numeric `id` or `key` beside a link or a real identifier.

    An entity stub -- SGD answers `{"id": 823128, "display_name": "CAA84998.1",
    "link": "/locus/S000000259"}` for every referenced object -- carries the
    database's own row number alongside the identifier that means something.
    The row number reaches no caller and should not: the wrapper reads the
    SGDID out of `link`. Scoped to this shape on purpose, because a bare
    numeric `id` IS the identifier in other APIs (a PubChem CID, an OMIM
    number), and those records do not carry a `link` beside it.
    """
    if out is None:
        out = set()
    if depth > MAX_DEPTH:
        return out
    if isinstance(node, dict):
        for name in SURROGATE_NAMES:
            value = node.get(name)
            if (
                isinstance(value, (int, float))
                or (isinstance(value, str) and value.strip().isdigit())
            ) and (
                any(node.get(sibling) for sibling in STUB_SIBLINGS)
                # RGD's annotation rows carry no bare `rgdId`; they carry
                # `annotatedObjectRgdId` and `refRgdId`, which are the
                # accessions its own URLs take, beside a `key` that is the
                # row number. Any sibling in that family counts.
                or any(
                    sibling.endswith("RgdId") and node.get(sibling)
                    for sibling in node
                )
            ):
                out.add(f"{prefix}.{name}" if prefix else name)
        for key, child in node.items():
            surrogate_id_paths(
                child, f"{prefix}.{key}" if prefix else key, out, depth + 1
            )
    elif isinstance(node, list):
        for child in node:
            surrogate_id_paths(child, f"{prefix}[]", out, depth + 1)
    return out


def compare(upstream, returned):
    """Per upstream field: how many of its leaf values reached the caller.

    `mapped` records the second signal, which exists because value survival
    alone has a false positive the first sampled run spent time on. MediaDive's
    wrapper does carry `description` and `reference`; on the rows that matched
    'nutrient agar' both are null upstream, so they have no value to survive and
    scored 0/68 and 0/36 while being fully exposed. A field whose own name
    reaches the caller was selected, whatever this page happened to hold, so it
    is reported apart from the fields the wrapper never asked for.
    """
    # Object KEYS count as survivors, because pivoting a long-format response
    # into a map is how a wrapper legitimately exposes it.
    # `OmniPath_get_annotation_resource_geneset` turns rows of
    # {label, value} into `annotations: {<label>: <value>}`, so every one of
    # 9,755 `label` values reaches the caller as a key and none of them as a
    # value. Diffing values alone called that the largest drop in the
    # catalogue.
    survivors = set(leaf_values(returned)) | {
        key for key in key_names_raw(returned) if len(key) >= MIN_VALUE_LENGTH
    }
    present = key_names(returned)
    # A value can also reach the caller as a KEY whose spelling the wrapper
    # normalised. cBioPortal's survival records are long-format rows of
    # {clinicalAttributeId: "OS_MONTHS", value: 31.1}, and the wrapper pivots
    # them into `os_months` -- the attribute NAME reaches the caller as a key, in
    # a different case and with a different separator, so neither the raw
    # value diff nor the raw key set matched it.
    normalised_keys = {normalise_key(key) for key in key_names_raw(returned)}

    def reached(value):
        """Did this upstream value reach the caller, prefix or no prefix?

        A wrapper that strips a curie prefix has not dropped the field.
        WormBase's `_wb_id` turns "WB:WBGene00006818" into "WBGene00006818",
        and Alliance answers `primaryExternalId` in the prefixed form, so the
        value diff reported it as missing on every row of every WormBase tool
        while it was plainly there.
        """
        if value in survivors:
            return True
        if normalise_key(value) in normalised_keys:
            return True
        head, _, tail = value.partition(":")
        return bool(tail) and len(tail) >= MIN_VALUE_LENGTH and tail in survivors

    rows = []
    for field, values in leaf_fields(upstream).items():
        kept = sum(1 for value in values if reached(value))
        leaf = normalise_key(field.rstrip("[]").split(".")[-1].rstrip("[]"))
        rows.append({"field": field, "kept": kept, "total": len(values), "leaf": leaf})

    # A leaf name that already reaches the caller from SOME other upstream path
    # explains the key match on its own, so it cannot excuse this path. GEO's
    # esummary carries `accession` twice: the series' own, which the tool
    # returns, and `samples[].accession`, which it drops. Without this the
    # series accession would vouch for the sample accessions.
    explained = {row["leaf"] for row in rows if row["kept"]}
    for row in rows:
        row["mapped"] = row["leaf"] in present and row["leaf"] not in explained
        del row["leaf"]
    rows.sort(key=lambda r: (r["kept"] / r["total"], -r["total"]))
    return rows


SELF_DESCRIPTION = re.compile(
    r"/(schema|openapi|swagger|_mapping|api-docs|metadata/fields)(\.json)?/?$",
    re.IGNORECASE,
)


def describes_the_api_not_a_record(call):
    """True when a captured response is the API describing itself.

    A tool may fetch its endpoint's own field list beside the data. ChEMBL's
    wrappers call `/molecule/CHEMBL25.json` and then
    `/molecule/schema.json`, and that second document's leaf values are FIELD
    NAMES -- `ordering`, `fields.molecule_properties.schema.filtering.ro3_pass`
    -- which of course never reach the caller. Diffing it reported all 20
    ChEMBL tools as dropping data and none of them were: it is the largest
    single false-positive class in the catalogue after pagination.

    An OPTIONS request is the same thing by another route.
    """
    if (call.get("method") or "").upper() == "OPTIONS":
        return True
    return bool(SELF_DESCRIPTION.search(call.get("url") or ""))


def record_http():
    """Patch requests so every JSON response body is kept. Returns (list, undo)."""
    import requests

    captured = []
    original = requests.Session.send

    def send(self, request, **kwargs):
        response = original(self, request, **kwargs)
        try:
            body = response.json()
        except Exception:
            body = None
        captured.append(
            {
                "method": request.method,
                "url": request.url.split("?")[0],
                "status": response.status_code,
                "body": body,
            }
        )
        return response

    requests.Session.send = send
    return captured, lambda: setattr(requests.Session, "send", original)


def _emit(finding, on_result):
    if on_result is not None:
        on_result(finding)
    return finding


def tool_configs(names=None, pattern=None):
    found = {}
    for path in sorted((REPO / "src" / "tooluniverse" / "data").glob("*.json")):
        try:
            entries = json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(entries, list):
            continue
        for cfg in entries:
            if not isinstance(cfg, dict) or "name" not in cfg:
                continue
            if names and cfg["name"] not in names:
                continue
            if pattern and pattern.lower() not in (
                cfg["name"].lower() + " " + path.name.lower()
            ):
                continue
            if cfg.get("test_examples"):
                found[cfg["name"]] = cfg
    return found


def select_shard(names, spec):
    if not spec:
        return names
    index, count = (int(part) for part in spec.split("/"))
    return [
        name for position, name in enumerate(sorted(names)) if position % count == index
    ]


def audit(
    names=None,
    pattern=None,
    limit=None,
    shard=None,
    min_values=4,
    on_result=None,
):
    """Audit each tool, reporting through `on_result` as each one lands.

    Incremental by design, for the reason the sweep itself is sharded: a run
    killed part-way must still yield what it measured. A 45-minute step that
    prints only at the end yields nothing when it is cut off.
    """
    sys.path.insert(0, str(REPO / "src"))
    from tooluniverse import ToolUniverse

    configs = tool_configs(names, pattern)
    chosen = select_shard(list(configs), shard)
    if limit:
        chosen = chosen[:limit]
    if not chosen:
        return []

    findings = []
    universe = ToolUniverse()
    universe.load_tools(include_tools=chosen)

    for name in chosen:
        config = configs[name]
        example = config["test_examples"][0]
        captured, undo = record_http()
        try:
            result = universe.run({"name": name, "arguments": example})
        except Exception as exc:
            undo()
            findings.append(
                _emit(
                    {"tool": name, "skipped": f"{type(exc).__name__}: {exc}"}, on_result
                )
            )
            continue
        finally:
            undo()

        if not isinstance(result, dict) or result.get("status") == "error":
            findings.append(
                _emit(
                    {"tool": name, "skipped": "the tool returned an error"}, on_result
                )
            )
            continue
        calls = [c for c in captured if isinstance(c["body"], (dict, list))]
        described = [c for c in calls if describes_the_api_not_a_record(c)]
        calls = [c for c in calls if not describes_the_api_not_a_record(c)]
        if not calls:
            findings.append(
                _emit(
                    {
                        "tool": name,
                        "skipped": "no JSON upstream response"
                        + (
                            " that is not the API describing itself"
                            if described
                            else ""
                        ),
                    },
                    on_result,
                )
            )
            continue

        # The WHOLE envelope, not just `data`. A wrapper's metadata is part
        # of what the caller is handed, and it is where this sweep's own
        # fixes put several things that belong there: the plant a USDA symbol
        # resolved to, a pagination disclosure, a note that a page was cut.
        # Comparing against `data` alone scored those as dropped.
        returned = result
        thin = []
        mapped_but_unseen = []
        not_record_data = []
        sparse_behind_a_cut = []
        # Calls to the SAME URL are one logical response. A tool that pages
        # through an endpoint makes several, and comparing each against the
        # single merged output reported the same field once per page with a
        # different total each time -- `datasourceScores[].id` five times over
        # on every disease_target_score tool -- and scored page 1's rows as
        # dropped because the output holds a later page's. Grouped, a value
        # that reached the caller from any page counts.
        by_url = {}
        for call in calls:
            by_url.setdefault(call["url"], []).append(call["body"])

        for url, bodies in by_url.items():
            body = bodies[0] if len(bodies) == 1 else bodies
            surrogates = surrogate_id_paths(body)
            # Was the response cut, and by how much? A tool with a declared
            # `limit` returns fewer records than the endpoint answered, and a
            # field that is not on every record then has a way of scoring zero
            # while being carried perfectly: none of its values happened to
            # fall in the rows the caller got. DisGeNET's VDA example asks for
            # 20 of 100 associations, and `alleles_ref` is multi-character on
            # 14 of them -- all 14 outside the page -- so a field the wrapper
            # does return read as dropped. The mapped-but-unseen signal cannot
            # catch it either, because the wrapper also renames the field.
            upstream_records = record_count(body)
            returned_records = record_count(returned)
            was_cut = upstream_records > returned_records > 0
            for row in compare(body, returned):
                row["url"] = url
                if row["total"] < min_values:
                    continue  # a single value that moved is a rename, not a loss
                # Zero survivors, not a low ratio. A ratio flags PAGINATION:
                # MediaDive's upstream answers 3,344 media and the tool returns
                # a page of 20, so `data[].name` scored 20/3344 and read as a
                # loss while the field is plainly exposed. That is the row axis,
                # which #824 already discloses. A field the wrapper drops has
                # NO surviving value; a field it exposes has at least the
                # current page's.
                if row["kept"]:
                    continue
                # ... unless the page it exposes is all nulls. Then the field is
                # selected and has nothing to show, which is the upstream being
                # sparse, not the wrapper dropping anything.
                if row["field"] in surrogates or not is_record_data(row["field"]):
                    not_record_data.append(row)
                elif was_cut and row["total"] < upstream_records:
                    row["upstream_records"] = upstream_records
                    row["returned_records"] = returned_records
                    sparse_behind_a_cut.append(row)
                elif row["mapped"]:
                    mapped_but_unseen.append(row)
                else:
                    thin.append(row)
        thin.sort(key=lambda r: -r["total"])
        mapped_but_unseen.sort(key=lambda r: -r["total"])
        not_record_data.sort(key=lambda r: -r["total"])
        sparse_behind_a_cut.sort(key=lambda r: -r["total"])
        findings.append(
            _emit(
                {
                    "tool": name,
                    "upstream_calls": len(captured),
                    "urls": sorted({c["url"] for c in calls})[:3],
                    "self_description_urls": sorted({c["url"] for c in described})[:3],
                    "thin_fields": thin[:12],
                    "mapped_but_unseen": mapped_but_unseen[:12],
                    "not_record_data": not_record_data[:12],
                    "sparse_behind_a_cut": sparse_behind_a_cut[:12],
                },
                on_result,
            )
        )
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", nargs="*")
    parser.add_argument("--pattern")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--shard", help="i/n, to split the catalogue across jobs")
    parser.add_argument(
        "--min-values",
        type=int,
        default=4,
        help="ignore upstream fields with fewer leaf values",
    )
    parser.add_argument("--json-output")
    args = parser.parse_args()

    # Print and persist as each tool lands. A step that is cut off -- a
    # 45-minute budget, an evicted runner -- still leaves everything it
    # measured, which is the lesson the sweep's own sharding records.
    def report(finding):
        if "thin_fields" not in finding:
            print(
                f"  skip  {finding['tool']:44s} {finding['skipped'][:60]}", flush=True
            )
            return
        rows = finding["thin_fields"]
        label = "THIN" if rows else "ok  "
        detail = ", ".join(f"{r['field']} {r['kept']}/{r['total']}" for r in rows[:5])
        sparse = finding.get("mapped_but_unseen") or []
        if sparse and not rows:
            detail = f"({len(sparse)} selected field(s) null on this page)"
        print(f"  {label}  {finding['tool']:44s} {detail}", flush=True)
        if args.json_output:
            pathlib.Path(args.json_output).write_text(json.dumps(seen, indent=2))

    seen = []

    def on_result(finding):
        seen.append(finding)
        report(finding)

    findings = audit(
        args.tools,
        args.pattern,
        args.limit,
        args.shard,
        args.min_values,
        on_result=on_result,
    )
    audited = [f for f in findings if "thin_fields" in f]
    with_loss = [f for f in audited if f["thin_fields"]]
    print(
        f"\naudited {len(audited)} tool(s); {len(with_loss)} carry an upstream "
        f"field whose values mostly do not reach the caller"
    )
    if args.json_output:
        pathlib.Path(args.json_output).write_text(json.dumps(findings, indent=2))
        print("wrote", args.json_output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
