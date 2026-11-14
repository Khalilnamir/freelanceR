"""Radar de signaux B2B avec sources, traçabilité, scoring et brouillons.

Dépendances : bibliothèque standard de Python uniquement.
Ne collecte pas de profils privés et n'automatise pas LinkedIn.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import sqlite3
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "radar.sqlite3"
PROFILE_PATH = ROOT / "profile.json"

# Requêtes volontairement ciblées; modifiables dans l'interface.
DEFAULT_QUERIES = [
    '"plateforme data" "lancement" France',
    '"équipe data" "création" France',
    '"Snowflake" "migration" entreprise France',
    '"data" "recrutement" "équipe" France',
    '"intelligence artificielle" "projet" banque France',
    '"directeur data" "nomination" France',
    '"transformation data" entreprise France',
]

SIGNAL_PATTERNS = {
    "Création d'équipe": ["creation d'equipe", "nouvelle equipe", "equipe data", "data team", "recrute", "recrutement", "renforce son equipe"],
    "Projet / lancement": ["lance", "lancement", "deploie", "deploiement", "nouveau projet", "programme", "plateforme data", "data platform"],
    "Migration / modernisation": ["migration", "migre", "modernisation", "snowflake", "dbt", "cloud", "refonte"],
    "Mouvement de direction": ["nomination", "nomme", "depart", "quitte", "recrute un directeur", "nouveau cdo"],
    "Acquisition / réorganisation": ["acquisition", "fusion", "reorganisation", "levee de fonds", "rachat"],
    "Annonce CDI": ["cdi", "offre d'emploi", "hiring", "recrutement", "recrute"],
}

MATCH_GROUPS = {
    "Data Platform": ["snowflake", "dbt", "sql", "data platform", "plateforme data", "data engineering", "data engineer", "data vault", "analytics engineering", "migration", "pipeline", "etl", "business intelligence", "power bi"],
    "Product & Transformation": ["product owner", "po data", "roadmap", "transformation", "cadrage", "agile", "gouvernance", "data governance", "delivery", "strategie data", "pilotage", "organisation data"],
    "Data & AI": ["intelligence artificielle", "ia generative", "genai", "llm", "agent ia", "agents ia", "artificial intelligence", "ai product", "streamlit"],
}

SECTOR_TERMS = ["banque", "bancaire", "finance", "assurance", "logistique", "fintech", "industrie", "transport"]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def clean_markup(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", html.unescape(text or ""))).strip()


def load_profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path: Path | str = DB_PATH) -> None:
    with connect(db_path) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS signals (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL,
            publisher TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL UNIQUE,
            summary TEXT NOT NULL DEFAULT '',
            published TEXT NOT NULL DEFAULT '',
            discovered TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            score INTEGER NOT NULL,
            position TEXT NOT NULL,
            rationale TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'À qualifier',
            contact_name TEXT NOT NULL DEFAULT '',
            contact_role TEXT NOT NULL DEFAULT '',
            contact_email TEXT NOT NULL DEFAULT '',
            contact_source TEXT NOT NULL DEFAULT '',
            do_not_contact INTEGER NOT NULL DEFAULT 0,
            note TEXT NOT NULL DEFAULT ''
        )""")


def detect_signal(title: str, summary: str = "") -> str:
    text = normalize(title + " " + summary)
    matched = [(sum(k in text for k in words), typ) for typ, words in SIGNAL_PATTERNS.items()]
    best = max(matched)
    return best[1] if best[0] else "Signal à qualifier"


