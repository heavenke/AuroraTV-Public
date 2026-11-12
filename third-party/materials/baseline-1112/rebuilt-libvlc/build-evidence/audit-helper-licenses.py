"""Audit actual selected plugins and recursively linked local helpers, read-only.

Uses the pinned upstream tarball and GNU make-expanded SOURCES/LIBADD data.
Quoted includes are followed only when they resolve to a real upstream file.
Unresolved/ambiguous includes remain explicit evidence gaps.
"""
import collections
import argparse
import json
import posixpath
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "vlc-lgpl-build"
SOURCE = ROOT / "artifacts" / "oss-public-sources" / "archives" / "vlc-c84ef1eda4f14f8b57a5b266b51c843cf51ed28b.tar.gz"
BLACKLIST = re.compile(r"^lib(?:dummy|rc|file_logger|syslog|lua|stream_out_cycle|stream_out_rtp|hqdn3d|rotate|deinterlace(?:_.*)?)_plugin\.la$")
GRANT = re.compile(r"under\s+the\s+terms\s+of\s+the\s+GNU\s+(?:(Lesser|Library)\s+)?General\s+Public\s+License", re.I)
INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--abi", choices=("arm64", "arm"), default="arm64")
parser.add_argument("--registered-only", action="store_true")
args = parser.parse_args()


def variable(archive):
    return posixpath.basename(archive).replace("-", "_").replace(".", "_")


rows = {}
for line in (ARTIFACTS / f"helper-module-sources-{args.abi}.tsv").read_text().splitlines():
    if not line.strip():
        continue
    name, sources, libs = line.split("|", 2)
    rows[name] = {"sources": sources.split(), "libadd": libs.split()}

if args.registered_only:
    audit_directory = ARTIFACTS / f"audit-{args.abi}"
    registered = json.loads((audit_directory / "module-license-audit.json").read_text())["registered_plugins"]
    plugins = {}
    for line in (audit_directory / "selected-module-sources.tsv").read_text().splitlines():
        if not line.strip():
            continue
        archive_name, sources, generated, libadd = line.split("|", 3)
        plugins[archive_name] = {"archive": archive_name, "sources": sources.split(), "generated_sources": generated.split(), "libadd": libadd.split()}
    selected = {"plugins": [plugins[f"lib{name}_plugin.la"] for name in registered]}
else:
    selected = json.loads((ARTIFACTS / "selected-module-license-arm64.json").read_text())
archive = tarfile.open(SOURCE, "r:gz")
members = {}
for item in archive.getmembers():
    if item.isfile():
        parts = item.name.split("/", 1)
        if len(parts) == 2:
            members[parts[1]] = item
basenames = collections.defaultdict(list)
for path in members:
    if path.startswith(("modules/", "include/", "src/")):
        basenames[posixpath.basename(path)].append(path)
cache = {}
# A single sequential pass avoids repeatedly decompressing the pinned tarball.
for path, member in members.items():
    if path.startswith(("modules/", "include/", "src/")) and member.size < 2_000_000:
        cache[path] = archive.extractfile(member).read().decode("utf-8", "replace")


def text(path):
    if path not in cache:
        cache[path] = archive.extractfile(members[path]).read().decode("utf-8", "replace")
    return cache[path]


def primary(path):
    # Ignore misleading received-copy footer and examine the license grant.
    match = GRANT.search(text(path)[:12000])
    if not match:
        return None
    return "LGPL" if match.group(1) else "GPL"


def source_path(path):
    value = posixpath.normpath("modules/" + path)
    return value if value in members else None


def includes(path, result, unresolved, ambiguous):
    if path in result:
        return
    result.add(path)
    for name in INCLUDE.findall(text(path)):
        candidates = []
        for base in (posixpath.dirname(path), "include", "modules", "src"):
            candidate = posixpath.normpath(posixpath.join(base, name))
            if candidate in members and candidate not in candidates:
                candidates.append(candidate)
        if not candidates:
            # Unique project-wide filenames can represent a configure include path.
            candidates = basenames.get(posixpath.basename(name), [])
        if len(candidates) == 1:
            includes(candidates[0], result, unresolved, ambiguous)
        elif len(candidates) > 1:
            ambiguous.add((path, name, tuple(candidates)))
        else:
            unresolved.add((path, name))


output = []
for plugin in selected["plugins"]:
    libs = set()
    pending = list(plugin["libadd"])
    sources = set(plugin["sources"] + plugin["generated_sources"])
    while pending:
        item = pending.pop()
        if not item.endswith(".la") or item in libs:
            continue
        libs.add(item)
        key = variable(item)
        regular = rows.get(key + "_SOURCES", {})
        generated = rows.get("nodist_" + key + "_SOURCES", {})
        sources.update(regular.get("sources", []))
        sources.update(generated.get("sources", []))
        pending.extend(regular.get("libadd", []))
    resolved, missing = set(), []
    unresolved, ambiguous = set(), set()
    for source in sources:
        path = source_path(source)
        if path:
            includes(path, resolved, unresolved, ambiguous)
        else:
            missing.append(source)
    hits = sorted(path for path in resolved if primary(path) == "GPL")
    output.append({
        "archive": plugin["archive"],
        "excluded_by_additional_blacklist": bool(BLACKLIST.match(plugin["archive"])),
        "recursive_helpers": sorted(libs),
        "resolved_source_and_quoted_include_count": len(resolved),
        "resolved_source_and_quoted_includes": sorted(resolved),
        "gpl_primary_grant_hits": hits,
        "generated_or_external_sources_not_in_upstream_archive": sorted(missing),
        "unresolved_quoted_includes": [list(x) for x in sorted(unresolved)],
        "ambiguous_quoted_includes": [list(x) for x in sorted(ambiguous)],
    })

result = {
    "vlc_revision": "c84ef1eda4f14f8b57a5b266b51c843cf51ed28b",
    "method": "GNU make-expanded selected plugin SOURCES/LIBADD, recursive local .la helper sources, recursively resolved quoted includes; primary under-the-terms grant only",
    "scope": f"{args.abi} {'final registered plugins' if args.registered_only else 'selected plugin candidates before additional blacklist'}; core/JNI/contrib audits are separate",
    "limitations": "Quoted include resolution uses source directory, known top-level include roots, then unique filename only. Ambiguous/generated/external references remain listed and are not silently classified.",
    "plugins": output,
    "additional_gpl_hits_in_retained_plugins": [
        {"archive": x["archive"], "hits": x["gpl_primary_grant_hits"]}
        for x in output if x["gpl_primary_grant_hits"] and not x["excluded_by_additional_blacklist"]
    ],
}
suffix = "-registered" if args.registered_only else ""
target = ARTIFACTS / f"recursive-helper-header-license-{args.abi}{suffix}.json"
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"plugins": len(output), "linked_helpers": len(set(h for p in output for h in p["recursive_helpers"])), "retained_plugins_with_gpl_primary_hits": result["additional_gpl_hits_in_retained_plugins"]}, ensure_ascii=False))
