#!/bin/bash
# Exemplos de uso do Documentation Crawler v2.0.0
# Este script contém casos de uso comuns para referência

echo "Documentation Crawler - Exemplos de Uso"
echo "========================================"
echo ""

# Exemplo 1: Uso básico
echo "1. Uso básico (default settings)"
echo "   python3 crawler.py --base-url https://docs.exemplo.com/"
echo ""

# Exemplo 2: Documentação com mais páginas
echo "2. Documentação grande (1000 páginas, 5 workers)"
echo "   python3 crawler.py \\"
echo "     --base-url https://vuejs.org/guide/ \\"
echo "     --output vue-docs.md \\"
echo "     --max-pages 1000 \\"
echo "     --workers 5"
echo ""

# Exemplo 3: Com autenticação
echo "3. Site com autenticação HTTP Basic"
echo "   python3 crawler.py \\"
echo "     --base-url https://docs-privadas.com/ \\"
echo "     --auth-user usuario \\"
echo "     --auth-pass senha123 \\"
echo "     --output docs-privadas.md"
echo ""

# Exemplo 4: Com headers customizados
echo "4. API docs com headers customizados"
echo "   python3 crawler.py \\"
echo "     --base-url https://api-docs.com/ \\"
echo "     --header \"Authorization: Bearer TOKEN123\" \\"
echo "     --header \"X-Custom-Header: value\" \\"
echo "     --output api-docs.md"
echo ""

# Exemplo 5: Limpar cache
echo "5. Limpar cache antes de rodar"
echo "   python3 crawler.py \\"
echo "     --base-url https://docs.exemplo.com/ \\"
echo "     --clear-cache"
echo ""

# Exemplo 6: Ignorar robots.txt (use com cuidado!)
echo "6. Ignorar robots.txt (use com responsabilidade)"
echo "   python3 crawler.py \\"
echo "     --base-url https://site.com/ \\"
echo "     --no-robots \\"
echo "     --output site-docs.md"
echo ""

# Exemplo 7: Filtro de conteúdo mais rigoroso
echo "7. Filtro de conteúdo mais rigoroso (min 500 chars)"
echo "   python3 crawler.py \\"
echo "     --base-url https://docs.exemplo.com/ \\"
echo "     --min-content-length 500"
echo ""

# Exemplo 8: Teste rápido (poucas páginas)
echo "8. Teste rápido (máx 10 páginas)"
echo "   python3 crawler.py \\"
echo "     --base-url https://docs.exemplo.com/ \\"
echo "     --max-pages 10 \\"
echo "     --output test.md"
echo ""

# Exemplo 9: Re-executar usando cache
echo "9. Re-executar usando cache (rápido)"
echo "   python3 crawler.py \\"
echo "     --base-url https://docs.exemplo.com/ \\"
echo "     --output docs-v2.md"
echo "   # Nota: Não usa --clear-cache, então reutiliza cache existente"
echo ""

# Exemplo 10: Sites reais conhecidos
echo "10. Exemplos com sites reais"
echo ""
echo "    Minimals UI:"
echo "    python3 crawler.py --base-url https://docs.minimals.cc/ --max-pages 50"
echo ""
echo "    Nextra:"
echo "    python3 crawler.py --base-url https://nextra.site/docs --max-pages 100"
echo ""
echo "    TradingView Lightweight Charts:"
echo "    python3 crawler.py --base-url https://tradingview.github.io/lightweight-charts/docs --max-pages 200"
echo ""

echo "========================================"
echo "Para mais informações, veja: README.md"
echo "========================================"
