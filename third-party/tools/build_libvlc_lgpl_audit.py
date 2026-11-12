"""Audit the exact Android static plugin selection against source primary grants.

Run after the pinned official build. The grant inventory is created from the
matching VLC source archive, not from strings embedded in shared objects.
"""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path


def audit(source, build, inventory, output):
    grants = json.loads(inventory.read_text(encoding="utf-8"))
    if (source / ".git").is_dir():
        revision = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    else:
        manifest = json.loads((source.parent / "build-source-manifest.json").read_text())
        revision = manifest["source_refs"]["vlc"]
    if revision != grants["vlc_revision"]:
        raise ValueError("Source checkout and primary-grant inventory revisions differ")
    gpl_paths = {item["path"] for item in grants["gpl_primary_grant_files"]}
    output.mkdir(parents=True, exist_ok=True)
    rows_file = output / "selected-module-sources.tsv"
    query = output / "query-module-sources.mk"
    query.write_text(
        ".PHONY: aurora-module-inventory\n"
        "aurora-module-inventory:\n"
        f"\t$(file >{rows_file.as_posix()},)\n"
        f"\t$(foreach module,$(LTLIBRARIES),$(file >>{rows_file.as_posix()},"
        "$(module)|$($(subst .,_,$(subst -,_,$(notdir $(module))))_SOURCES)|"
        "$(nodist_$(subst .,_,$(subst -,_,$(notdir $(module))))_SOURCES)|"
        "$($(subst .,_,$(subst -,_,$(notdir $(module))))_LIBADD)))\n"
        "\t@true\n", encoding="utf-8")
    subprocess.run(["make", "-s", "-C", str(build / "modules"), "-f", "Makefile",
                    "-f", str(query), "aurora-module-inventory"], check=True)
    generated = build / "ndk/libvlcjni-modules.c"
    if not generated.is_file():
        raise ValueError(f"Final module registration file missing: {generated}")
    registered = set(re.findall(r"^\s+vlc_entry__(\w+),", generated.read_text(), re.M))
    if not registered:
        raise ValueError("The built static module registration list is empty")
    plugins = []
    candidates = {}
    for row in rows_file.read_text().splitlines():
        if not row.strip():
            continue
        archive, sources, generated_sources, libadd = row.split("|", 3)
        filename = Path(archive).name
        name = filename[3:-10] if filename.startswith("lib") and filename.endswith("_plugin.la") else filename
        item = {"name": name, "archive": archive, "sources": sources.split(),
                "generated_sources": generated_sources.split(), "libadd": libadd.split()}
        item["gpl_primary_source_hits"] = [p for p in item["sources"]
                                          if "modules/" + p in gpl_paths]
        candidates[name] = item
        if name in registered:
            plugins.append(item)
    missing = sorted(registered - candidates.keys())
    hits = [item for item in plugins if item["gpl_primary_source_hits"]]
    required = {"ts", "mkv", "avcodec", "freetype", "libass", "mediacodec", "android_display"}
    report = {
        "vlc_revision": grants["vlc_revision"],
        "module_registration_sha256": hashlib.sha256(generated.read_bytes()).hexdigest(),
        "registered_plugin_count": len(registered),
        "gpl_primary_source_plugin_count": len(hits),
        "unmapped_registered_plugins": missing,
        "required_playback_plugins": {name: name in registered for name in sorted(required)},
        "registered_plugins": sorted(registered),
        "plugins": sorted(plugins, key=lambda item: item["name"]),
        "scope": "Primary-grant audit of declared selected module source files. Contrib configure flags and linked dependencies require the accompanying build provenance. Device playback is tested separately."
    }
    (output / "module-license-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if hits or missing or not all(report["required_playback_plugins"].values()):
        raise ValueError("Final static module audit requires review; see module-license-audit.json")
    print(json.dumps({"registered_plugins": len(registered), "gpl_source_hits": len(hits),
                      "required_playback_plugins": report["required_playback_plugins"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--build", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    audit(args.source, args.build, args.inventory, args.output)
