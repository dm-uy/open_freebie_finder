"""NVIDIA's public Free Endpoint selection, intersected with its keyed catalog.

Catalog labels narrow pending probes only. They never certify an account tariff
or replace buffered/SSE qualification. All request destinations are owned constants.
"""
import json
import re

FREE_CATALOG_URL = "https://api.ngc.nvidia.com/v2/search/catalog/resources/ENDPOINT"
FREE_CATALOG_QUERY = json.dumps({"filters": [{"field": "label", "value": "nim_type_preview"}],
    "page": 0, "pageSize": 100, "query": "*"}, separators=(",", ":"))
SOURCE_REVISION = "nvidia_free_endpoint_chat_v1"


def intersect_free_chat(catalog, source):
    """Fail closed on partial/schema-changed sources; never guess API ID aliases."""
    from backend.app.core.discovery.orchestrator import CatalogFailure

    def invalid():
        raise CatalogFailure("invalid_nvidia_free_catalog")

    if not isinstance(catalog, dict) or not isinstance(catalog.get("data"), list):
        invalid()
    if any(catalog.get(k) for k in ("has_more", "next_cursor", "next")):
        raise CatalogFailure("incomplete_catalog")
    info = catalog.get("result_info", {})
    if not isinstance(info, dict) or info.get("total_pages", 1) != 1:
        raise CatalogFailure("incomplete_catalog")
    if len(catalog["data"]) > 1000:
        raise CatalogFailure("catalog_too_large")
    if not isinstance(source, dict) or not isinstance(source.get("results"), list):
        invalid()
    total = source.get("resultTotal")
    if type(total) is not int or not 0 <= total <= 1000:
        invalid()
    # The observed API supplies a separate _scored teaser; it is not a page.
    groups = [g for g in source["results"] if isinstance(g, dict) and g.get("groupValue") == "ENDPOINT"]
    if len(groups) != 1:
        invalid()
    group = groups[0]
    rows = group.get("resources")
    if not isinstance(rows, list):
        invalid()
    if source.get("resultPageTotal") != 1 or group.get("totalCount") != total or len(rows) != total:
        raise CatalogFailure("incomplete_nvidia_free_catalog")
    candidates = set()
    seen = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("resourceType") != "ENDPOINT":
            invalid()
        resource = row.get("resourceId")
        if not isinstance(resource, str) or not resource or len(resource) > 512:
            invalid()
        if resource in seen:
            if seen[resource] != row:
                raise CatalogFailure("conflicting_catalog")
            # A repeated resource cannot stand in for another missing row.
            raise CatalogFailure("incomplete_nvidia_free_catalog")
        seen[resource] = row
        labels, attributes = row.get("labels"), row.get("attributes")
        if not isinstance(labels, list) or not isinstance(attributes, list):
            invalid()
        label_map, attrs = {}, {}
        for label in labels:
            if not isinstance(label, dict) or not isinstance(label.get("key"), str):
                invalid()
            key = label["key"]
            if key in label_map and label_map[key] != label:
                raise CatalogFailure("conflicting_catalog")
            label_map[key] = label
        for attr in attributes:
            if not isinstance(attr, dict) or not isinstance(attr.get("key"), str):
                invalid()
            key = attr["key"]
            if key in attrs and attrs[key] != attr.get("value"):
                raise CatalogFailure("conflicting_catalog")
            attrs[key] = attr.get("value")
        general = label_map.get("general", {}).get("unresolvedValues")
        publishers = label_map.get("publisher", {}).get("values")
        if (not isinstance(general, list) or not all(isinstance(v, str) for v in general)
                or not isinstance(publishers, list) or len(publishers) != 1
                or not isinstance(publishers[0], str)):
            invalid()
        if (row.get("isPublic") is not True or attrs.get("AVAILABLE") != "true"
                or attrs.get("PREVIEW") != "true" or attrs.get("DEPRECATION")
                or "nim_type_preview" not in general or "playgroundtype_chat" not in general):
            continue
        publisher, name = publishers[0], row.get("name")
        # Only an exact publisher/name also returned by /v1/models is usable.
        # A slug such as glm-5-3 is never guessed to mean glm-5.3.
        if (not re.fullmatch(r"[a-zA-Z0-9_.-]{1,128}", publisher)
                or not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,256}", name)):
            continue
        candidates.add(publisher + "/" + name)
    selected = []
    for item in catalog["data"]:
        if not isinstance(item, dict):
            invalid()
        identifier = item.get("id")
        if isinstance(identifier, str) and identifier in candidates:
            selected.append({**item, "nvidia_catalog_source": SOURCE_REVISION})
    return {"data": selected}
