# Documentation Crawler

Um crawler eficiente e otimizado para baixar documentações de sites e convertê-las em um único arquivo Markdown com **sumário automático (TOC)**.

## ⚙️ Funcionalidades

- 🔗 **Resolução de links relativos** e controle de domínio
- 📂 **Conversão para único arquivo Markdown** com TOC
- 📝 **Geração automática de sumário (Table of Contents)**
- 🛑 **Timeout e retries** para lidar com falhas de rede
- 🗂 **Log detalhado** salvo em `crawler.log`
- ⚡ **Threads para aceleração** de downloads
- 💾 **Cache local** para evitar downloads repetidos
- 🎨 **Barra de progresso** com `tqdm`
- 📊 **Estatísticas detalhadas** ao final do processo
- 🧹 **Filtro de conteúdo** (páginas muito pequenas ou irrelevantes)

## 🛠️ Requisitos

- Python 3.7+
- `pip` (geralmente vem com o Python)

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
python -m venv venv

# Ativa o ambiente virtual
# No Linux/Mac:
source venv/bin/activate
# No Windows:
venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install requests beautifulsoup4 tqdm
```

> **Nota:** Se você ativou o ambiente virtual, as dependências serão instaladas nele e não afetarão o Python do seu sistema.

### 4. Execute o script

#### Uso Básico

```bash
python crawler.py --base-url <URL_DA_DOCUMENTACAO>
```

Este comando usará os **valores padrão** para todos os outros parâmetros.

#### Exemplos Avançados

**Exemplo completo com todos os parâmetros:**

```bash
python crawler.py \
  --base-url https://tradingview.github.io/lightweight-charts/docs \
  --output minha_documentacao.md \
  --workers 2 \
  --max-pages 500 \
  --min-content-length 100 \
  --cache-dir .cache
```

**Exemplo com limpeza de cache e menos páginas:**

```bash
python crawler.py \
  --base-url https://exemplo.com/docs \
  --output docs_simplificadas.md \
  --max-pages 100 \
  --clear-cache
```

## 🎛️ Opções de Comando

| Argumento | Descrição | Valor Padrão |
| :--- | :--- | :--- |
| `--base-url` | **(Obrigatório)** A URL base da documentação a ser crawleada. | |
| `--output` | Nome do arquivo Markdown de saída. | `output.md` |
| `--workers` | Número de threads para downloads paralelos. | `2` |
| `--cache-dir` | Diretório para armazenar páginas baixadas localmente. | `.cache` |
| `--max-pages` | Número máximo de páginas a crawlear. | `500` |
| `--min-content-length` | Tamanho mínimo de conteúdo (em caracteres) para considerar uma página válida. Páginas menores são descartadas. | `100` |
| `--clear-cache` | Limpa o diretório de cache antes de iniciar o crawling. | (flag, não tem valor) |

## 📁 Estrutura do Projeto

```
.
├── crawler.py          # Script principal
├── README.md           # Este arquivo
├── requirements.txt    # (opcional) Lista de dependências
└── venv/              # (opcional) Ambiente virtual
```

## 📝 Exemplo de `requirements.txt`

Se você quiser manter um arquivo com as dependências explicitamente:

```txt
requests>=2.25.1
beautifulsoup4>=4.9.3
tqdm>=4.62.3
```

Para instalar a partir do arquivo:

```bash
pip install -r requirements.txt
```

## 📊 Saída

- **Arquivo de Saída:** Um único arquivo `.md` contendo toda a documentação.
- **Arquivo de Log:** `crawler.log` com detalhes do processo.
- **Cache:** Pasta especificada (`--cache-dir`) com páginas HTML baixadas.

Após a conclusão, o script imprime um resumo com estatísticas como:

- Páginas Crawleadas
- Páginas Falhas
- Páginas Filtradas
- Total de Caracteres e Palavras
- Tamanho do Arquivo de Saída
- Tempo Total de Execução

## ⚠️ Avisos

- Use com responsabilidade e respeite os `robots.txt` e os termos de serviço dos sites.
- Baixar grandes volumes de dados pode ser intenso em recursos e tempo.
- A opção `--max-pages` e `--min-content-length` ajudam a controlar o escopo e a qualidade da coleta.
- O cache local pode ocupar espaço em disco, especialmente para sites grandes.

## 🤝 Contribuições

Pull requests são bem-vindos! Fique à vontade para sugerir melhorias, correções ou novas funcionalidades.
```