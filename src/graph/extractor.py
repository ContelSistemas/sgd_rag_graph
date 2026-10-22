# src/graph/extractor.py
"""Extracción estructurada de entidades y relaciones desde texto usando LLM local."""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

import httpx
from pydantic import BaseModel, Field

from src.config.settings import get_settings


class Entity(BaseModel):
    """Entidad extraída del texto."""
    name: str = Field(..., description="Nombre canónico de la entidad")
    type: str = Field(..., description="Tipo: equipo, IP, VLAN, cliente, sistema, ubicación, servicio, etc.")
    description: Optional[str] = Field(None, description="Descripción breve")
    chunk_id: Optional[str] = Field(None, description="ID del chunk de origen")
    source_path: Optional[str] = Field(None, description="Ruta del archivo fuente")


class Relation(BaseModel):
    """Relación dirigida entre dos entidades."""
    source: str = Field(..., description="Nombre de la entidad origen")
    target: str = Field(..., description="Nombre de la entidad destino")
    type: str = Field(..., description="Tipo de relación: conecta_a, pertenece_a, usa, bloquea, gestiona, etc.")
    description: Optional[str] = Field(None, description="Descripción breve de la relación")
    chunk_id: Optional[str] = Field(None, description="ID del chunk de origen")


class ExtractionResult(BaseModel):
    """Resultado estructurado de la extracción."""
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)


def normalize_name(name: str) -> str:
    """Normaliza un nombre de entidad para resolución de duplicados."""
    n = name.strip().lower()
    n = unicodedata.normalize("NFKD", n)
    n = "".join(c for c in n if not unicodedata.combining(c))  # quita tildes
    n = re.sub(r"\s+", " ", n)  # colapsa espacios múltiples
    return n


class LLMExtractor:
    """Extrae entidades y relaciones desde texto usando un LLM local con salida JSON forzada."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.extraction_model or settings.llm_model_name
        self.timeout = timeout or settings.llm_timeout
        self.temperature = temperature or settings.extraction_temperature
        self.max_tokens = max_tokens or settings.extraction_max_tokens

    # ------------------------------------------------------------------ #
    # Prompt
    # ------------------------------------------------------------------ #
    def _build_prompt(
        self,
        text: str,
        chunk_id: str,
        source_path: str,
        frontmatter: Optional[Dict[str, Any]] = None,
    ) -> str:
        ctx = ""
        if frontmatter:
            ctx = "\n# Metadatos del documento (frontmatter):\n"
            for k, v in frontmatter.items():
                ctx += f"- {k}: {v}\n"

        return f"""Eres un asistente experto en extracción de información para un grafo de conocimiento de redes e infraestructura TI.

Tu tarea es leer el siguiente fragmento de texto y extraer:
1. Entidades relevantes (equipos, IPs, VLANs, clientes, sistemas, servicios, ubicaciones, etc.)
2. Relaciones dirigidas entre esas entidades.

{ctx}

# Fragmento de texto:
{text}

# Reglas:
- Extrae solo entidades y relaciones que estén explícitamente mencionadas en el texto.
- Usa nombres canónicos y consistentes (ej: "OLT 10.104.8.10", no "la OLT").
- Tipos de entidad sugeridos: equipo, ip, vlan, cliente, sistema, servicio, ubicacion, protocolo, puerto.
- Tipos de relación sugeridos: conecta_a, pertenece_a, usa, bloquea, gestiona, tiene_ip, tiene_vlan, ubicado_en.
- Cada entidad y relación debe incluir el chunk_id de origen: "{chunk_id}".
- Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después.
- El JSON debe tener exactamente estas claves: "entities" (lista) y "relations" (lista).
- Cada entidad: {{"name": "...", "type": "...", "description": "...", "chunk_id": "{chunk_id}", "source_path": "{source_path}"}}
- Cada relación: {{"source": "...", "target": "...", "type": "...", "description": "...", "chunk_id": "{chunk_id}"}}
- Los campos "source" y "target" de las relaciones deben coincidir exactamente con el "name" de entidades ya extraídas.

