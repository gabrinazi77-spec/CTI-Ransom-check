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

3. **Normalização robusta dos campos**
   - A API pode mudar nomes de colunas entre endpoints/versões e também retornar valores aninhados (objeto/lista).
   - O script agora: 
     - tenta aliases por campo;
     - faz busca *case-insensitive*;
     - busca chaves também em estruturas aninhadas;
     - converte timestamp numérico para data (`YYYY-MM-DD`) quando necessário.

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

## Suporte a ambientes com erro de certificado SSL

Se você receber erro como:

`SSL: CERTIFICATE_VERIFY_FAILED`

isso normalmente significa um destes cenários:

- CA do sistema ausente/desatualizada;
- proxy corporativo interceptando HTTPS;
- Python sem cadeia de certificados correta.

### Opções para resolver

1. **Informar um CA bundle explícito (recomendado):**

```bash
python ransomware_scraper.py --no-browser --cafile /etc/ssl/certs/ca-certificates.crt
```

2. **Usar variável de ambiente padrão do Python (`SSL_CERT_FILE`):**

```bash
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
python ransomware_scraper.py --no-browser
```

3. **Último recurso para diagnóstico (inseguro):**

```bash
python ransomware_scraper.py --no-browser --insecure
```

> `--insecure` desabilita validação TLS/SSL. Use apenas temporariamente para troubleshooting.

### Correção rápida para Linux (Debian/Ubuntu)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates
python ransomware_scraper.py --no-browser --cafile /etc/ssl/certs/ca-certificates.crt
```

### Correção rápida para macOS (Python.org)

Execute o script `Install Certificates.command` que vem com o Python instalado.
Depois rode novamente o scraper.


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

## Por que às vezes 'grupo' e 'data' vinham vazios?

Isso acontecia porque o script antigo assumia apenas chaves simples no nível raiz do JSON.
Em alguns endpoints/versões da API, `grupo` e `data` podem vir com outros nomes, maiúsculas/minúsculas diferentes, objetos aninhados ou listas.
Resultado: `vitima` e `pais` podiam ser preenchidos, mas `grupo` e `data` ficavam `""`.

Para ajudar diagnóstico, o script também imprime no terminal um resumo de quantos registros vieram sem `grupo`/`data` e mostra as chaves do primeiro objeto retornado pela API.
