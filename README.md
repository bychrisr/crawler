# Documentation Crawler

Um crawler eficiente e otimizado para baixar documentações de sites e convertê-las em um único arquivo Markdown com **sumário automático (TOC)**.

## ⚙️ Funcionalidades

- 🔗 **Resolução robusta de links** (relativos/absolutos) com suporte a múltiplos padrões de documentação
- 🌐 **Crawling baseado em domínio** (crawleia todo o domínio base, ex: `docs.minimals.cc`)
- 📂 **Conversão para único arquivo Markdown** com TOC automático
- 📝 **Geração automática de sumário (Table of Contents)**
- 🛑 **Timeout e retries** para lidar com falhas de rede
- 🗂 **Log detalhado** salvo em `crawler.log` para debug
- ⚡ **Threads para aceleração** de downloads paralelos
- 💾 **Cache local** para evitar downloads repetidos
- 🎨 **Barra de progresso** com `tqdm`
- 📊 **Estatísticas detalhadas** ao final do processo (links encontrados, duplicados, externos, etc.)
- 🧹 **Filtro conservador** (remove apenas páginas explicitamente inúteis: privacy-policy, terms-of-service, etc.)

## 🛠️ Requisitos

- **Python 3.7+** (use `python3` no Linux/Mac)
- `pip3` ou `pip` (geralmente vem com o Python)

> ⚠️ **IMPORTANTE:** Se você estiver no Linux/Mac, use `python3` e `pip3` em vez de `python` e `pip`.

## 🚀 Como Usar

### 1. Clone ou baixe o script

```bash
git clone git@github.com:bychrisr/crawler.git
cd crawler
```

### 2. (Opcional) Crie um ambiente virtual (recomendado)

Um ambiente virtual isola as dependências do script do resto do seu sistema.

```bash
# Cria o ambiente virtual (pasta 'venv')
python3 -m venv venv

# Ativa o ambiente virtual
# No Linux/Mac:
source venv/bin/activate
# No Windows:
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
# Se você está usando ambiente virtual ou Python 3 como padrão:
pip install requests beautifulsoup4 tqdm lxml

# Se você precisa especificar Python 3:
pip3 install requests beautifulsoup4 tqdm lxml
```

> **Nota:** O pacote `lxml` é opcional mas recomendado para parsing HTML mais rápido.

Ou usando o arquivo `requirements.txt`:

```bash
pip install -r requirements.txt
# ou
pip3 install -r requirements.txt
```

### 4. Execute o script

#### Uso Básico

```bash
python3 crawler.py --base-url <URL_DA_DOCUMENTACAO>
```

Este comando usará os **valores padrão** para todos os outros parâmetros.

#### Exemplos Práticos

**Exemplo 1: Documentação do Minimals UI**

```bash
python3 crawler.py \
  --base-url https://docs.minimals.cc/introduction/ \
  --output minimals-docs.md \
  --max-pages 100 \
  --workers 3
```

**Exemplo 2: Documentação do TradingView Lightweight Charts**

```bash
python3 crawler.py \
  --base-url https://tradingview.github.io/lightweight-charts/docs \
  --output tradingview-docs.md \
  --max-pages 200 \
  --workers 4
```

**Exemplo 3: Com limpeza de cache e filtro de conteúdo**

```bash
python3 crawler.py \
  --base-url https://docs.exemplo.com/ \
  --output docs.md \
  --max-pages 500 \
  --min-content-length 200 \
  --clear-cache
```

**Exemplo 4: Documentação grande com mais workers**

```bash
python3 crawler.py \
  --base-url https://vuejs.org/guide/ \
  --output vue-docs.md \
  --max-pages 1000 \
  --workers 5
```

## 🎛️ Opções de Comando

| Argumento | Descrição | Valor Padrão |
| :--- | :--- | :--- |
| `--base-url` | **(Obrigatório)** A URL base da documentação a ser crawleada. | |
| `--output` | Nome do arquivo Markdown de saída. | `output.md` |
| `--workers` | Número de threads para downloads paralelos. Mais threads = mais rápido, mas cuidado com rate limits. | `2` |
| `--cache-dir` | Diretório para armazenar páginas baixadas localmente. | `.cache` |
| `--max-pages` | Número máximo de páginas a crawlear. | `500` |
| `--min-content-length` | Tamanho mínimo de conteúdo (em caracteres) para considerar uma página válida. Páginas menores são descartadas. | `100` |
| `--clear-cache` | Limpa o diretório de cache antes de iniciar o crawling. | (flag, não tem valor) |

## 📁 Estrutura do Projeto

```
.
├── crawler.py          # Script principal
├── README.md           # Este arquivo
├── requirements.txt    # Lista de dependências
├── crawler.log         # Log detalhado (gerado automaticamente)
├── output.md           # Documentação gerada (nome customizável)
├── .cache/            # Cache de páginas HTML (criado automaticamente)
└── venv/              # (opcional) Ambiente virtual
```

