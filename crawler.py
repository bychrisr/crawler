#!/usr/bin/env python3
"""
Documentation Crawler v2.0.0
A robust, production-ready web crawler for documentation sites.

Author: Chris R
Repository: https://github.com/bychrisr/crawler
License: MIT
"""

import argparse
import os
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from tqdm import tqdm
import logging
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import gc
import re
import json
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple

__version__ = "2.0.1"

# Configuração de logging
logging.basicConfig(
    filename="crawler.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class CrawlerConfig:
    """Configurações centralizadas do crawler."""
    
    # User agent padrão
    USER_AGENT = f'DocumentationCrawler/{__version__} (+https://github.com/bychrisr/crawler)'
    
    # Timeouts e retries
    DEFAULT_TIMEOUT = 15
    DEFAULT_RETRIES = 3
    RETRY_BACKOFF = 2  # Exponential backoff multiplier
    
    # Rate limiting
    MIN_REQUEST_INTERVAL = 0.5  # Segundos entre requests
    
    # Patterns de exclusão (mais conservador)
    JUNK_URL_PATTERNS = re.compile(
        r'^(privacy-policy|terms-of-service|cookie-policy|legal|license)$',
        re.IGNORECASE
    )
    
    # Extensões de arquivo a ignorar
    IGNORED_EXTENSIONS = {'.pdf', '.zip', '.tar', '.gz', '.exe', '.dmg', '.jpg', '.png', '.gif', '.svg'}
    
    @staticmethod
    def calculate_expected_ratio(stats: Dict) -> float:
        """
        Calcula ratio mínimo esperado de conversão HTML→Markdown baseado no conteúdo.
        
        Sites modernos (React/Next/Vue) têm muito HTML estrutural (CSS inline, JS, metadados),
        resultando em ratios muito baixos (~1%). Esta função adapta o threshold dinamicamente.
        """
        fetched = max(stats.get('fetched', 1), 1)
        code_blocks = stats.get('code_blocks', 0)
        
        # Calcula densidade de código (code blocks por página)
        code_density = code_blocks / fetched
        
        # Sites de documentação técnica (muito código inline)
        if code_density > 2:  # >2 code blocks por página
            return 0.01  # 1% - sites com muito código têm muito HTML de highlighting
        
        # Sites pequenos podem ser mais densos
        if fetched < 20:
            return 0.03  # 3% - amostras pequenas podem ter mais variação
        
        # Sites modernos padrão (React/Next/Vue com SSR)
        return 0.015  # 1.5% - padrão realista para sites modernos


class UXEnhancedCrawler:
    """Crawler robusto e otimizado para documentações."""
    
    def __init__(
        self,
        base_url: str,
        output_file: str = "output.md",
        max_workers: int = 2,
        cache_dir: str = ".cache",
        max_pages: int = 1000,
        min_content_length: int = 100,
        respect_robots: bool = True,
        auth: Optional[Tuple[str, str]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        debug: bool = False
    ):
        self.base_url = base_url
        self.output_file = output_file
        self.max_workers = max_workers
        self.cache_dir = cache_dir
        self.max_pages = max_pages
        self.min_content_length = min_content_length
        self.respect_robots = respect_robots
        self.auth = auth
        self.custom_headers = custom_headers or {}
        self.debug = debug
        
        # Estado interno
        self.visited_urls: Set[str] = set()
        self.pages_content: Dict[str, str] = {}
        self.url_queue: List[str] = []
        self.lock = threading.Lock()
        self.last_request_time = 0
        
        # Estatísticas detalhadas
        self.stats = {
            'fetched': 0,
            'failed': 0,
            'too_small': 0,
            'filtered': 0,
            'total_chars': 0,
            'total_words': 0,
            'links_found': 0,
            'links_skipped_external': 0,
            'links_skipped_duplicate': 0,
            'retries_performed': 0,
            'cache_hits': 0,
            'validation_warnings': [],
            'robots_blocked': 0,
            'code_blocks': 0,  # Novo: contador de code blocks
            'empty_pages_skipped': 0  # Novo: páginas vazias puladas no TOC
        }
        
        # Extrai domínio base e scheme
        parsed_base = urlparse(self.base_url)
        self.base_domain = parsed_base.netloc
        self.base_scheme = parsed_base.scheme
        
        # Setup robots.txt
        self.robots_parser = None
        if self.respect_robots:
            self._setup_robots_parser()
        
        # Cria diretório de cache
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Salva metadados da execução
        self.metadata = {
            'version': __version__,
            'base_url': self.base_url,
            'started_at': datetime.now().isoformat(),
            'config': {
                'max_workers': max_workers,
                'max_pages': max_pages,
                'min_content_length': min_content_length,
                'respect_robots': respect_robots
            }
        }
        
        logging.info(f"Crawler v{__version__} inicializado - Base domain: {self.base_domain}")

    def _setup_robots_parser(self):
        """Configura parser de robots.txt."""
        try:
            robots_url = f"{self.base_scheme}://{self.base_domain}/robots.txt"
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            logging.info(f"robots.txt carregado de {robots_url}")
        except Exception as e:
            logging.warning(f"Não foi possível carregar robots.txt: {e}")
            self.robots_parser = None

    def _can_fetch(self, url: str) -> bool:
        """Verifica se a URL pode ser crawleada segundo robots.txt."""
        if not self.respect_robots or not self.robots_parser:
            return True
        
        can_fetch = self.robots_parser.can_fetch(CrawlerConfig.USER_AGENT, url)
        if not can_fetch:
            logging.info(f"Bloqueado por robots.txt: {url}")
            with self.lock:
                self.stats['robots_blocked'] += 1
        
        return can_fetch

    def _rate_limit(self):
        """Aplica rate limiting entre requests."""
        with self.lock:
            elapsed = time.time() - self.last_request_time
            if elapsed < CrawlerConfig.MIN_REQUEST_INTERVAL:
                time.sleep(CrawlerConfig.MIN_REQUEST_INTERVAL - elapsed)
            self.last_request_time = time.time()

    def _normalize_url(self, url: str) -> str:
        """Normaliza URL removendo fragmentos e garantindo trailing slash consistente."""
        parsed = urlparse(url)
        clean_path = parsed.path
        
        if not clean_path.endswith('/') and '.' not in clean_path.split('/')[-1]:
            clean_path = clean_path + '/'
        
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            clean_path,
            '', '', ''
        ))
        
        return normalized

    def _get_cache_path(self, url: str) -> str:
        """Retorna o caminho do arquivo de cache para uma URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{url_hash}.html")

    def _should_skip_url(self, url: str) -> bool:
        """Verifica se a URL deve ser ignorada."""
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        if any(path.endswith(ext) for ext in CrawlerConfig.IGNORED_EXTENSIONS):
            return True
        
        return False

    def fetch(self, url: str, retries: Optional[int] = None, timeout: Optional[int] = None) -> Optional[str]:
        """Faz o download de uma URL com retry automático e rate limiting."""
        if retries is None:
            retries = CrawlerConfig.DEFAULT_RETRIES
        if timeout is None:
            timeout = CrawlerConfig.DEFAULT_TIMEOUT
        
        if not self._can_fetch(url):
            return None
        
        cache_path = self._get_cache_path(url)
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    logging.info(f"Cache hit: {url}")
                    with self.lock:
                        self.stats['cache_hits'] += 1
                    return f.read()
            except Exception as e:
                logging.warning(f"Erro ao ler cache de {url}: {e}")

        headers = {
            'User-Agent': CrawlerConfig.USER_AGENT,
            **self.custom_headers
        }

        for attempt in range(retries):
            try:
                self._rate_limit()
                logging.info(f"Fetching ({attempt+1}/{retries}): {url}")
                
                kwargs = {'timeout': timeout, 'headers': headers}
                if self.auth:
                    kwargs['auth'] = self.auth
                
                response = requests.get(url, **kwargs)
                
                if response.status_code == 200:
                    with open(cache_path, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    logging.info(f"Success: {url}")
                    return response.text
                else:
                    logging.warning(f"HTTP {response.status_code} em {url}")
                    
            except requests.exceptions.Timeout:
                logging.error(f"Timeout ao acessar {url} (tentativa {attempt+1})")
                with self.lock:
                    self.stats['retries_performed'] += 1
            except requests.exceptions.RequestException as e:
                logging.error(f"Erro ao acessar {url} (tentativa {attempt+1}): {e}")
                with self.lock:
                    self.stats['retries_performed'] += 1
            
            if attempt < retries - 1:
                sleep_time = CrawlerConfig.RETRY_BACKOFF ** attempt
                logging.info(f"Aguardando {sleep_time}s antes de retry...")
                time.sleep(sleep_time)
        
        logging.error(f"Failed após {retries} tentativas: {url}")
        return None

    def _extract_links(self, current_url: str, html: str) -> List[str]:
        """Extrai links do HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = set()
        links_found_raw = 0
        
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            links_found_raw += 1
            
            if href.startswith('#') or href.startswith('javascript:') or href.startswith('mailto:'):
                continue
            
            full_url = urljoin(current_url, href)
            parsed = urlparse(full_url)
            
            if parsed.netloc != self.base_domain:
                with self.lock:
                    self.stats['links_skipped_external'] += 1
                continue
            
            if self._should_skip_url(full_url):
                continue
            
            normalized = self._normalize_url(full_url)
            
            if normalized in self.visited_urls:
                with self.lock:
                    self.stats['links_skipped_duplicate'] += 1
                continue
            
            path_parts = parsed.path.strip('/').split('/')
            if any(CrawlerConfig.JUNK_URL_PATTERNS.match(part) for part in path_parts):
                with self.lock:
                    self.stats['filtered'] += 1
                logging.info(f"Filtrado (junk pattern): {normalized}")
                continue
            
            links.add(normalized)
        
        with self.lock:
            self.stats['links_found'] += len(links)
        
        logging.info(f"Links encontrados em {current_url}: {links_found_raw} raw → {len(links)} válidos")
        return list(links)

    def _is_junk_page(self, url: str, title: str, content: str) -> bool:
        """Detecta se a página é lixo."""
        title_lower = title.lower() if title else ""
        path = urlparse(url).path.strip('/').split('/')
        
        for part in path:
            if CrawlerConfig.JUNK_URL_PATTERNS.match(part):
                return True
        
        if CrawlerConfig.JUNK_URL_PATTERNS.search(title_lower):
            return True
        
        return False

    def crawl(self):
        """Executa o crawling principal."""
        initial_normalized = self._normalize_url(self.base_url)
        self.visited_urls.add(initial_normalized)
        self.url_queue = [self.base_url]
        
        processed_count = 0
        
        print(f"\n{'='*70}")
        print(f"🔍 Documentation Crawler v{__version__}")
        print(f"{'='*70}")
        print(f"🌐 Base URL: {self.base_url}")
        print(f"🌐 Domínio: {self.base_domain}")
        print(f"📦 Limite de páginas: {self.max_pages}")
        print(f"⚡ Workers: {self.max_workers}")
        print(f"💾 Cache: {self.cache_dir}")
        print(f"📏 Filtro de conteúdo: min. {self.min_content_length} chars")
        print(f"🤖 Respeita robots.txt: {self.respect_robots}")
        print(f"{'='*70}\n")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
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
                                soup = BeautifulSoup(html, "html.parser")
                                
                                title_tag = soup.find("h1")
                                title = title_tag.get_text().strip() if title_tag else urlparse(url).path.split('/')[-1]
                                
                                if self._is_junk_page(url, title, html):
                                    with self.lock:
                                        self.stats['filtered'] += 1
                                    logging.info(f"Página filtrada (junk): {url}")
                                    continue
                                
                                content_text = soup.get_text(strip=True)
                                if len(content_text) < self.min_content_length:
                                    with self.lock:
                                        self.stats['too_small'] += 1
                                    logging.info(f"Página muito pequena ({len(content_text)} chars): {url}")
                                    continue
                                
                                with self.lock:
                                    self.pages_content[url] = html
                                    self.stats['fetched'] += 1
                                    self.stats['total_chars'] += len(html)
                                    self.stats['total_words'] += len(content_text.split())
                                    processed_count += 1
                                    pbar.update(1)
                                
                                logging.info(f"Página processada ({processed_count}/{self.max_pages}): {url}")
                                
                                new_links = self._extract_links(url, html)
                                
                                with self.lock:
                                    for link in new_links:
                                        if len(self.visited_urls) < self.max_pages:
                                            self.visited_urls.add(link)
                                            self.url_queue.append(link)
                                
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
                        
                        if processed_count % 50 == 0:
                            gc.collect()
                        
                        if processed_count >= self.max_pages:
                            break

    def _detect_code_language(self, code: str) -> str:
        """
        Detecta a linguagem de um bloco de código via heurística.
        
        Args:
            code: Conteúdo do bloco de código
            
        Returns:
            String com a linguagem detectada ('javascript', 'python', etc.) ou 'text'
        """
        code_lower = code.lower()
        
        # JavaScript/TypeScript
        if any(keyword in code for keyword in ['import ', 'export ', 'const ', 'let ', 'var ', '=>']):
            if 'tsx' in code_lower or '<' in code and '>' in code:
                return 'tsx'
            if 'typescript' in code_lower or ': string' in code or ': number' in code:
                return 'typescript'
            return 'javascript'
        
        # React/JSX
        if '<' in code and '>' in code and any(x in code for x in ['className', 'onClick', 'useState', 'useEffect']):
            return 'jsx'
        
        # Python
        if any(keyword in code for keyword in ['def ', 'import ', 'from ', 'class ', 'self.', '__init__']):
            return 'python'
        
        # Bash/Shell
        if code.startswith('#!') or any(keyword in code for keyword in ['#!/bin/', 'npm ', 'pip ', 'git ']):
            return 'bash'
        
        # JSON
        if code.strip().startswith('{') or code.strip().startswith('['):
            try:
                import json
                json.loads(code)
                return 'json'
            except:
                pass
        
        # CSS
        if '{' in code and '}' in code and ':' in code and any(x in code_lower for x in ['color', 'margin', 'padding', 'display']):
            return 'css'
        
        # HTML
        if '<!DOCTYPE' in code or '<html' in code_lower:
            return 'html'
        
        # Markdown
        if code.startswith('#') or '```' in code:
            return 'markdown'
        
        # Fallback
        return 'text'

    def _html_to_markdown(self, html: str, url: str) -> str:
        """Converte HTML para Markdown com fallback robusto."""
        soup = BeautifulSoup(html, "html.parser")
        
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        
        content = []
        code_blocks_count = 0
        
        # Título principal
        h1 = soup.find("h1")
        if h1:
            content.append(f"# {h1.get_text().strip()}\n")
        else:
            # Usa path da URL como fallback
            path_title = urlparse(url).path.replace('/', ' ').strip()
            if path_title:
                content.append(f"# {path_title}\n")

        # Estratégia de fallback para encontrar conteúdo principal
        main = soup.find("main") or soup.find("article") or soup.find(class_=re.compile(r'content|main|body', re.I))
        
        if main:
            has_content = main.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'pre'], limit=3)
            if not has_content:
                if self.debug:
                    print(f"  [DEBUG] Main vazio em {url}, usando body como fallback")
                logging.warning(f"Main vazio em {url}, usando body como fallback")
                main = soup.body
        else:
            main = soup.body or soup
        
        if main and main.name == 'body':
            for tag in main.find_all(['nav', 'header', 'footer', 'aside']):
                tag.decompose()
        
        # Contadores para debug
        p_count = h_count = li_count = 0
        
        # Extrai conteúdo
        for element in main.find_all():
            if element.name in ["h2", "h3", "h4", "h5", "h6"]:
                level = int(element.name[1])
                text = element.get_text().strip()
                if text:
                    content.append(f"{'#' * level} {text}\n")
                    h_count += 1
            elif element.name == "p":
                text = element.get_text().strip()
                if text:
                    content.append(text + "\n")
                    p_count += 1
            elif element.name in ["ul", "ol"]:
                for li in element.find_all("li", recursive=False):
                    li_text = li.get_text().strip()
                    if li_text:
                        content.append(f"- {li_text}\n")
                        li_count += 1
            elif element.name == "pre":
                code_text = element.get_text()
                lang = "text"
                
                # Tenta pegar linguagem da classe
                if element.find("code"):
                    code_class = element.find("code").get("class", [])
                    for cls in code_class:
                        if cls.startswith("language-"):
                            lang = cls.split("-", 1)[1]
                            break
                
                # Se não encontrou, detecta via heurística
                if lang == "text":
                    lang = self._detect_code_language(code_text)
                
                content.append(f"```{lang}\n{code_text}\n```\n")
                code_blocks_count += 1
            elif element.name == "code" and not element.find_parent("pre"):
                content.append(f"`{element.get_text()}`")
            elif element.name == "blockquote":
                quote_text = element.get_text().strip()
                if quote_text:
                    content.append(f"> {quote_text}\n")
        
        # Atualiza estatísticas de code blocks
        with self.lock:
            self.stats['code_blocks'] += code_blocks_count
        
        # Debug output
        if self.debug:
            print(f"  [DEBUG] Extraído de {url}:")
            print(f"    - {h_count} headers")
            print(f"    - {p_count} parágrafos")
            print(f"    - {li_count} items de lista")
            print(f"    - {code_blocks_count} code blocks")

        return "\n".join(content).strip()

    def validate_output(self) -> Dict[str, any]:
        """Valida a qualidade do output gerado com thresholds adaptativos."""
        validation = {
            'success': True,
            'warnings': [],
            'errors': []
        }
        
        if not os.path.exists(self.output_file):
            validation['success'] = False
            validation['errors'].append("Arquivo de output não foi criado")
            return validation
        
        file_size = os.path.getsize(self.output_file)
        
        # Valida tamanho do arquivo (500 bytes por página é mínimo aceitável)
        expected_min_size = self.stats['fetched'] * 500
        
        if file_size < expected_min_size:
            validation['warnings'].append(
                f"Arquivo menor que esperado: {file_size:,} bytes "
                f"(esperado: ~{expected_min_size:,} bytes para {self.stats['fetched']} páginas)"
            )
        
        # Valida ratio de conteúdo com threshold ADAPTATIVO
        if self.stats['total_chars'] > 0:
            content_ratio = file_size / self.stats['total_chars']
            
            # Calcula threshold esperado dinamicamente
            expected_ratio = CrawlerConfig.calculate_expected_ratio(self.stats)
            
            if content_ratio < expected_ratio:
                # Calcula densidade de código para mensagem mais útil
                code_density = self.stats.get('code_blocks', 0) / max(self.stats['fetched'], 1)
                
                msg = (
                    f"Conversão HTML→Markdown abaixo do esperado: {content_ratio:.1%} "
                    f"(esperado: >{expected_ratio:.1%} para este tipo de site)"
                )
                
                # Adiciona contexto se for site de documentação técnica
                if code_density > 2:
                    msg += f" [Site de docs técnicas: {code_density:.1f} code blocks/página]"
                
                validation['warnings'].append(msg)
        
        # Valida número de páginas
        if self.stats['fetched'] < 5:
            validation['warnings'].append(
                f"Poucas páginas crawleadas: {self.stats['fetched']} "
                f"(pode indicar problema na extração de links ou bloqueio)"
            )
        
        # Valida failures
        total_attempts = self.stats['fetched'] + self.stats['failed']
        if total_attempts > 0:
            failure_rate = self.stats['failed'] / total_attempts
            if failure_rate > 0.2:  # >20% de falhas
                validation['warnings'].append(
                    f"Alta taxa de falhas: {failure_rate:.1%} "
                    f"({self.stats['failed']}/{total_attempts} páginas)"
                )
        
        self.stats['validation_warnings'] = validation['warnings']
        return validation

    def save_markdown(self):
        """Salva a documentação em formato Markdown."""
        print(f"\n💾 Salvando documentação em {self.output_file}...")
        
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(f"# Documentação: {self.base_url}\n\n")
            f.write(f"*Gerado automaticamente por Documentation Crawler v{__version__}*\n")
            f.write(f"*Data: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            
            f.write("## Metadados da Execução\n\n")
            f.write(f"- **Total de páginas**: {self.stats['fetched']}\n")
            f.write(f"- **Páginas falhas**: {self.stats['failed']}\n")
            f.write(f"- **Cache hits**: {self.stats['cache_hits']}\n")
            f.write(f"- **Links encontrados**: {self.stats['links_found']}\n")
            f.write(f"- **Code blocks extraídos**: {self.stats['code_blocks']}\n\n")
            
            # Gera TOC (pulando páginas vazias)
            f.write("## Table of Contents\n\n")
            empty_pages_skipped = 0
            
            for url in sorted(self.pages_content.keys()):
                html = self.pages_content[url]
                soup = BeautifulSoup(html, "html.parser")
                h1 = soup.find("h1")
                title = h1.get_text().strip() if h1 else ""
                
                # Skip páginas sem título (root vazias)
                if not title or len(title.strip()) == 0:
                    # Tenta usar path como fallback
                    path_title = urlparse(url).path.strip('/').replace('/', ' ').strip()
                    if not path_title:
                        empty_pages_skipped += 1
                        if self.debug:
                            print(f"  [DEBUG] Pulando página vazia no TOC: {url}")
                        continue
                    title = path_title
                
                anchor = re.sub(r'[^\w\s-]', '', title.lower()).replace(" ", "-")
                f.write(f"- [{title}](#{anchor})\n")
            
            self.stats['empty_pages_skipped'] = empty_pages_skipped
            
            f.write("\n---\n\n")
            
            # Conteúdo
            for url in sorted(self.pages_content.keys()):
                html = self.pages_content[url]
                markdown_content = self._html_to_markdown(html, url)
                f.write(markdown_content + "\n\n")
                f.write(f"*Fonte: [{url}]({url})*\n\n")
                f.write("---\n\n")
        
        logging.info(f"Documentação salva: {self.output_file}")
        
        if empty_pages_skipped > 0 and self.debug:
            print(f"  [DEBUG] {empty_pages_skipped} páginas vazias puladas no TOC")

    def save_metadata(self):
        """Salva metadados da execução em JSON."""
        metadata_file = self.output_file.replace('.md', '.metadata.json')
        
        self.metadata['finished_at'] = datetime.now().isoformat()
        self.metadata['stats'] = self.stats
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Metadados salvos: {metadata_file}")

    def print_summary(self):
        """Imprime um resumo detalhado das estatísticas."""
        print("\n" + "="*70)
        print("📊 RESUMO DO CRAWLING")
        print("="*70)
        print(f"✅ Páginas Crawleadas: {self.stats['fetched']}")
        print(f"❌ Páginas Falhas: {self.stats['failed']}")
        print(f"🗑️  Páginas Filtradas (junk): {self.stats['filtered']}")
        print(f"📏 Páginas Muito Pequenas: {self.stats['too_small']}")
        print(f"🤖 Bloqueadas por robots.txt: {self.stats['robots_blocked']}")
        print(f"\n🔗 Links Encontrados: {self.stats['links_found']}")
        print(f"🌐 Links Externos (ignorados): {self.stats['links_skipped_external']}")
        print(f"♻️  Links Duplicados (ignorados): {self.stats['links_skipped_duplicate']}")
        print(f"\n💾 Cache Hits: {self.stats['cache_hits']}")
        print(f"🔄 Retries Realizados: {self.stats['retries_performed']}")
        print(f"\n📝 Total de Caracteres: {self.stats['total_chars']:,}")
        print(f"📖 Total de Palavras: {self.stats['total_words']:,}")
        print(f"📦 Code Blocks Extraídos: {self.stats['code_blocks']}")
        
        if self.stats['empty_pages_skipped'] > 0:
            print(f"⚠️  Páginas Vazias (puladas no TOC): {self.stats['empty_pages_skipped']}")
        
        if os.path.exists(self.output_file):
            file_size = os.path.getsize(self.output_file)
            print(f"💾 Tamanho do Arquivo: {file_size:,} bytes ({file_size/1024:.2f} KB)")
        
        elapsed = time.time() - self.start_time
        print(f"⏱️  Tempo Total: {time.strftime('%H:%M:%S', time.gmtime(elapsed))}")
        
        print("\n" + "="*70)
        print("🔍 VALIDAÇÃO DE QUALIDADE")
        print("="*70)
        
        validation = self.validate_output()
        
        if validation['success'] and not validation['warnings']:
            print("✅ Output validado com sucesso! Nenhum problema detectado.")
        else:
            if validation['warnings']:
                print("⚠️  AVISOS:")
                for warning in validation['warnings']:
                    print(f"   - {warning}")
            if validation['errors']:
                print("❌ ERROS:")
                for error in validation['errors']:
                    print(f"   - {error}")
        
        print("\n" + "="*70)
        print(f"📄 Logs detalhados salvos em: crawler.log")
        print(f"📊 Metadados salvos em: {self.output_file.replace('.md', '.metadata.json')}")
        print("="*70)

    def run(self):
        """Executa o crawler completo."""
        self.start_time = time.time()
        logging.info(f"="*70)
        logging.info(f"Iniciando Documentation Crawler v{__version__}")
        logging.info(f"Base URL: {self.base_url}")
        logging.info(f"Domínio base: {self.base_domain}")
        logging.info(f"="*70)
        
        try:
            self.crawl()
            logging.info(f"Total de páginas crawleadas: {len(self.pages_content)}")
            
            self.save_markdown()
            self.save_metadata()
            
            self.print_summary()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Crawling interrompido pelo usuário!")
            print(f"📊 Progresso até agora: {self.stats['fetched']} páginas crawleadas")
            
            if self.stats['fetched'] > 0:
                print("💾 Salvando progresso parcial...")
                self.save_markdown()
                self.save_metadata()
                print("✅ Progresso salvo!")
            
            sys.exit(1)
        
        except Exception as e:
            logging.error(f"Erro fatal durante execução: {e}", exc_info=True)
            print(f"\n❌ Erro fatal: {e}")
            print(f"📄 Verifique crawler.log para detalhes")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description=f"Documentation Crawler v{__version__} - Crawler robusto para documentações",
        epilog="Exemplo: python3 crawler.py --base-url https://docs.exemplo.com/",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--base-url", required=True, help="URL base da documentação")
    parser.add_argument("--output", default="output.md", help="Arquivo de saída (padrão: output.md)")
    parser.add_argument("--workers", type=int, default=2, help="Número de threads (padrão: 2)")
    parser.add_argument("--cache-dir", default=".cache", help="Diretório para cache local (padrão: .cache)")
    parser.add_argument("--max-pages", type=int, default=500, help="Número máximo de páginas (padrão: 500)")
    parser.add_argument("--min-content-length", type=int, default=100, 
                       help="Tamanho mínimo de conteúdo em caracteres (padrão: 100)")
    
    parser.add_argument("--clear-cache", action="store_true", help="Limpa o cache antes de iniciar")
    parser.add_argument("--no-robots", action="store_true", help="Ignora robots.txt (use com cuidado!)")
    parser.add_argument("--debug", action="store_true", help="Mostra extração de conteúdo em tempo real")
    parser.add_argument("--version", action="version", version=f"Documentation Crawler v{__version__}")
    
    parser.add_argument("--auth-user", help="Usuário para autenticação HTTP básica")
    parser.add_argument("--auth-pass", help="Senha para autenticação HTTP básica")
    
    parser.add_argument("--header", action="append", 
                       help="Header HTTP customizado (formato: 'Nome: Valor'). Pode ser usado múltiplas vezes")
    
    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"Documentation Crawler v{__version__}")
    print(f"{'='*70}\n")

    if args.clear_cache and os.path.exists(args.cache_dir):
        import shutil
        print(f"🗑️  Limpando cache em {args.cache_dir}...")
        shutil.rmtree(args.cache_dir)
        os.makedirs(args.cache_dir, exist_ok=True)
    
    auth = None
    if args.auth_user and args.auth_pass:
        auth = (args.auth_user, args.auth_pass)
        print(f"🔐 Autenticação HTTP básica ativada para usuário: {args.auth_user}")
    
    custom_headers = {}
    if args.header:
        for header in args.header:
            if ':' not in header:
                print(f"⚠️  Header inválido ignorado: {header}")
                continue
            name, value = header.split(':', 1)
            custom_headers[name.strip()] = value.strip()
        print(f"📋 Headers customizados: {len(custom_headers)}")
    
    if args.debug:
        print(f"🐛 Modo DEBUG ativado - mostrando extração em tempo real\n")

    crawler = UXEnhancedCrawler(
        base_url=args.base_url,
        output_file=args.output,
        max_workers=args.workers,
        cache_dir=args.cache_dir,
        max_pages=args.max_pages,
        min_content_length=args.min_content_length,
        respect_robots=not args.no_robots,
        auth=auth,
        custom_headers=custom_headers,
        debug=args.debug
    )
    crawler.run()


if __name__ == "__main__":
    main()
