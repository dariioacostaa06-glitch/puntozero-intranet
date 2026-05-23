#!/usr/bin/env python3
"""
Regenera data.json con info actualizada de los repos de PuntoZero.

Uso:  python3 scripts/fetch_data.py
Requiere `gh` CLI autenticada.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

OWNER = "dariioacostaa06-glitch"
OUT = Path(__file__).parent.parent / "data.json"


def gh_json(args, default=None):
    try:
        return json.loads(subprocess.check_output(["gh"] + args, stderr=subprocess.DEVNULL))
    except Exception:
        return default if default is not None else {}


def main():
    print("→ listando repos…")
    repos = gh_json([
        "repo", "list", "--json",
        "name,description,visibility,primaryLanguage,pushedAt,homepageUrl,url,"
        "stargazerCount,forkCount,isFork,isArchived,repositoryTopics",
        "--limit", "100",
    ], default=[])

    if not repos:
        print("❌ No se han encontrado repos. ¿Está `gh` autenticado?")
        sys.exit(1)

    out = []
    for r in repos:
        name = r["name"]
        print(f"  · {name}")

        langs_raw = gh_json(["api", f"repos/{OWNER}/{name}/languages"])
        total = sum(langs_raw.values()) or 1
        langs = sorted([(k, round(v * 100 / total)) for k, v in langs_raw.items()],
                       key=lambda x: -x[1])

        pages = gh_json(["api", f"repos/{OWNER}/{name}/pages"])
        pages_url = pages.get("html_url", "") if isinstance(pages, dict) else ""

        commits = gh_json(["api", f"repos/{OWNER}/{name}/commits?per_page=1"], default=[])
        last = commits[0] if commits else {}
        commit_msg = (last.get("commit") or {}).get("message", "").split("\n")[0][:100]
        commit_author = (last.get("commit") or {}).get("author", {}).get("name", "")
        commit_date = (last.get("commit") or {}).get("author", {}).get("date", "")

        out.append({
            "name": name,
            "description": r.get("description") or "",
            "url": r["url"],
            "visibility": r["visibility"],
            "language": (r.get("primaryLanguage") or {}).get("name", ""),
            "languages": langs,
            "topics": [t["name"] for t in (r.get("repositoryTopics") or [])],
            "stars": r.get("stargazerCount", 0),
            "forks": r.get("forkCount", 0),
            "pushed_at": r.get("pushedAt", ""),
            "homepage": r.get("homepageUrl", ""),
            "pages_url": pages_url,
            "last_commit_msg": commit_msg,
            "last_commit_author": commit_author,
            "last_commit_date": commit_date,
            "archived": r.get("isArchived", False),
            "fork": r.get("isFork", False),
        })

    data = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "owner": OWNER,
        "company": "PuntoZero",
        "repos": out,
    }
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\n✓ {OUT} actualizado con {len(out)} repos")


if __name__ == "__main__":
    main()