def score_signal(title: str, summary: str = "") -> tuple[int, str, str, str]:
    text = normalize(title + " " + summary)
    overlaps = {key: [term for term in terms if term in text] for key, terms in MATCH_GROUPS.items()}
    position = max(overlaps, key=lambda x: len(overlaps[x]))
    match_count = len(overlaps[position])
    unique_skill_matches = len(set(t for terms in overlaps.values() for t in terms))
    sector = any(term in text for term in SECTOR_TERMS)
    kind = detect_signal(title, summary)
    strong = kind in ("Création d'équipe", "Projet / lancement", "Migration / modernisation")
    # Score heuristique et explicable, pas une probabilité de mission.
    score = min(98, 15 + min(42, unique_skill_matches * 9) + (18 if strong else 7 if kind != "Signal à qualifier" else 0) + (10 if sector else 0) + (10 if match_count >= 2 else 0) + (5 if len(title) > 45 else 0))
    if unique_skill_matches == 0:
        score = min(score, 35)
    matched = ", ".join(sorted({x for xs in overlaps.values() for x in xs})[:6]) or "aucun mot-clé métier spécifique"
    reason = f"Signal : {kind}. Correspondances : {matched}. Secteur cible : {'oui' if sector else 'non détecté'}."
    return score, position, kind, reason


def parse_feed(xml_data: bytes, source: str = "Google News RSS") -> list[dict[str, str]]:
    root = ET.fromstring(xml_data)
    rows = []
    for node in root.findall(".//item"):
        def field(name: str) -> str:
            return (node.findtext(name) or "").strip()
        title = clean_markup(field("title"))
        url = field("link")
        if not title or not url.startswith(("https://", "http://")):
            continue
        publisher = clean_markup((node.findtext("source") or ""))
        summary = clean_markup(field("description"))[:1200]
        date_raw = field("pubDate")
        try:
            published = parsedate_to_datetime(date_raw).astimezone(timezone.utc).date().isoformat()
        except (ValueError, TypeError, OverflowError):
            published = ""
        rows.append({"title": title, "company": "", "source": source,
                     "publisher": publisher, "url": url, "summary": summary,
                     "published": published})
    return rows


def search_rss(query: str, timeout: int = 12) -> list[dict[str, str]]:
    params = urllib.parse.urlencode({"q": query, "hl": "fr", "gl": "FR", "ceid": "FR:fr"})
    url = f"https://news.google.com/rss/search?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "FreelanceRadarAI/0.1 (RSS reader)"})
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        data = resp.read(2_000_000)
    return parse_feed(data)


