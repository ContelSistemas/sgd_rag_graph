import re
from pathlib import Path
from typing import Dict, Any, List
import yaml

class MarkdownParser:
    """Parser para documentos Markdown del SGD. Extrae frontmatter YAML, enlaces wiki [[enlace]] y contenido."""
    
    WIKI_LINK_REGEX = re.compile(r'\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]')

    def parse_file(self, file_path: str | Path) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"El archivo {path} no existe.")
            
        content = path.read_text(encoding='utf-8')
        return self.parse_content(content, source_path=str(path))

    def parse_content(self, content: str, source_path: str = "") -> Dict[str, Any]:
        frontmatter = {}
        body = content

        # Extraer YAML Frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    frontmatter = {}
                body = parts[2]

        # Extraer enlaces wiki [[enlace]]
        wiki_links = []
        for match in self.WIKI_LINK_REGEX.finditer(content):
            target = match.group(1).strip()
            alias = match.group(2).strip() if match.group(2) else target
            wiki_links.append({"target": target, "alias": alias})

        return {
            "source_path": source_path,
            "frontmatter": frontmatter,
            "content": body.strip(),
            "wiki_links": wiki_links
        }
