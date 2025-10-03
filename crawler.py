#!/usr/bin/env python3
import argparse
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
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
        self.min_content_length = min_content_length  # Novo: filtro de tamanho
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
            'total_words': 0
        }
        
        # Padrões para detectar páginas "lixo" (opcional)
        self.junk_patterns = re.compile(r'(privacy|terms|legal|licen[cs]e|cookies|about)', re.IGNORECASE)
        
        # Cria diretório de cache
        os.makedirs(self.cache_dir, exist_ok=True)

    def _normalize_url(self, url):
        parsed = urlparse(url)
        clean_path = parsed.path.rstrip('/')
        return f"{parsed.scheme}://{parsed.netloc}{clean_path}"

    def _get_cache_path(self, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.html")

    def fetch(self, url, retries=3, timeout=10):
        cache_path = self._get_cache_path(url)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                pass

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        for i in range(retries):
            try:
                response = requests.get(url, timeout=timeout, headers=headers)
                if response.status_code == 200:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    return response.text
                else:
                    logging.warning(f"Falha {response.status_code} em {url}")
            except Exception as e:
                logging.error(f"Erro ao acessar {url} (tentativa {i+1}): {e}")
            time.sleep(1)
        return None

    def _extract_links(self, current_url, html):
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove tags irrelevantes para acelerar parsing
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        links = set()
        base_domain = urlparse(self.base_url).netloc
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(current_url, href)
            
            parsed = urlparse(full_url)
            if (parsed.netloc == base_domain and 
                full_url.startswith(self.base_url) and
                self._normalize_url(full_url) not in self.visited_urls):
                
                normalized = self._normalize_url(full_url)
                if normalized not in self.visited_urls:
                    links.add(full_url)
        
        return list(links)

    def _is_junk_page(self, url, title, content):
        """Detecta se a página é "lixo" com base em título ou URL."""
        title_lower = title.lower() if title else ""
        url_lower = url.lower()
        
        return (self.junk_patterns.search(title_lower) or 
                self.junk_patterns.search(url_lower))

    def crawl(self):
        initial_normalized = self._normalize_url(self.base_url)
        self.visited_urls.add(initial_normalized)
        self.url_queue = [self.base_url]
        
        processed_count = 0
        
        print(f"\n🔍 Iniciando crawling em: {self.base_url}")
        print(f"📦 Limite de páginas: {self.max_pages}")
        print(f" Workers: {self.max_workers}")
        print(f"📁 Cache: {self.cache_dir}")
        print(f"📏 Filtro de conteúdo (min. {self.min_content_length} chars)\n")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.fetch, url): url for url in self.url_queue[:min(10, len(self.url_queue))]}
            self.url_queue = self.url_queue[min(10, len(self.url_queue)):]

            with tqdm(desc="Crawleando páginas", total=self.max_pages, unit="página", leave=False) as pbar:
                while future_to_url and processed_count < self.max_pages:
                    for future in as_completed(future_to_url):
                        url = future_to_url[future]
                        try:
                            html = future.result()
                            if html:
                                # --- Análise e Filtragem ---
                                soup = BeautifulSoup(html, "html.parser")
                                title_tag = soup.find("h1")
                                title = title_tag.get_text().strip() if title_tag else urlparse(url).path.split('/')[-1]
                                
                                # Filtrar páginas "lixo"
                                if self._is_junk_page(url, title, html):
                                    with self.lock:
                                        self.stats['filtered'] += 1
                                    continue
                                
                                # Filtrar páginas muito pequenas
                                content_text = soup.get_text(strip=True)
                                if len(content_text) < self.min_content_length:
                                    with self.lock:
                                        self.stats['too_small'] += 1
                                    continue
                                
                                # Armazena conteúdo
                                with self.lock:
                                    self.pages_content[url] = html
                                    self.stats['fetched'] += 1
                                    self.stats['total_chars'] += len(html)
                                    self.stats['total_words'] += len(content_text.split())
                                    processed_count += 1
                                    pbar.update(1)
                                
                                # Extrai novos links
                                new_links = self._extract_links(url, html)
                                
                                with self.lock:
                                    for link in new_links:
                                        normalized = self._normalize_url(link)
                                        if normalized not in self.visited_urls and len(self.visited_urls) < self.max_pages:
                                            self.visited_urls.add(normalized)
                                            self.url_queue.append(link)
                                
                                if self.url_queue and len(future_to_url) < self.max_workers:
                                    next_url = self.url_queue.pop(0)
                                    new_future = executor.submit(self.fetch, next_url)
                                    future_to_url[new_future] = next_url
                            else:
                                with self.lock:
                                    self.stats['failed'] += 1
                            
                        except Exception as e:
                            logging.error(f"Erro processando {url}: {e}")
                            with self.lock:
                                self.stats['failed'] += 1
                        
                        del future_to_url[future]
                        
                        if processed_count % 50 == 0:
                            gc.collect()
                        
                        if processed_count >= self.max_pages:
                            break

    def _html_to_markdown(self, html, url):
        soup = BeautifulSoup(html, "html.parser")
        
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        content = []
        
        h1 = soup.find("h1")
        if h1:
            content.append(f"# {h1.get_text().strip()}\n")
        else:
            content.append(f"# {urlparse(url).path.replace('/', ' ').strip()}\n")

        main = soup.find("main") or soup.find("article") or soup.body or soup
        for element in main.find_all():
            if element.name in ["h2", "h3", "h4", "h5", "h6"]:
                level = int(element.name[1])
                content.append(f"{'#' * level} {element.get_text().strip()}\n")
            elif element.name == "p":
                text = element.get_text().strip()
                if text:
                    content.append(text + "\n")
            elif element.name in ["ul", "ol"]:
                for li in element.find_all("li", recursive=False):
                    content.append(f"- {li.get_text().strip()}\n")
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

        return "\n".join(content).strip()

    def save_markdown(self):
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(f"# Documentação: {self.base_url}\n\n")
            f.write("## Table of Contents\n")
            
            for url in self.pages_content.keys():
                html = self.pages_content[url]
                soup = BeautifulSoup(html, "html.parser")
                h1 = soup.find("h1")
                title = h1.get_text().strip() if h1 else urlparse(url).path.replace('/', ' ').strip()
                anchor = title.lower().replace(" ", "-").replace(":", "").replace("(", "").replace(")", "")
                f.write(f"- [{title}](#{anchor})\n")
            
            f.write("\n---\n\n")
            
            for url in self.pages_content.keys():
                html = self.pages_content[url]
                markdown_content = self._html_to_markdown(html, url)
                f.write(markdown_content + "\n\n---\n\n")

    def print_summary(self):
        """Imprime um resumo das estatísticas do crawling."""
        print("\n" + "="*50)
        print("📊 RESUMO DO CRAWLING")
        print("="*50)
        print(f"Páginas Crawleadas: {self.stats['fetched']}")
        print(f"Páginas Falhas: {self.stats['failed']}")
        print(f"Páginas Filtradas (lixo): {self.stats['filtered']}")
        print(f"Páginas Muito Pequenas (<{self.min_content_length} chars): {self.stats['too_small']}")
        print(f"Total de Caracteres: {self.stats['total_chars']:,}")
        print(f"Total de Palavras: {self.stats['total_words']:,}")
        print(f"Tamanho do Arquivo de Saída: {os.path.getsize(self.output_file) if os.path.exists(self.output_file) else 0:,} bytes")
        print(f"Tempo Total: {time.strftime('%H:%M:%S', time.gmtime(time.time() - self.start_time))}")
        print("="*50)

    def run(self):
        self.start_time = time.time()
        logging.info(f"Iniciando crawler otimizado em {self.base_url}")
        
        self.crawl()
        logging.info(f"Total de páginas crawleadas: {len(self.pages_content)}")
        
        self.save_markdown()
        logging.info(f"Documentação salva em {self.output_file}")
        
        self.print_summary()

def main():
    parser = argparse.ArgumentParser(description="Crawler de documentação otimizado e com UX melhorada")
    parser.add_argument("--base-url", required=True, help="URL base da documentação")
    parser.add_argument("--output", default="output.md", help="Arquivo de saída")
    parser.add_argument("--workers", type=int, default=2, help="Número de threads (padrão: 2)")
    parser.add_argument("--cache-dir", default=".cache", help="Diretório para cache local")
    parser.add_argument("--max-pages", type=int, default=500, help="Número máximo de páginas")
    parser.add_argument("--min-content-length", type=int, default=100, help="Tamanho mínimo de conteúdo em caracteres (padrão: 100)")
    parser.add_argument("--clear-cache", action="store_true", help="Limpa o cache antes de iniciar")
    
    args = parser.parse_args()

    if args.clear_cache and os.path.exists(args.cache_dir):
        import shutil
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