def insert_signal(data: dict[str, Any], db_path: Path | str = DB_PATH) -> bool:
    url = (data.get("url") or "").strip()
    title = (data.get("title") or "").strip()
    if not url.startswith(("https://", "http://")) or not title:
        raise ValueError("Titre et URL http(s) obligatoires")
    score, position, kind, reason = score_signal(title, data.get("summary", ""))
    identifier = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    with connect(db_path) as con:
        cur = con.execute("""INSERT OR IGNORE INTO signals
            (id, title, company, source, publisher, url, summary, published, discovered,
             signal_type, score, position, rationale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (identifier, title[:500], str(data.get("company", ""))[:180],
             str(data.get("source", "Import manuel"))[:120], str(data.get("publisher", ""))[:180],
             url, str(data.get("summary", ""))[:2000], str(data.get("published", ""))[:24],
             now_utc(), kind, score, position, reason))
        return cur.rowcount > 0


def fetch_all(db_path: Path | str = DB_PATH, minimum: int = 0) -> list[dict[str, Any]]:
    with connect(db_path) as con:
        rows = con.execute("""SELECT * FROM signals WHERE score >= ?
              ORDER BY score DESC, discovered DESC""", (minimum,)).fetchall()
        return [dict(row) for row in rows]


def update_signal(signal_id: str, changes: dict[str, Any], db_path: Path | str = DB_PATH) -> None:
    allowed = {"company", "status", "contact_name", "contact_role", "contact_email", "contact_source", "do_not_contact", "note"}
    safe = {k: (int(v) if k == "do_not_contact" else str(v)) for k, v in changes.items() if k in allowed}
    if not safe:
        return
    with connect(db_path) as con:
        con.execute("UPDATE signals SET " + ", ".join(f"{k} = ?" for k in safe) + " WHERE id = ?", (*safe.values(), signal_id))


def outreach_draft(signal: dict[str, Any], profile: dict | None = None) -> tuple[str, str]:
    profile = profile or load_profile()
    company = signal.get("company") or "votre organisation"
    position = signal.get("position", "Data Platform")
    background = profile["positionings"].get(position, profile["positionings"]["Data Platform"])
    name = (signal.get("contact_name") or "").strip()
    greeting = f"Bonjour {name}," if name else "Bonjour,"
    source = (signal.get("publisher") or signal.get("source") or "une source publique").strip()
    title = signal.get("title", "une évolution de vos activités")
    subj = f"{company} | Proposition d'accompagnement Data en freelance" if signal.get("company") else "Proposition d'accompagnement Data en freelance"
    body = (f"{greeting}\n\n"
            f"J'ai vu passer une information publiée par {source} : « {title} ». "
            "Je me permets de vous contacter car ce sujet pourrait éventuellement nécessiter un renfort Data externe.\n\n"
            f"Je suis consultant Data & IA (9 ans d'expérience, doctorat en IA). {background} "
            "J'ai notamment accompagné Pickup Services, BPCE et La Poste sur des projets Data.\n\n"
            "Si vous envisagez un appui freelance sur le cadrage ou la réalisation, "
            "seriez-vous ouvert(e) à un échange de 15 minutes ?\n\n"
            "Bien cordialement,\n"
            "Khalil NAMIR\n\n"
            "PS : Si ce message ne concerne pas votre activité ou si vous préférez ne plus recevoir "
            "de sollicitation de ma part, répondez simplement « stop ». Je respecterai votre demande.")
    return subj, body


def export_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def scan(queries: list[str] | None = None, db_path: Path | str = DB_PATH) -> dict[str, Any]:
    init_db(db_path)
    found = added = 0
    errors = []
    for query in (queries if queries is not None else DEFAULT_QUERIES):
        try:
            rows = search_rss(query)
            found += len(rows)
            for row in rows:
                added += insert_signal(row, db_path)
        except Exception as exc:
            errors.append(f"{query}: {type(exc).__name__}: {exc}")
    return {"queries": len(queries if queries is not None else DEFAULT_QUERIES),
            "found": found, "added": added, "errors": errors, "run_at": now_utc()}


def export_snapshot(db_path: Path | str = DB_PATH) -> str:
    """Exporter les lignes de la base locale pour restauration manuelle.

    Contient potentiellement des contacts professionnels : à garder privé.
    """
    rows = fetch_all(db_path)
    return json.dumps({"version": 1, "exported_at": now_utc(), "signals": rows},
                      ensure_ascii=False, indent=2)


def import_snapshot(payload: bytes | str, db_path: Path | str = DB_PATH) -> dict[str, int]:
    """Importer une sauvegarde sans remplacer les signaux existants."""
    if isinstance(payload, bytes):
        if len(payload) > 5_000_000:
            raise ValueError("Sauvegarde trop volumineuse (maximum 5 Mo).")
        payload = payload.decode("utf-8")
    backup = json.loads(payload)
    if not isinstance(backup, dict) or backup.get("version") != 1 or not isinstance(backup.get("signals"), list):
        raise ValueError("Format de sauvegarde incompatible.")
    rows = backup["signals"]
    if len(rows) > 2000:
        raise ValueError("Limite de 2000 enregistrements par import.")
    init_db(db_path)
    added = skipped = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Enregistrement invalide dans la sauvegarde.")
        data = {key: row.get(key, "") for key in
                ("title", "company", "url", "summary", "publisher", "published", "source")}
        if any(not isinstance(v, str) for v in data.values()):
            raise ValueError("Un champ de signal doit contenir du texte.")
        inserted = insert_signal(data, db_path)
        if not inserted:
            skipped += 1
            continue
        allowed_statuses = {"À qualifier", "À contacter", "Contacté", "Écarté"}
        changes = {k: str(row.get(k, ""))[:300] for k in
                   ("contact_name", "contact_role", "contact_email", "contact_source", "company", "note")}
        changes["status"] = row.get("status") if row.get("status") in allowed_statuses else "À qualifier"
        changes["do_not_contact"] = int(bool(row.get("do_not_contact", 0)))
        identifier = hashlib.sha256(data["url"].strip().encode("utf-8")).hexdigest()[:20]
        update_signal(identifier, changes, db_path)
        added += 1
    return {"added": added, "skipped": skipped}
