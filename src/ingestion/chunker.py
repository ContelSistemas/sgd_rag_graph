import re
from typing import List, Dict, Any

class HierarchicalMarkdownChunker:
    """Fragmentador de documentos Markdown respetando la jerarquía de encabezados (#, ##, ###)."""

    HEADING_REGEX = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    def chunk_document(self, parsed_doc: Dict[str, Any], max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        content = parsed_doc.get("content", "")
        source_path = parsed_doc.get("source_path", "")
        frontmatter = parsed_doc.get("frontmatter", {})
        wiki_links = parsed_doc.get("wiki_links", [])

        matches = list(self.HEADING_REGEX.finditer(content))
        
        if not matches:
            return [{
                "chunk_id": f"{source_path}#chunk-0",
                "source_path": source_path,
                "header_path": frontmatter.get("title", source_path),
                "content": content,
                "frontmatter": frontmatter,
                "wiki_links": wiki_links
            }]

        chunks = []
        intro_text = content[:matches[0].start()].strip()
        if intro_text:
            chunks.append({
                "chunk_id": f"{source_path}#intro",
                "source_path": source_path,
                "header_path": f"{frontmatter.get('title', source_path)} > Introduction",
                "content": intro_text,
                "frontmatter": frontmatter,
                "wiki_links": wiki_links
            })

        for i, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            chunk_content = content[start_pos:end_pos].strip()
            
            chunks.append({
                "chunk_id": f"{source_path}#heading-{i}-{title.lower().replace(' ', '-')}",
                "source_path": source_path,
                "header_path": f"{frontmatter.get('title', source_path)} > {title}",
                "content": chunk_content,
                "frontmatter": frontmatter,
                "wiki_links": wiki_links
            })

        return chunks
