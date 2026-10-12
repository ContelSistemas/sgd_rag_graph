import pytest
from src.ingestion.chunker import HierarchicalMarkdownChunker

def test_chunker_hierarchical():
    content = """---
title: Test Doc
---
Intro text here.

# Section 1
Content of section 1.

## Subsection 1.1
Content of subsection 1.1.
"""
    parsed = {
        "source_path": "test.md",
        "frontmatter": {"title": "Test Doc"},
        "content": content,
        "wiki_links": []
    }

    chunker = HierarchicalMarkdownChunker()
    chunks = chunker.chunk_document(parsed)

    assert len(chunks) >= 3
    assert any("Intro" in c["header_path"] for c in chunks)
    assert any("Section 1" in c["header_path"] for c in chunks)
    assert any("Subsection 1.1" in c["header_path"] for c in chunks)
