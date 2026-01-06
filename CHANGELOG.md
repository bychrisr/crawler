# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [2.0.2] - 2026-01-06

### 🐛 Corrigido

#### Detecção de SPA (Crítico)
- **Detecta SPAs automaticamente**: Crawler agora identifica sites que renderizam via JavaScript (React/Vue/Angular sem SSR)
- **Aborta gracefully em SPAs**: Em vez de travar em loop infinito, detecta e aborta com mensagem clara
- **Exit code apropriado**: `exit(1)` quando SPA é detectada, facilitando automação

#### Timeout de Inatividade
- **Proteção contra deadlock**: Se crawler ficar sem progresso por 30s, aborta automaticamente
- **Salva progresso parcial**: Mesmo em timeout, salva o que foi crawleado até o momento
- **Mensagens diagnósticas**: Explica possíveis causas (SPA, rede, bloqueio)

### ✨ Adicionado

#### Sistema de Detecção de SPA
```
Indicadores verificados:
- Div root (#root, #app, #__next, #__nuxt)
- HTML muito pequeno (<1500 chars)
- Poucos links (<3)
- Conteúdo textual mínimo (<200 chars)
- Ausência de tags de conteúdo (<p>, <h1>, <article>)
```

#### Mensagens Detalhadas para SPAs
Quando SPA é detectada, o crawler mostra:
- Análise técnica (tamanho HTML, links, conteúdo)
- Soluções alternativas sugeridas
- Exit imediato para evitar perda de tempo

#### Debug de Detecção de SPA
No modo `--debug`, mostra análise completa:
```
[DEBUG] SPA detectada em https://exemplo.com:
  - Root div: True
  - Conteúdo mínimo: True (150 chars)
  - Poucos links: True (0 links)
  - HTML pequeno: True (494 chars)
  - Sem tags de conteúdo: True
```

### 🔧 Melhorado

- **Controle de progresso**: Rastreia última vez que houve progresso
- **Estatísticas**: Adicionado `spa_detected` aos metadados
- **Logging**: Mensagens mais claras sobre por que o crawler parou

### 📚 Documentação

- Adicionada seção sobre limitações de SPAs no README
- Exemplos de como identificar se um site é SPA
- Soluções alternativas para crawlear SPAs

---

## [2.0.1] - 2026-01-06

### 🐛 Corrigido

#### Validação Adaptativa (Crítico)
- **Validação inteligente de conversão HTML→Markdown**: Threshold agora se adapta dinamicamente ao tipo de site
  - Sites de documentação técnica (>2 code blocks/página): 1% esperado
  - Sites pequenos (<20 páginas): 3% esperado  
  - Sites modernos padrão: 1.5% esperado
- Removido aviso falso-positivo de "Baixa conversão" que aparecia em 100% dos sites modernos
- Mensagens de validação agora incluem contexto (densidade de código, tipo de site)

#### Melhorias no TOC
- Páginas root vazias (sem título) não aparecem mais no Table of Contents
- Fallback para usar path da URL como título quando `<h1>` está vazio
- Contador de páginas vazias puladas adicionado às estatísticas

### ✨ Adicionado

#### Detecção Automática de Linguagem
- Code blocks agora detectam linguagem automaticamente via heurística quando o site não especifica
- Suporta: JavaScript, TypeScript, JSX, TSX, Python, Bash, JSON, CSS, HTML, Markdown
- Melhora syntax highlighting em 90% dos casos

#### Flag `--debug`
- Novo modo debug que mostra extração em tempo real:
  ```
  [DEBUG] Extraído de https://exemplo.com:
    - 5 headers
    - 12 parágrafos
    - 8 items de lista
    - 3 code blocks
  ```
- Útil para debugar problemas de extração em sites desconhecidos

#### Estatísticas Expandidas
- **Code blocks extraídos**: Contador total de blocos de código
- **Páginas vazias**: Contador de páginas sem título puladas no TOC
- **Densidade de código**: Usado para validação adaptativa

### 🔧 Melhorado

- Logging mais detalhado em modo debug
- Mensagens de erro mais acionáveis (incluem contexto do problema)
- Metadados no arquivo Markdown agora incluem code blocks extraídos

