#!/usr/bin/env python3
"""Coleta os 100 incidentes mais recentes de ransomware.live e salva em JSON.

Fluxo:
1) Abre a página principal no navegador padrão (opcional).
2) Consulta o endpoint oficial com os incidentes recentes.
3) Normaliza apenas os campos: grupo, vítima, data e país.
4) Salva em arquivo JSON local.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

PAGE_URL = "https://www.ransomware.live/#/"
API_URL = "https://api.ransomware.live/v2/recentvictims"


def fetch_recent_victims(api_url: str = API_URL) -> list[dict[str, Any]]:
    """Busca dados de vítimas recentes na API pública."""
    request = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CTI-Ransom-check/1.0)",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"Erro HTTP {response.status} ao consultar a API.")

        payload = response.read().decode("utf-8")
        data = json.loads(payload)

    if not isinstance(data, list):
        raise RuntimeError("Resposta inesperada da API: formato não é lista.")

    return data


def normalize_record(record: dict[str, Any]) -> dict[str, str]:
    """Mantém apenas os campos solicitados, com fallback seguro."""
    group = str(record.get("group", "") or record.get("group_name", "") or "").strip()
    date = str(
        record.get("attackdate", "")
        or record.get("discovered", "")
        or record.get("date", "")
        or ""
    ).strip()

    return {
        "grupo": group,
        "vitima": str(record.get("victim", "") or "").strip(),
        "data": date,
        "pais": str(record.get("country", "") or "").strip(),
    }


def save_json(records: list[dict[str, str]], output_path: Path) -> None:
    """Salva lista de registros em JSON legível."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(records, fp, ensure_ascii=False, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Abre ransomware.live e baixa os dados do bloco '100 most recent victim' em JSON."
        )
    )
    parser.add_argument(
        "-o",
        "--output",
        default=f"recent_victims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        help="Arquivo de saída JSON (padrão: recent_victims_YYYYMMDD_HHMMSS.json).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Não abre a página no navegador antes da coleta.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.no_browser:
        opened = webbrowser.open(PAGE_URL, new=2)
        if opened:
            print(f"Página aberta no navegador: {PAGE_URL}")
        else:
            print(
                "Não foi possível abrir automaticamente o navegador. "
                f"Acesse manualmente: {PAGE_URL}"
            )

    try:
        raw_data = fetch_recent_victims()
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Falha ao coletar dados da API: {exc}", file=sys.stderr)
        return 1

    top_100 = raw_data[:100]
    normalized = [normalize_record(item) for item in top_100]

    output_path = Path(args.output)
    save_json(normalized, output_path)

    print(f"Total de registros coletados: {len(normalized)}")
    print(f"Arquivo JSON salvo em: {output_path.resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
