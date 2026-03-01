#!/usr/bin/env python3
"""Coleta os 100 incidentes mais recentes de ransomware.live e salva em JSON."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

PAGE_URL = "https://www.ransomware.live/#/"
API_URL = "https://api.ransomware.live/v2/recentvictims"

GROUP_FIELD_CANDIDATES = (
    "group_name",
    "group",
    "ransomware_group",
    "threat_actor",
    "actor",
    "threatactor",
    "groupname",
)
DATE_FIELD_CANDIDATES = (
    "date",
    "discovered",
    "published",
    "published_at",
    "post_date",
    "created_at",
    "disclosure_date",
    "leak_date",
)
COUNTRY_FIELD_CANDIDATES = ("country", "country_code", "location", "countryname")
VICTIM_FIELD_CANDIDATES = ("victim", "victim_name", "name", "target", "title")

NESTED_TEXT_CANDIDATES = (
    "name",
    "value",
    "title",
    "label",
    "slug",
    "display_name",
)


def build_ssl_context(cafile: str | None = None, insecure: bool = False) -> ssl.SSLContext:
    if insecure:
        return ssl._create_unverified_context()
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    env_cafile = os.environ.get("SSL_CERT_FILE")
    if env_cafile:
        return ssl.create_default_context(cafile=env_cafile)
    return ssl.create_default_context()


def fetch_recent_victims(
    api_url: str = API_URL,
    cafile: str | None = None,
    insecure: bool = False,
) -> list[dict[str, Any]]:
    request = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; CTI-Ransom-check/1.0)",
            "Accept": "application/json",
        },
    )
    ssl_context = build_ssl_context(cafile=cafile, insecure=insecure)

    with urllib.request.urlopen(request, timeout=30, context=ssl_context) as response:
        if response.status != 200:
            raise RuntimeError(f"Erro HTTP {response.status} ao consultar a API.")
        payload = response.read().decode("utf-8")
        data = json.loads(payload)

    if not isinstance(data, list):
        raise RuntimeError("Resposta inesperada da API: formato não é lista.")
    return data


def _normalize_key(key: str) -> str:
    return key.strip().lower().replace("-", "_").replace(" ", "_")


def _to_text(value: Any, *, for_date: bool = False) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float)):
        if for_date and value > 1_000_000_000:
            ts = value / 1000 if value > 10_000_000_000 else value
            return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        return str(value)

    if isinstance(value, dict):
        lowered = {_normalize_key(k): v for k, v in value.items()}
        for k in NESTED_TEXT_CANDIDATES:
            if k in lowered:
                txt = _to_text(lowered[k], for_date=for_date)
                if txt:
                    return txt
        for item in lowered.values():
            txt = _to_text(item, for_date=for_date)
            if txt:
                return txt
        return ""

    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            txt = _to_text(item, for_date=for_date)
            if txt:
                parts.append(txt)
        return ", ".join(parts)

    return str(value).strip()


def _find_key_recursively(payload: Any, key_set: set[str]) -> Any:
    if isinstance(payload, dict):
        lowered = {_normalize_key(k): v for k, v in payload.items()}
        for candidate in key_set:
            if candidate in lowered:
                return lowered[candidate]
        for value in lowered.values():
            found = _find_key_recursively(value, key_set)
            if found is not None:
                return found
        return None

    if isinstance(payload, list):
        for item in payload:
            found = _find_key_recursively(item, key_set)
            if found is not None:
                return found
    return None


def first_non_empty_value(record: dict[str, Any], keys: Iterable[str], *, for_date: bool = False) -> str:
    normalized_keys = [_normalize_key(k) for k in keys]
    lowered = {_normalize_key(k): v for k, v in record.items()}

    for key in normalized_keys:
        if key in lowered:
            text = _to_text(lowered[key], for_date=for_date)
            if text:
                return text

    found = _find_key_recursively(record, set(normalized_keys))
    text = _to_text(found, for_date=for_date)
    return text if text else ""


def normalize_record(record: dict[str, Any]) -> dict[str, str]:
    return {
        "grupo": first_non_empty_value(record, GROUP_FIELD_CANDIDATES),
        "vitima": first_non_empty_value(record, VICTIM_FIELD_CANDIDATES),
        "data": first_non_empty_value(record, DATE_FIELD_CANDIDATES, for_date=True),
        "pais": first_non_empty_value(record, COUNTRY_FIELD_CANDIDATES),
    }


def save_json(records: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(records, fp, ensure_ascii=False, indent=2)


def print_field_diagnostics(raw_data: list[dict[str, Any]], normalized: list[dict[str, str]]) -> None:
    missing_group = sum(1 for item in normalized if not item["grupo"])
    missing_date = sum(1 for item in normalized if not item["data"])
    if missing_group == 0 and missing_date == 0:
        return

    print("Aviso de qualidade dos dados: alguns registros vieram sem 'grupo' e/ou 'data'.", file=sys.stderr)
    print(f"- Registros sem grupo: {missing_group}\n- Registros sem data: {missing_date}", file=sys.stderr)
    if raw_data:
        print(
            "Chaves disponíveis no primeiro registro retornado pela API: "
            + ", ".join(sorted(raw_data[0].keys())),
            file=sys.stderr,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Abre ransomware.live e baixa os dados do bloco '100 most recent victim' em JSON."
    )
    parser.add_argument(
        "-o",
        "--output",
        default=f"recent_victims_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        help="Arquivo de saída JSON (padrão: recent_victims_YYYYMMDD_HHMMSS.json).",
    )
    parser.add_argument("--no-browser", action="store_true", help="Não abre a página no navegador.")
    parser.add_argument("--cafile", help="Caminho para CA bundle para validação TLS.")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Desabilita validação TLS/SSL (não recomendado; use só para diagnóstico).",
    )
    return parser.parse_args()


def print_ssl_help(exc: Exception) -> None:
    print(
        "Falha SSL: o certificado não pôde ser validado.\n"
        "1) Atualize CAs do sistema.\n"
        "2) Use --cafile /caminho/ca-bundle.pem.\n"
        "3) Use SSL_CERT_FILE=/caminho/ca-bundle.pem.\n"
        "4) Último recurso (diagnóstico): --insecure.\n"
        f"Detalhe técnico: {exc}",
        file=sys.stderr,
    )


def is_ssl_cert_error(exc: Exception) -> bool:
    if isinstance(exc, ssl.SSLCertVerificationError):
        return True
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLCertVerificationError):
            return True
        if isinstance(reason, ssl.SSLError) and "CERTIFICATE_VERIFY_FAILED" in str(reason):
            return True
    return False


def main() -> int:
    args = parse_args()

    if not args.no_browser:
        opened = webbrowser.open(PAGE_URL, new=2)
        if opened:
            print(f"Página aberta no navegador: {PAGE_URL}")
        else:
            print(f"Abra manualmente: {PAGE_URL}")

    try:
        raw_data = fetch_recent_victims(cafile=args.cafile, insecure=args.insecure)
    except (ssl.SSLError, urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        if is_ssl_cert_error(exc):
            print_ssl_help(exc)
        else:
            print(f"Falha ao coletar dados da API: {exc}", file=sys.stderr)
        return 1

    top_100 = raw_data[:100]
    normalized = [normalize_record(item) for item in top_100]
    print_field_diagnostics(top_100, normalized)

    output_path = Path(args.output)
    save_json(normalized, output_path)

    print(f"Total de registros coletados: {len(normalized)}")
    print(f"Arquivo JSON salvo em: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
