#!/usr/bin/env python3
import argparse
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from tqdm import tqdm
import logging
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import re

# Configuração de logging
logging.basicConfig(
    filename="crawler.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class UXEnhancedCrawler:
    def __init__(self, base_url, output_file="output.md", max_workers=2, cache_dir=".cache", max_pages=1000, min_content_length=100):
        self.base_url = base_url
        self.output_file = output_file
        self.max_workers = max_workers
        self.cache_dir = cache_dir
        self.max_pages = max_pages
        self.min_content_length = min_content_length
        self.visited_urls = set()
        self.pages_content = {}
        self.url_queue = []
        self.lock = threading.Lock()
        self.stats = {
            'fetched': 0,
            'failed': 0,
            'too_small': 0,
            'filtered': 0,
            'total_chars': 0,
            'total_words': 0,
            'links_found': 0,
            'links_skipped_external': 0,
            'links_skipped_duplicate': 0
        }

        # Padrões para detectar páginas "lixo" - mais conservador
        self.junk_patterns = re.compile(r'^(privacy-policy|terms-of-service|cookie-policy|legal)$', re.IGNORECASE)

        # Extrai domínio base e scheme
        parsed_base = urlparse(self.base_url)
        self.base_domain = parsed_base.netloc
        self.base_scheme = parsed_base.scheme

        # Cria diretório de cache
        os.makedirs(self.cache_dir, exist_ok=True)

        logging.info(f"Crawler inicializado - Base domain: {self.base_domain}")

    def _normalize_url(self, url):
        """
        Normaliza URL removendo fragmentos, query params opcionais e garantindo trailing slash consistente.
        """
        parsed = urlparse(url)

        # Remove fragment (#section)
        clean_path = parsed.path

        # Garante trailing slash para paths (exceto arquivos)
        if not clean_path.endswith('/') and '.' not in clean_path.split('/')[-1]:
            clean_path = clean_path + '/'

        # Reconstrói URL sem query/fragment
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            clean_path,
            '',  # params
            '',  # query - removido para evitar duplicatas
            ''   # fragment
        ))

        return normalized

    def _get_cache_path(self, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.html")

    def fetch(self, url, retries=3, timeout=10):
        cache_path = self._get_cache_path(url)

        # Tenta carregar do cache
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    logging.info(f"Cache hit: {url}")
                    return f.read()
            except Exception as e:
                logging.warning(f"Erro ao ler cache de {url}: {e}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        for i in range(retries):
            try:
                logging.info(f"Fetching ({i+1}/{retries}): {url}")
                response = requests.get(url, timeout=timeout, headers=headers)
                if response.status_code == 200:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    logging.info(f"Success: {url}")
                    return response.text
                else:
                    logging.warning(f"HTTP {response.status_code} em {url}")
            except Exception as e:
                logging.error(f"Erro ao acessar {url} (tentativa {i+1}): {e}")
            time.sleep(1)

        logging.error(f"Failed após {retries} tentativas: {url}")
        return None

    def _extract_links(self, current_url, html):
        """
        Extrai links do HTML ANTES de destruir tags de navegação.
        Retorna apenas links do mesmo domínio.
        """
        soup = BeautifulSoup(html, "html.parser")

        links = set()
        links_found_raw = 0

        # Extrai TODOS os links antes de qualquer modificação no DOM
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            links_found_raw += 1

            # Ignora anchors puros (#section) e javascript:
            if href.startswith('#') or href.startswith('javascript:'):
                continue

            # Resolve URL relativa para absoluta
            full_url = urljoin(current_url, href)
            parsed = urlparse(full_url)

            # Filtro 1: Mesmo domínio
            if parsed.netloc != self.base_domain:
                with self.lock:
                    self.stats['links_skipped_external'] += 1
                continue

            # Normaliza URL
            normalized = self._normalize_url(full_url)

            # Filtro 2: Já visitado
            if normalized in self.visited_urls:
                with self.lock:
                    self.stats['links_skipped_duplicate'] += 1
                continue

            # Filtro 3: Páginas "lixo" (muito conservador)
            path_parts = parsed.path.strip('/').split('/')
            if any(self.junk_patterns.match(part) for part in path_parts):
                with self.lock:
                    self.stats['filtered'] += 1
                logging.info(f"Filtrado (junk pattern): {normalized}")
                continue

            links.add(normalized)

        with self.lock:
            self.stats['links_found'] += len(links)

        logging.info(f"Links encontrados em {current_url}: {links_found_raw} raw -> {len(links)} válidos")

        return list(links)

    def _is_junk_page(self, url, title, content):
        """Detecta se a página é "lixo" - versão mais conservadora."""
        title_lower = title.lower() if title else ""
        path = urlparse(url).path.strip('/').split('/')

        # Apenas bloqueia páginas explicitamente de políticas/legal
        for part in path:
            if self.junk_patterns.match(part):
                return True

        if self.junk_patterns.search(title_lower):
            return True

        return False

    def crawl(self):
        initial_normalized = self._normalize_url(self.base_url)
        self.visited_urls.add(initial_normalized)
        self.url_queue = [self.base_url]

        processed_count = 0

        print(f"\n🔍 Iniciando crawling em: {self.base_url}")
        print(f"🌐 Domínio base: {self.base_domain}")
        print(f"📦 Limite de páginas: {self.max_pages}")
        print(f"⚡ Workers: {self.max_workers}")
        print(f"💾 Cache: {self.cache_dir}")
        print(f"📏 Filtro de conteúdo (min. {self.min_content_length} chars)\n")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Inicia primeiras requisições
            initial_batch = min(self.max_workers * 2, len(self.url_queue))
            future_to_url = {
                executor.submit(self.fetch, url): url
                for url in self.url_queue[:initial_batch]
            }
            self.url_queue = self.url_queue[initial_batch:]

            with tqdm(desc="Crawleando páginas", total=self.max_pages, unit="página", leave=False) as pbar:
                while future_to_url and processed_count < self.max_pages:
                    for future in as_completed(future_to_url):
                        url = future_to_url[future]
                        try:
                            html = future.result()
                            if html:
                                # --- Análise e Filtragem ---
                                soup = BeautifulSoup(html, "html.parser")

                                # Extrai título
                                title_tag = soup.find("h1")
                                title = title_tag.get_text().strip() if title_tag else urlparse(url).path.split('/')[-1]

                                # Filtrar páginas "lixo"
                                if self._is_junk_page(url, title, html):
                                    with self.lock:
                                        self.stats['filtered'] += 1
                                    logging.info(f"Página filtrada (junk): {url}")
                                    continue

                                # Filtrar páginas muito pequenas
                                content_text = soup.get_text(strip=True)
                                if len(content_text) < self.min_content_length:
                                    with self.lock:
                                        self.stats['too_small'] += 1
                                    logging.info(f"Página muito pequena ({len(content_text)} chars): {url}")
                                    continue

                                # Armazena conteúdo
                                with self.lock:
                                    self.pages_content[url] = html
                                    self.stats['fetched'] += 1
                                    self.stats['total_chars'] += len(html)
                                    self.stats['total_words'] += len(content_text.split())
                                    processed_count += 1
                                    pbar.update(1)

                                logging.info(f"Página processada ({processed_count}/{self.max_pages}): {url}")

                                # Extrai novos links (APÓS processar a página atual)
                                new_links = self._extract_links(url, html)

                                with self.lock:
                                    for link in new_links:
                                        if len(self.visited_urls) < self.max_pages:
                                            self.visited_urls.add(link)
                                            self.url_queue.append(link)

                                # Submete próximas URLs
                                while self.url_queue and len(future_to_url) < self.max_workers * 2:
                                    next_url = self.url_queue.pop(0)
                                    new_future = executor.submit(self.fetch, next_url)
                                    future_to_url[new_future] = next_url
                            else:
                                with self.lock:
                                    self.stats['failed'] += 1
                                logging.error(f"Fetch falhou: {url}")

                        except Exception as e:
                            logging.error(f"Erro processando {url}: {e}")
                            with self.lock:
                                self.stats['failed'] += 1

                        del future_to_url[future]

                        # Garbage collection periódico
                        if processed_count % 50 == 0:
                            gc.collect()

                        if processed_count >= self.max_pages:
                            break

    def _html_to_markdown(self, html, url):
        soup = BeautifulSoup(html, "html.parser")

        # Limpa tags irrelevantes para o conteúdo final
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        content = []

        # Título principal
        h1 = soup.find("h1")
        if h1:
            content.append(f"# {h1.get_text().strip()}\n")
        else:
            content.append(f"# {urlparse(url).path.replace('/', ' ').strip()}\n")

        # Estratégia de fallback para encontrar conteúdo principal
        main = soup.find("main") or soup.find("article") or soup.find(class_=re.compile(r'content|main|body', re.I))

        # Se main existe mas está vazio (sites com JS), usa body
        if main:
            # Verifica se tem conteúdo útil
            has_content = main.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'pre'], limit=3)
            if not has_content:
                logging.warning(f"Main vazio em {url}, usando body como fallback")
                main = soup.body
        else:
            main = soup.body or soup

        # Se usar body, remove navegação/footer
        if main and main.name == 'body':
            for tag in main.find_all(['nav', 'header', 'footer', 'aside']):
                tag.decompose()

        # Extrai conteúdo
        for element in main.find_all():
            if element.name in ["h2", "h3", "h4", "h5", "h6"]:
                level = int(element.name[1])
                text = element.get_text().strip()
                if text:
                    content.append(f"{'#' * level} {text}\n")
            elif element.name == "p":
                text = element.get_text().strip()
                if text:
                    content.append(text + "\n")
            elif element.name in ["ul", "ol"]:
                for li in element.find_all("li", recursive=False):
                    li_text = li.get_text().strip()
                    if li_text:
                        content.append(f"- {li_text}\n")
            elif element.name == "pre":
                code_text = element.get_text()
                lang = "text"
                if element.find("code"):
                    code_class = element.find("code").get("class", [])
                    for cls in code_class:
                        if cls.startswith("language-"):
                            lang = cls.split("-", 1)[1]
                            break
                content.append(f"```{lang}\n{code_text}\n```\n")
            elif element.name == "code" and not element.find_parent("pre"):
                content.append(f"`{element.get_text()}`")
            elif element.name == "blockquote":
                quote_text = element.get_text().strip()
                if quote_text:
                    content.append(f"> {quote_text}\n")

        return "\n".join(content).strip()

    def save_markdown(self):
        print(f"\n💾 Salvando documentação em {self.output_file}...")

        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(f"# Documentação: {self.base_url}\n\n")
            f.write(f"*Gerado automaticamente em {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write("## Table of Contents\n\n")

            # Gera TOC
            for url in sorted(self.pages_content.keys()):
                html = self.pages_content[url]
                soup = BeautifulSoup(html, "html.parser")
                h1 = soup.find("h1")
                title = h1.get_text().strip() if h1 else urlparse(url).path.replace('/', ' ').strip()
                anchor = re.sub(r'[^\w\s-]', '', title.lower()).replace(" ", "-")
                f.write(f"- [{title}](#{anchor})\n")

            f.write("\n---\n\n")

            # Gera conteúdo
            for url in sorted(self.pages_content.keys()):
                html = self.pages_content[url]
                markdown_content = self._html_to_markdown(html, url)
                f.write(markdown_content + "\n\n")
                f.write(f"*Fonte: [{url}]({url})*\n\n")
                f.write("---\n\n")

        logging.info(f"Documentação salva: {self.output_file}")

    def print_summary(self):
        """Imprime um resumo das estatísticas do crawling."""
        print("\n" + "="*60)
        print("📊 RESUMO DO CRAWLING")
        print("="*60)
        print(f"✅ Páginas Crawleadas: {self.stats['fetched']}")
        print(f"❌ Páginas Falhas: {self.stats['failed']}")
        print(f"🗑️  Páginas Filtradas (junk): {self.stats['filtered']}")
        print(f"📏 Páginas Muito Pequenas: {self.stats['too_small']}")
        print(f"🔗 Links Encontrados: {self.stats['links_found']}")
        print(f"🌐 Links Externos (ignorados): {self.stats['links_skipped_external']}")
        print(f"♻️  Links Duplicados (ignorados): {self.stats['links_skipped_duplicate']}")
        print(f"📝 Total de Caracteres: {self.stats['total_chars']:,}")
        print(f"📖 Total de Palavras: {self.stats['total_words']:,}")

        if os.path.exists(self.output_file):
            file_size = os.path.getsize(self.output_file)
            print(f"💾 Tamanho do Arquivo: {file_size:,} bytes ({file_size/1024:.2f} KB)")

        elapsed = time.time() - self.start_time
        print(f"⏱️  Tempo Total: {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
        print("="*60)

        # Sugestões
        if self.stats['fetched'] < 5:
            print("\n⚠️  ATENÇÃO: Poucas páginas crawleadas!")
            print("   Verifique se a URL base está correta e se o site permite crawling.")
            print(f"   Logs detalhados em: crawler.log")

    def run(self):
        self.start_time = time.time()
        logging.info(f"="*60)
        logging.info(f"Iniciando crawler em {self.base_url}")
        logging.info(f"Domínio base: {self.base_domain}")
        logging.info(f"="*60)

        self.crawl()
        logging.info(f"Total de páginas crawleadas: {len(self.pages_content)}")

        self.save_markdown()

        self.print_summary()

def main():
    parser = argparse.ArgumentParser(
        description="Crawler de documentação otimizado com extração robusta de links",
        epilog="Exemplo: python3 crawler.py --base-url https://docs.exemplo.com/"
    )
    parser.add_argument("--base-url", required=True, help="URL base da documentação")
    parser.add_argument("--output", default="output.md", help="Arquivo de saída (padrão: output.md)")
    parser.add_argument("--workers", type=int, default=2, help="Número de threads (padrão: 2)")
    parser.add_argument("--cache-dir", default=".cache", help="Diretório para cache local (padrão: .cache)")
    parser.add_argument("--max-pages", type=int, default=500, help="Número máximo de páginas (padrão: 500)")
    parser.add_argument("--min-content-length", type=int, default=100, help="Tamanho mínimo de conteúdo em caracteres (padrão: 100)")
    parser.add_argument("--clear-cache", action="store_true", help="Limpa o cache antes de iniciar")

    args = parser.parse_args()

    # Limpa cache se solicitado
    if args.clear_cache and os.path.exists(args.cache_dir):
        import shutil
        print(f"🗑️  Limpando cache em {args.cache_dir}...")
        shutil.rmtree(args.cache_dir)
        os.makedirs(args.cache_dir, exist_ok=True)

    crawler = UXEnhancedCrawler(
        base_url=args.base_url,
        output_file=args.output,
        max_workers=args.workers,
        cache_dir=args.cache_dir,
        max_pages=args.max_pages,
        min_content_length=args.min_content_length
    )
    crawler.run()

if __name__ == "__main__":
    main()
