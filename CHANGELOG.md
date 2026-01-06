# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

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