# JSON de salida:
{{"""

    # ------------------------------------------------------------------ #
    # Llamada al LLM
    # ------------------------------------------------------------------ #
    def _call_llm(self, prompt: str) -> str:
        """Llama a llama-server (o Ollama) forzando salida JSON."""
        is_ollama = "ollama" in self.base_url.lower() or "/api/generate" in self.base_url

        if is_ollama:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            }
            url = f"{self.base_url}/api/generate"
        else:
            # llama.cpp /completion
            payload = {
                "prompt": prompt,
                "format": "json",
                "temperature": self.temperature,
                "n_predict": self.max_tokens,
                "stream": False,
            }
            url = f"{self.base_url}/completion"

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        if is_ollama:
            return data.get("response", "")
        else:
            return data.get("content", "")

    # ------------------------------------------------------------------ #
    # Extracción principal
    # ------------------------------------------------------------------ #
    def extract(
        self,
        text: str,
        chunk_id: str,
        source_path: str,
        frontmatter: Optional[Dict[str, Any]] = None,
    ) -> ExtractionResult:
        prompt = self._build_prompt(text, chunk_id, source_path, frontmatter)
        raw = self._call_llm(prompt)

        # Limpieza por si el modelo envía markdown ```json ... ```
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            # Intento de rescate: buscar el primer {...}
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                except json.JSONDecodeError:
                    return ExtractionResult()
            else:
                return ExtractionResult()

        return ExtractionResult(**parsed)

    # ------------------------------------------------------------------ #
    # Resolución de entidades (normalización + fusión)
    # ------------------------------------------------------------------ #
    @staticmethod
    def resolve_entities(
        entities: List[Entity],
        similarity_threshold: float = 0.9,
    ) -> List[Entity]:
        """Fusiona entidades cuyo nombre normalizado sea idéntico o muy similar."""
        groups: Dict[str, Entity] = {}
        seen_keys: Set[str] = set()

        for ent in entities:
            key = normalize_name(ent.name)
            if key in seen_keys:
                # Fusionar descripción si existe y la existente no tiene
                existing = groups[key]
                if ent.description and not existing.description:
                    existing.description = ent.description
                continue
            seen_keys.add(key)
            groups[key] = ent

        return list(groups.values())

    @staticmethod
    def build_entity_index(entities: List[Entity]) -> Dict[str, str]:
        """Mapea nombre normalizado → nombre canónico."""
        return {normalize_name(e.name): e.name for e in entities}


# ------------------------------------------------------------------ #
# Integración con KnowledgeGraphManager
# ------------------------------------------------------------------ #
def populate_graph_from_extraction(
    kg_manager: Any,  # KnowledgeGraphManager
    extractor: LLMExtractor,
    text: str,
    chunk_id: str,
    source_path: str,
    frontmatter: Optional[Dict[str, Any]] = None,
    add_frontmatter_nodes: bool = False,
) -> ExtractionResult:
    """
    Extrae entidades y relaciones del texto y las inserta en el grafo.

    Por defecto NO crea nodos de frontmatter para evitar duplicados con
    lo que ya hace el indexer (nodos de documento y wiki_links).
    """
    result = extractor.extract(text, chunk_id, source_path, frontmatter)

    # Resolución de entidades (evita duplicados tipo "Juan Pérez" / "J. Pérez")
    result.entities = LLMExtractor.resolve_entities(
        result.entities,
        similarity_threshold=get_settings().entity_similarity_threshold,
    )
    entity_index = LLMExtractor.build_entity_index(result.entities)

    # Insertar entidades como nodos
    for ent in result.entities:
        kg_manager.add_document_node(
            doc_id=ent.name,
            metadata={
                "type": ent.type,
                "description": ent.description or "",
                "chunk_id": ent.chunk_id or chunk_id,
                "source_path": ent.source_path or source_path,
                "extracted": True,
            },
        )

    # Insertar relaciones como aristas
    for rel in result.relations:
        src = entity_index.get(normalize_name(rel.source), rel.source)
        tgt = entity_index.get(normalize_name(rel.target), rel.target)
        kg_manager.add_relation(
            source_id=src,
            target_id=tgt,
            relation_type=rel.type,
            description=rel.description or "",
            chunk_id=rel.chunk_id or chunk_id,
        )

    # Nodos "gratis" desde el frontmatter (opcional, desactivado por defecto)
    if add_frontmatter_nodes and frontmatter:
        doc_title = frontmatter.get("title", source_path)
        for field in ("cliente", "sistema", "categoria", "criticidad"):
            val = frontmatter.get(field)
            if val:
                kg_manager.add_document_node(
                    doc_id=f"fm:{field}:{val}",
                    metadata={
                        "type": "metadata",
                        "field": field,
                        "source_path": source_path,
                        "extracted": False,
                    },
                )
                kg_manager.add_relation(
                    source_id=doc_title,
                    target_id=f"fm:{field}:{val}",
                    relation_type="tiene_" + field,
                    source_path=source_path,
                )

        # Enlaces wiki desde link_to (lista o string)
        link_to = frontmatter.get("link_to", [])
        if isinstance(link_to, str):
            link_to = [link_to]
        for link in link_to:
            target = link.strip("[]").split("|")[0]  # [[target|alias]] -> target
            kg_manager.add_relation(
                source_id=doc_title,
                target_id=target,
                relation_type="wiki_link",
                source_path=source_path,
            )

    return result
