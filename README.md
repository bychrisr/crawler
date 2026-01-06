# Documentation Crawler v2.0.0

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/bychrisr/crawler)
[![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

Um crawler **robusto** e **profissional** para baixar documentações de sites e convertê-las em um único arquivo Markdown com sumário automático (TOC).

## 🎯 Funcionalidades

### Core Features
- 🔗 **Resolução robusta de links** (relativos/absolutos) com suporte a múltiplos padrões de documentação
- 🌐 **Crawling baseado em domínio** (crawleia todo o domínio base)
- 📂 **Conversão para Markdown** com TOC automático e metadados
- 🤖 **Respeita robots.txt** por padrão
- 💾 **Cache local inteligente** para re-execuções rápidas
- ⚡ **Threads paralelas** para downloads acelerados
- 🎨 **Barra de progresso** com `tqdm`

### Features Avançadas v2.0
- ✅ **Validação automática de output** (detecta problemas de extração)
- 🔄 **Retry inteligente** com exponential backoff
- ⏱️ **Rate limiting** automático para evitar bans
- 🔐 **Autenticação HTTP** (Basic Auth)
- 📋 **Headers HTTP customizados**
- 📊 **Metadados em JSON** salvos automaticamente
- 🛑 **Tratamento robusto de interrupções** (Ctrl+C salva progresso)
- 📝 **Logging detalhado** para debug

### Melhorias de Extração
- 🧹 **Fallback inteligente** para sites com SSR/JavaScript
- 🎯 **Filtro conservador** (remove apenas páginas realmente inúteis)
- 📊 **Estatísticas detalhadas** (cache hits, retries, links duplicados, etc.)

## 🛠️ Requisitos

- **Python 3.7+** (use `python3` no Linux/Mac)
- `pip3` ou `pip`

## 🚀 Instalação

### 1. Clone o repositório

```bash
git clone git@github.com:bychrisr/crawler.git
cd crawler
```

### 2. (Recomendado) Crie um ambiente virtual

```bash
python3 -m venv venv

# Ativa o ambiente virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
# ou
pip3 install -r requirements.txt
```

## 📖 Uso

### Uso Básico

```bash
python3 crawler.py --base-url <URL_DA_DOCUMENTACAO>
```

### Exemplos Práticos

#### Documentação simples
```bash
python3 crawler.py \
  --base-url https://docs.minimals.cc/introduction/ \
  --output minimals-docs.md \
  --max-pages 100
```

#### Documentação grande com mais workers
```bash
python3 crawler.py \
  --base-url https://vuejs.org/guide/ \
  --output vue-docs.md \
  --max-pages 1000 \
  --workers 5
```

#### Com autenticação
```bash
python3 crawler.py \
  --base-url https://docs-privadas.com/ \
  --auth-user meu-usuario \
  --auth-pass minha-senha \
  --output docs-privadas.md
```

#### Com headers customizados
```bash
python3 crawler.py \
  --base-url https://api-docs.com/ \
  --header "Authorization: Bearer TOKEN123" \
  --header "X-Custom-Header: value" \
  --output api-docs.md
```

#### Ignorar robots.txt (use com responsabilidade!)
```bash
python3 crawler.py \
  --base-url https://site.com/ \
  --no-robots \
  --output site-docs.md
```

## 🎛️ Opções de Linha de Comando

### Argumentos Principais

| Argumento | Descrição | Padrão |
|-----------|-----------|--------|
| `--base-url` | **(Obrigatório)** URL base da documentação | - |
| `--output` | Arquivo de saída Markdown | `output.md` |
| `--workers` | Número de threads paralelas | `2` |
| `--max-pages` | Número máximo de páginas a crawlear | `500` |
| `--cache-dir` | Diretório para cache local | `.cache` |
| `--min-content-length` | Tamanho mínimo de conteúdo (chars) | `100` |

### Flags

| Flag | Descrição |
|------|-----------|
| `--clear-cache` | Limpa o cache antes de iniciar |
| `--no-robots` | Ignora robots.txt (⚠️ use com cuidado) |
| `--version` | Mostra a versão do crawler |

### Autenticação e Headers

| Argumento | Descrição |
|-----------|-----------|
| `--auth-user` | Usuário para autenticação HTTP básica |
| `--auth-pass` | Senha para autenticação HTTP básica |
| `--header` | Header HTTP customizado (pode usar múltiplas vezes) |

## 📁 Estrutura de Saída

Após a execução, você terá:

```
.
├── output.md                 # Documentação em Markdown
├── output.metadata.json      # Metadados da execução
├── crawler.log              # Log detalhado
└── .cache/                  # Cache de páginas HTML
    ├── abc123def.html
    └── ...
```

### Arquivo de Metadados (JSON)

Exemplo de `output.metadata.json`:

```json
{
  "version": "2.0.0",
  "base_url": "https://docs.exemplo.com/",
  "started_at": "2026-01-05T23:00:00",
  "finished_at": "2026-01-05T23:05:32",
  "config": {
    "max_workers": 3,
    "max_pages": 100,
    "min_content_length": 100,
    "respect_robots": true
  },
  "stats": {
    "fetched": 87,
    "failed": 2,
    "cache_hits": 12,
    "links_found": 95,
    "retries_performed": 4,
    ...
  }
}
```

## 📊 Exemplo de Resumo de Execução

```
======================================================================
📊 RESUMO DO CRAWLING
======================================================================
✅ Páginas Crawleadas: 87
❌ Páginas Falhas: 2
🗑️  Páginas Filtradas (junk): 3
📏 Páginas Muito Pequenas: 1
🤖 Bloqueadas por robots.txt: 0

🔗 Links Encontrados: 95
🌐 Links Externos (ignorados): 234
♻️  Links Duplicados (ignorados): 1,523

💾 Cache Hits: 12
🔄 Retries Realizados: 4

📝 Total de Caracteres: 3,245,892
📖 Total de Palavras: 456,234
💾 Tamanho do Arquivo: 245,892 bytes (240.13 KB)
⏱️  Tempo Total: 00:05:32

======================================================================
🔍 VALIDAÇÃO DE QUALIDADE
======================================================================
✅ Output validado com sucesso! Nenhum problema detectado.

======================================================================
📄 Logs detalhados salvos em: crawler.log
📊 Metadados salvos em: output.metadata.json
======================================================================
```

## 🆕 O Que Há de Novo na v2.0.0

### ✨ Novidades Principais

1. **Validação Automática**
   - Detecta automaticamente problemas de extração
   - Avisa se arquivo está muito pequeno para o número de páginas
   - Identifica baixa conversão HTML → Markdown
   - Alerta sobre alta taxa de falhas

2. **Retry Inteligente**
   - Exponential backoff automático (2^n segundos)
   - Configurable retries (padrão: 3 tentativas)
   - Estatísticas de retries no resumo final

3. **Rate Limiting**
   - Intervalo mínimo de 0.5s entre requests
   - Evita bans e respeita servidores

4. **Autenticação e Headers**
   - Suporte a HTTP Basic Auth
   - Headers HTTP customizados
   - Útil para APIs e docs privadas

5. **Metadados e Observabilidade**
   - Arquivo JSON com metadados completos
   - Timestamps de início/fim
   - Configuração usada
   - Todas as estatísticas

6. **Tratamento de Interrupções**
   - Ctrl+C agora salva progresso parcial
   - Não perde trabalho em interrupções

7. **Robots.txt**
   - Respeita robots.txt por padrão
   - Flag `--no-robots` para ignorar (use com responsabilidade)

### 🔧 Melhorias Técnicas

- Extração robusta para sites com SSR/JavaScript
- Fallback inteligente quando `<main>` está vazio
- Logs mais detalhados para debug
- Código refatorado com type hints
- Configurações centralizadas em `CrawlerConfig`

## 🔍 Troubleshooting

### Problema: "ModuleNotFoundError"

**Solução:**
```bash
pip3 install -r requirements.txt
```

### Problema: Poucas páginas crawleadas

**Diagnóstico:**
1. Verifique `crawler.log`:
   ```bash
   grep "Links encontrados" crawler.log
   ```
2. Verifique se robots.txt está bloqueando:
   ```bash
   grep "Bloqueado por robots.txt" crawler.log
   ```
3. Teste manualmente se os links funcionam no navegador

**Soluções:**
- Use `--no-robots` se appropriate
- Aumente `--max-pages` se atingiu o limite
- Verifique se o site usa JavaScript (SPAs não são suportados)

### Problema: Arquivo muito pequeno (validação alerta)

**Causas comuns:**
- Site usa JavaScript para renderizar (React/Vue SPA)
- Bloqueio por robots.txt
- Problemas na extração de conteúdo

**Soluções:**
1. Verifique os avisos de validação no resumo
2. Analise `crawler.log` para detalhes
3. Para SPAs, considere usar Selenium/Puppeteer (não suportado atualmente)

### Problema: Alta taxa de falhas

**Causas:**
- Timeouts de rede
- Rate limiting do servidor
- Bloqueio por firewall/WAF

**Soluções:**
- Reduza `--workers` para 1-2
- Use headers customizados se necessário
- Verifique conectividade de rede

## ⚠️ Limitações Conhecidas

- **Sites com JavaScript puro (SPAs)**: Sites que renderizam 100% do conteúdo via JS (sem SSR) não são suportados. Use Selenium/Puppeteer nesses casos.
- **Autenticação complexa**: Apenas HTTP Basic Auth é suportada. OAuth e outros métodos requerem modificação no código.
- **Rate Limiting agressivo**: Alguns sites podem bloquear mesmo com rate limiting. Ajuste manualmente se necessário.

## 🤝 Contribuindo

Pull requests são bem-vindos! Para mudanças maiores:

1. Abra uma issue primeiro para discutir
2. Fork o projeto
3. Crie uma branch (`git checkout -b feature/MinhaFeature`)
4. Commit suas mudanças (`git commit -m 'Add: MinhaFeature'`)
5. Push para a branch (`git push origin feature/MinhaFeature`)
6. Abra um Pull Request

## 📝 Changelog

Veja [CHANGELOG.md](CHANGELOG.md) para histórico de versões.

## 📄 Licença

Este projeto é open source sob a licença MIT. Veja [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
- [requests](https://docs.python-requests.org/) - HTTP requests
- [tqdm](https://github.com/tqdm/tqdm) - Progress bars

---

**Desenvolvido com ❤️ para a comunidade open source**

Para bugs, sugestões ou dúvidas, [abra uma issue](https://github.com/bychrisr/crawler/issues)!
