# CTI-Ransom-check

Script em Python para:

1. Abrir a página `https://www.ransomware.live/#/` no navegador padrão.
2. Coletar os dados correspondentes à seção **"100 most recent victim"** pela API pública do site.
3. Gerar um arquivo `.json` contendo apenas:
   - `grupo`
   - `vitima`
   - `data`
   - `pais`

## Arquivo principal

- `ransomware_scraper.py`

## Como o código funciona

O script segue este fluxo:

1. **(Opcional) Visualização da página no navegador**
   - Por padrão, o script tenta abrir a URL `https://www.ransomware.live/#/` usando o módulo `webbrowser`.
   - Se você não quiser abrir o navegador, use `--no-browser`.

2. **Coleta dos dados**
   - O script consulta `https://api.ransomware.live/v2/recentvictims` com `urllib.request`.
   - Essa rota retorna os incidentes/vítimas mais recentes em JSON.

3. **Normalização dos campos**
   - Para cada item retornado, o script extrai e converte para os campos solicitados:
     - `group_name` -> `grupo`
     - `victim` -> `vitima`
     - `date` -> `data`
     - `country` -> `pais`

4. **Filtro dos 100 mais recentes**
   - Mesmo que a API retorne mais dados, o script mantém apenas os 100 primeiros itens (`raw_data[:100]`).

5. **Exportação para JSON**
   - O resultado é salvo com indentação (legível), UTF-8 e sem escapar acentos.

## Requisitos

- Python 3.10+ (ou compatível com type hints modernos)
- Sem bibliotecas externas

## Como executar

### Execução padrão

```bash
python ransomware_scraper.py
```

- Abre a página no navegador.
- Salva o JSON com nome automático, por exemplo:
  - `recent_victims_20260224_103000.json`

### Definir nome de saída

```bash
python ransomware_scraper.py --output dados/victimas_recentes.json
```

### Executar sem abrir o navegador

```bash
python ransomware_scraper.py --no-browser
```

## Exemplo de saída JSON

```json
[
  {
    "grupo": "LockBit3",
    "vitima": "Empresa X",
    "data": "2026-02-23",
    "pais": "BR"
  }
]
```

## Tratamento de erros

Se houver problema de rede, timeout ou resposta inválida da API, o script:

- mostra uma mensagem de erro no terminal;
- encerra com código de saída `1`.

Quando executa com sucesso, retorna código `0`.