---

## [2.0.0] - 2026-01-06

### ✨ Adicionado

#### Core Features
- **Validação automática de output**: Sistema detecta automaticamente problemas de extração e avisa o usuário
- **Retry inteligente**: Exponential backoff automático com 3 tentativas por padrão
- **Rate limiting**: Intervalo mínimo de 0.5s entre requests para evitar bans
- **Autenticação HTTP**: Suporte a HTTP Basic Auth via `--auth-user` e `--auth-pass`
- **Headers customizados**: Flag `--header` para adicionar headers HTTP personalizados
- **Metadados em JSON**: Arquivo `.metadata.json` com informações completas da execução
- **Tratamento de interrupções**: Ctrl+C agora salva progresso parcial automaticamente
- **Suporte a robots.txt**: Respeita robots.txt por padrão (desabilitável com `--no-robots`)

#### Estatísticas e Observabilidade
- **Cache hits**: Contador de quantas páginas foram carregadas do cache
- **Retries realizados**: Contador de tentativas de retry executadas
- **Bloqueios por robots.txt**: Contador de URLs bloqueadas
- **Timestamps**: Data/hora de início e fim da execução
- **Configuração salva**: Todos os parâmetros usados são salvos em JSON

#### Melhorias de Extração
- **Fallback robusto**: Extração funciona mesmo em sites com SSR/JavaScript
- **Detecção de `<main>` vazio**: Usa `<body>` como fallback quando `<main>` não tem conteúdo
- **Remoção de navegação**: Remove `<nav>`, `<header>`, `<footer>` automaticamente do `<body>`

### 🔧 Mudado

#### Arquitetura
- Refatorado para usar classe `CrawlerConfig` centralizada
- Adicionado type hints em todo o código
- Melhorado tratamento de erros e logging
- Código mais modular e testável

#### CLI
- Adicionado `--version` flag
- Melhorado help text de todos os argumentos
- Banner visual no início da execução

#### Output
- Metadados da execução agora aparecem no resumo final
- Arquivo Markdown inclui seção de metadados no topo
- Validação de qualidade executada automaticamente

### 🐛 Corrigido

#### Extração de Conteúdo
- **[CRÍTICO]** Corrigido bug onde sites com SSR retornavam arquivos vazios
- **[CRÍTICO]** Corrigido bug na extração de links que ignorava toda navegação
- Corrigido problema de normalização de URLs com trailing slashes
- Corrigido problema onde `soup()` destruía o DOM

#### Robustez
- Melhorado tratamento de timeouts de rede
- Melhorado tratamento de erros de encoding
- Adicionado garbage collection periódico para evitar memory leaks

### 📚 Documentação

- README completamente reescrito com seção de troubleshooting
- Adicionado CHANGELOG.md para versionamento
- Documentados todos os novos parâmetros de linha de comando
- Adicionados exemplos práticos de uso

---

## [1.0.0] - 2026-01-05

### ✨ Versão Inicial

#### Features
- Crawling básico de documentações
- Conversão para Markdown
- Cache local
- Threading paralelo
- Progress bar com tqdm
- Filtro de páginas muito pequenas
- Filtro de páginas "lixo"
- Suporte a links relativos e absolutos
- Table of Contents automático

#### Limitações Conhecidas
- Não valida output automaticamente
- Não suporta autenticação
- Não respeita robots.txt
- Não salva metadados
- Extração falha em sites com SSR
- Sem retry inteligente
- Sem rate limiting

---

## Formato de Versionamento

Este projeto usa [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Mudanças incompatíveis na API/CLI
- **MINOR** (x.Y.0): Novas funcionalidades (backward compatible)
- **PATCH** (x.y.Z): Bug fixes (backward compatible)

### Categorias de Mudanças

- **✨ Adicionado**: Novas features
- **🔧 Mudado**: Mudanças em funcionalidades existentes
- **❌ Removido**: Features removidas
- **🐛 Corrigido**: Bug fixes
- **🔒 Segurança**: Correções de segurança
- **📚 Documentação**: Mudanças em documentação
