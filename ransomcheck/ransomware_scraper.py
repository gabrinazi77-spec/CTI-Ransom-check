#!/usr/bin/env python3
"""Coleta incidentes recentes de ransomware.live e ransomlook.io e salva em JSON.

Fluxo:
1) Consulta os endpoints oficiais com os incidentes recentes.
2) Normaliza apenas os campos: grupo, vitima, data e pais.
3) Remove vitimas duplicadas entre as fontes.
4) Salva em arquivo JSON local.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

RANSOMWARE_LIVE_API_URL = "https://api.ransomware.live/v2/recentvictims"
RANSOMLOOK_API_URL = "https://www.ransomlook.io/api/recent/100"
SOURCE_LIMIT = 100


def fetch_json_list(api_url: str) -> list[dict[str, Any]]:
    """Busca uma lista JSON em uma API publica."""
    request = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CTI-Ransom-check/1.0)",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Erro HTTP {response.status} ao consultar a API: {api_url}"
            )

        payload = response.read().decode("utf-8")
        data = json.loads(payload)

    if not isinstance(data, list):
        raise RuntimeError(
            f"Resposta inesperada da API ({api_url}): formato nao e lista."
        )

    return data


def normalize_record(record: dict[str, Any]) -> dict[str, str]:
    """Mantem apenas os campos solicitados, com fallback entre APIs."""
    group = str(record.get("group", "") or record.get("group_name", "") or "").strip()
    date = str(
        record.get("attackdate", "")
        or record.get("discovered", "")
        or record.get("date", "")
        or ""
    ).strip()
    victim = str(
        record.get("victim", "")
        or record.get("title", "")
        or record.get("post_title", "")
        or ""
    ).strip()

    return {
        "grupo": group,
        "vitima": victim,
        "data": date,
        "pais": str(record.get("country", "") or "").strip(),
    }


def deduplicate_by_victim(records: list[dict[str, str]]) -> list[dict[str, str]]:
    """Remove registros repetidos considerando o nome da vitima."""
    seen: set[str] = set()
    unique: list[dict[str, str]] = []

    for record in records:
        victim = record.get("vitima", "").strip().lower()
        if not victim or victim in seen:
            continue
        seen.add(victim)
        unique.append(record)

    return unique


def save_json(records: list[dict[str, str]], output_path: Path) -> None:
    """Salva lista de registros em JSON legivel."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(records, fp, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa dados recentes de ransomware.live e ransomlook.io em JSON."
        )
    )
    parser.add_argument(
        "-o",
        "--output",
        default=f"recent_victims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        help="Arquivo de saida JSON (padrao: recent_victims_YYYYMMDD_HHMMSS.json).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        raw_live = fetch_json_list(RANSOMWARE_LIVE_API_URL)
        raw_look = fetch_json_list(RANSOMLOOK_API_URL)
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Falha ao coletar dados da API: {exc}", file=sys.stderr)
        return 1

    normalized_live = [normalize_record(item) for item in raw_live[:SOURCE_LIMIT]]
    normalized_look = [normalize_record(item) for item in raw_look[:SOURCE_LIMIT]]
    merged = normalized_live + normalized_look
    deduplicated = deduplicate_by_victim(merged)
    final_records = deduplicated

    output_path = Path(args.output)
    save_json(final_records, output_path)

    print(f"Registros consultados (ransomware.live): {len(normalized_live)}")
    print(f"Registros consultados (ransomlook.io): {len(normalized_look)}")
    print(f"Total unico apos deduplicacao: {len(deduplicated)}")
    print(f"Total final salvo: {len(final_records)}")
    print(f"Arquivo JSON salvo em: {output_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
