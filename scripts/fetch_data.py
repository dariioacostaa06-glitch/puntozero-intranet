#!/usr/bin/env python3
"""
Regenera data.json con info actualizada de los repos de PuntoZero.

Cubre a los dos cofounders. Para cada repo extrae descripción, lenguajes,
URL de Pages, último commit y topics.

Uso:
    python3 scripts/fetch_data.py

Requiere `gh` CLI autenticada.
"""
import datetime
import json
import subprocess
import sys
from pathlib import Path

# Si añadís más cofounders en el futuro, aquí.
COFOUNDERS = [
    {"login": "dariioacostaa06-glitch", "name": "Darío Acosta",        "role": "Software & Producto"},
    {"login": "alexestepagallego",      "name": "Alex Estepa Gallego", "role": "Negocio & Clientes"},
]
OUT = Path(__file__).parent.parent / "data.json"


def gh_json(args, default=None):
    try:
        return json.loads(subprocess.check_output(["gh"] + args, stderr=subprocess.DEVNULL))
    except Exception:
        return default if default is not None else {}


def get_user_avatar(login):
    return gh_json(["api", f"users/{login}"]).get("avatar_url", "")


def list_repos_of(login):
    """Devuelve todos los repos públicos de un usuario (su propio listado)."""
    return gh_json(["api", f"users/{login}/repos?per_page=100&sort=updated"], default=[])


def enrich(repo, owner_login):
    """Pide a la API los detalles que no vienen en /users/X/repos."""
    name = repo["name"]
    # Languages full breakdown
    langs_raw = gh_json(["api", f"repos/{owner_login}/{name}/languages"])
    total = sum(langs_raw.values()) or 1
    langs = sorted(
        [(k, round(v * 100 / total)) for k, v in langs_raw.items()],
        key=lambda x: -x[1],
    )
    # Pages
    pages = gh_json(["api", f"repos/{owner_login}/{name}/pages"])
    pages_url = pages.get("html_url", "") if isinstance(pages, dict) else ""
    # Latest commit
    commits = gh_json(["api", f"repos/{owner_login}/{name}/commits?per_page=1"], default=[])
    last = commits[0] if commits else {}
    commit = last.get("commit") or {}
    commit_msg = (commit.get("message", "").split("\n")[0])[:100]
    commit_author = (commit.get("author") or {}).get("name", "")
    commit_date = (commit.get("author") or {}).get("date", "")
    topics = repo.get("topics") or []
    return {
        "owner": owner_login,
        "name": name,
        "description": repo.get("description") or "",
        "url": repo["html_url"],
        "visibility": "PRIVATE" if repo.get("private") else "PUBLIC",
        "language": repo.get("language") or "",
        "languages": langs,
        "topics": topics,
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "pushed_at": repo.get("pushed_at", ""),
        "homepage": repo.get("homepage") or "",
        "pages_url": pages_url,
        "last_commit_msg": commit_msg,
        "last_commit_author": commit_author,
        "last_commit_date": commit_date,
        "archived": repo.get("archived", False),
        "fork": repo.get("fork", False),
    }


def main():
    # Cargar config previa para preservar overrides (incluido el blob cifrado)
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
        except Exception:
            prev = {}
    hidden_repos = prev.get("hidden_repos", [])
    encrypted = prev.get("encrypted")  # blob privado cifrado, no se toca

    cofounders_full = []
    for c in COFOUNDERS:
        avatar = get_user_avatar(c["login"])
        cofounders_full.append({**c, "avatar": avatar})

    seen = set()
    all_repos = []
    for c in COFOUNDERS:
        login = c["login"]
        print(f"→ {login}")
        repos = list_repos_of(login)
        for r in repos:
            key = (login, r["name"])
            if key in seen:
                continue
            seen.add(key)
            print(f"   · {r['name']}")
            all_repos.append(enrich(r, login))

    data = {
        "schema": 2,
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "company": "PuntoZero",
        "cofounders": cofounders_full,
        "hidden_repos": hidden_repos,
        "repos": all_repos,
    }
    if encrypted:
        data["encrypted"] = encrypted
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\n✓ {OUT} actualizado · {len(all_repos)} repos · {len(cofounders_full)} cofounders")


if __name__ == "__main__":
    main()
