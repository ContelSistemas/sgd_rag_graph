import pytest
from src.ingestion.parser import MarkdownParser

def test_parse_content_with_frontmatter_and_links():
    content = """---
title: Documento de Prueba
category: Manuales
---
# Introducción
Este es un documento que referencia a [[Guia de Usuario]] y también a [[Procedimiento Técnico|Proceso]].
"""
    parser = MarkdownParser()
    result = parser.parse_content(content, source_path="test.md")

    assert result["source_path"] == "test.md"
    assert result["frontmatter"]["title"] == "Documento de Prueba"
    assert result["frontmatter"]["category"] == "Manuales"
    assert len(result["wiki_links"]) == 2
    assert result["wiki_links"][0] == {"target": "Guia de Usuario", "alias": "Guia de Usuario"}
    assert result["wiki_links"][1] == {"target": "Procedimiento Técnico", "alias": "Proceso"}
    assert "# Introducción" in result["content"]
