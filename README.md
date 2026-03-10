# CTI-Ransom-check

Script em Python para:

1. Coletar os dados recentes de duas APIs publicas:
   - `https://api.ransomware.live/v2/recentvictims`
   - `https://www.ransomlook.io/api/recent/100`
2. Normalizar os campos para um formato unico:
   - `grupo`
   - `vitima`
   - `data`
   - `pais`
3. Remover vitimas duplicadas entre as duas fontes.
4. Salvar em `.json` (sem limite final apos deduplicacao).

## Arquivo principal

- `ransomware_scraper.py`

## Como o codigo funciona

O script segue este fluxo:

1. **Coleta dos dados das duas fontes**
   - Ransomware.live: `https://api.ransomware.live/v2/recentvictims`
   - RansomLook: `https://www.ransomlook.io/api/recent/100`
   - O script usa os 100 registros mais recentes de cada fonte.

2. **Normalizacao de campos**
   - O script converte cada registro para o schema final:
     - `grupo`: usa `group` ou `group_name`
     - `vitima`: usa `victim` (Ransomware.live) ou `title`/`post_title` (RansomLook)
     - `data`: usa `attackdate`, `discovered` ou `date`
     - `pais`: usa `country` (quando existir)

3. **Deduplicacao por vitima**
   - Junta os registros das duas fontes.
   - Remove duplicatas comparando `vitima` (case-insensitive).
   - Mantem apenas a primeira ocorrencia de cada vitima.

4. **Exportacao**
   - Apos deduplicar, salva todos os registros unicos encontrados.
   - Salva em JSON legivel (`indent=2`, UTF-8, `ensure_ascii=False`).

## Requisitos

- Python 3.10+
- Sem bibliotecas externas

## Como executar

### Execucao padrao

```bash
python ransomware_scraper.py
```

- Salva o JSON com nome automatico, por exemplo:
  - `recent_victims_20260307_153000.json`

### Definir nome de saida

```bash
python ransomware_scraper.py --output dados/victimas_recentes.json
```

## Exemplo de saida JSON

```json
[
  {
    "grupo": "qilin",
    "vitima": "Geotec Surveys",
    "data": "2026-03-07 18:39:58.824682",
    "pais": ""
  }
]
```

## Tratamento de erros

Se houver problema de rede, timeout ou resposta invalida da API, o script:

- mostra uma mensagem de erro no terminal;
- encerra com codigo de saida `1`.

Quando executa com sucesso, retorna codigo `0`.