## 📝 Arquivo `requirements.txt`

```txt
requests>=2.31.0
beautifulsoup4>=4.12.0
tqdm>=4.66.0
lxml>=4.9.0
```

Para instalar a partir do arquivo:

```bash
pip3 install -r requirements.txt
```

## 📊 Saída

Após a execução, você terá:

- **Arquivo de Saída:** Um único arquivo `.md` contendo toda a documentação com:
  - Sumário (Table of Contents) com links internos
  - Conteúdo de todas as páginas em Markdown
  - Links para as fontes originais
- **Arquivo de Log:** `crawler.log` com detalhes técnicos do processo
- **Cache:** Pasta `.cache/` com páginas HTML baixadas (para re-execuções mais rápidas)

### Exemplo de Resumo Final

```
============================================================
📊 RESUMO DO CRAWLING
============================================================
✅ Páginas Crawleadas: 47
❌ Páginas Falhas: 0
🗑️  Páginas Filtradas (junk): 2
📏 Páginas Muito Pequenas: 3
🔗 Links Encontrados: 52
🌐 Links Externos (ignorados): 15
♻️  Links Duplicados (ignorados): 8
📝 Total de Caracteres: 245,892
📖 Total de Palavras: 38,421
💾 Tamanho do Arquivo: 189.45 KB
⏱️  Tempo Total: 00:02:34
============================================================
```

## 🔍 Melhorias na Versão Atual

### 🆕 O que mudou?

1. **Extração de Links Corrigida**
   - Links agora são extraídos ANTES de destruir tags `<nav>`, `<header>`, `<footer>`
   - Suporta links relativos e absolutos corretamente
   - Normalização robusta de URLs (trailing slashes, query params, fragments)

2. **Lógica de Domínio Melhorada**
   - Crawleia todo o domínio base (ex: todo `docs.minimals.cc`)
   - Não mais limitado ao path inicial

3. **Logging Detalhado**
   - Estatísticas de links encontrados, externos, duplicados
   - Log de cada URL processada
   - Facilita debug quando páginas não são encontradas

4. **Filtro Conservador**
   - Remove apenas páginas explicitamente inúteis (privacy-policy, terms-of-service, cookie-policy, legal)
   - Mantém cobertura completa da documentação

5. **Melhor Conversão Markdown**
   - Suporte a `<blockquote>`
   - Detecção de `main`, `article` ou classes comuns (`content`, `main`, `body`)
   - Preserva estrutura de código com syntax highlighting

## ⚠️ Avisos e Boas Práticas

- **Respeite robots.txt**: Use com responsabilidade e respeite os termos de serviço dos sites
- **Rate Limiting**: Se crawlear sites grandes, considere usar menos workers ou adicionar delays
- **Cache**: O cache local pode ocupar espaço em disco. Use `--clear-cache` para limpar
- **Debugging**: Se poucas páginas foram crawleadas, verifique `crawler.log` para entender o motivo
- **Python 3**: Sempre use `python3` e `pip3` no Linux/Mac para evitar conflitos com Python 2

## 🐛 Troubleshooting

### Problema: "ModuleNotFoundError: No module named 'bs4'"

**Solução:**
```bash
pip3 install beautifulsoup4 requests tqdm lxml
```

### Problema: Poucas páginas crawleadas

**Diagnóstico:**
1. Verifique `crawler.log` para ver quais links foram encontrados
2. Teste manualmente se os links funcionam no navegador
3. Verifique se o site usa JavaScript para renderizar conteúdo (SPAs não são suportados)

**Solução para SPAs:**
- Este crawler não suporta sites que renderizam conteúdo via JavaScript (React, Vue, Angular SPAs)
- Para esses casos, considere usar Selenium ou Puppeteer

### Problema: "Permission denied" ao salvar arquivo

**Solução:**
```bash
# Verifique permissões do diretório
ls -la

# Rode com permissões adequadas ou mude o diretório de saída
python3 crawler.py --base-url https://... --output ~/Downloads/docs.md
```

## 🤝 Contribuições

Pull requests são bem-vindos! Fique à vontade para sugerir melhorias, correções ou novas funcionalidades.

### Roadmap de Melhorias Futuras

- [ ] Suporte a autenticação (sites que requerem login)
- [ ] Exportação para outros formatos (PDF, HTML, EPUB)
- [ ] Suporte a SPAs (com Selenium/Puppeteer)
- [ ] Rate limiting configurável
- [ ] Filtros customizáveis via regex
- [ ] Modo incremental (atualizar apenas páginas modificadas)

## 📄 Licença

Este projeto é open source. Use livremente, mas com responsabilidade.

---

**Desenvolvido para crawlear documentações de forma eficiente e gerar Markdown de alta qualidade.**
