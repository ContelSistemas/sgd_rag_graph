# src/documentation/agent.py
"""Agente de documentación de incidencias para la Base del Conocimiento.

El agente recibe notas crudas de un incidente (caso, pruebas y resolución)
y, con ayuda del LLM local, devuelve la información organizada en el esquema
de frontmatter del proyecto y lista para guardarse como archivo Markdown en
``data/incidencias/``.

Órdenes del agente (system prompt):
- Leer detenidamente el caso, las pruebas y la resolución proporcionadas.
- No inventar datos: si algo no aparece en las notas, usar un valor por defecto
  razonable o dejarlo vacío, pero nunca alucinar fechas, IPs ni equipos.
- Organizar la información en el esquema de frontmatter del proyecto.
- Generar el cuerpo del documento en Markdown con las secciones estándar:
  Síntoma del Problema, Causa Raíz, Protocolo de Resolución y
  Comprobación de Verificación.
- Responder ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from src.config import get_settings
from src.config.settings import Settings


class IncidentFrontmatter:
    """Esquema de metadatos (frontmatter YAML) de un archivo de incidencia."""

    REQUIRED_FIELDS = [
        "id",
        "title",
        "caso",
        "tipo",
        "categoria",
        "sistema",
        "criticidad",
        "tags",
        "clientes_afectados",
        "fecha_deteccion",
        "fecha_actualizacion",
    ]

    def __init__(
        self,
        id: str,
        title: str,
        caso: str,
        tipo: str = "incidencia",
        categoria: str = "general",
        sistema: str = "general",
        criticidad: str = "media",
        tags: Optional[List[str]] = None,
        clientes_afectados: Optional[List[str]] = None,
        fecha_deteccion: Optional[str] = None,
        fecha_actualizacion: Optional[str] = None,
        **extra: Any,
    ):
        self.id = id
        self.title = title
        self.caso = caso
        self.tipo = tipo
        self.categoria = categoria
        self.sistema = sistema
        self.criticidad = criticidad
        self.tags = tags or []
        self.clientes_afectados = clientes_afectados or []
        today = date.today().isoformat()
        self.fecha_deteccion = fecha_deteccion or today
        self.fecha_actualizacion = fecha_actualizacion or today
        self.extra = extra

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "caso": self.caso,
            "tipo": self.tipo,
            "categoria": self.categoria,
            "sistema": self.sistema,
            "criticidad": self.criticidad,
            "tags": self.tags,
            "clientes_afectados": self.clientes_afectados,
            "fecha_deteccion": self.fecha_deteccion,
            "fecha_actualizacion": self.fecha_actualizacion,
        }
        data.update(self.extra)
        return data

    def to_yaml(self) -> str:
        """Serializa el frontmatter a bloque YAML entre ``---``."""
        lines: List[str] = ["---"]
        for key, value in self.to_dict().items():
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        return "\n".join(lines)


class DocumentationResult:
    """Resultado del agente: frontmatter, cuerpo markdown y ruta del archivo."""

    def __init__(
        self,
        frontmatter: IncidentFrontmatter,
        body: str,
        file_path: Optional[Path] = None,
        raw_llm_output: Optional[str] = None,
    ):
        self.frontmatter = frontmatter
        self.body = body
        self.file_path = file_path
        self.raw_llm_output = raw_llm_output

    @property
    def full_markdown(self) -> str:
        return f"{self.frontmatter.to_yaml()}\n\n{self.body.strip()}\n"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frontmatter": self.frontmatter.to_dict(),
            "body": self.body,
            "file_path": str(self.file_path) if self.file_path else None,
            "raw_llm_output": self.raw_llm_output,
        }


class DocumentationAgent:
    """Agente que organiza notas de incidente usando el LLM local."""

    def __init__(
        self,
        incidencias_dir: Optional[str] = None,
        backend: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        temperature: float = 0.2,
        n_predict: int = 1024,
        settings: Optional[Settings] = None,
    ):
        self.settings = settings or get_settings()
        self.incidencias_dir = Path(
            incidencias_dir or self.settings.data_dir
        ) / "incidencias"
        self.incidencias_dir.mkdir(parents=True, exist_ok=True)

        self.backend = (backend or self.settings.llm_backend).lower()
        self.base_url = (base_url or self.settings.llm_base_url).rstrip("/")
        self.model_name = model_name or self.settings.llm_model_name
        self.timeout = timeout if timeout is not None else self.settings.llm_timeout
        self.max_retries = max_retries if max_retries is not None else self.settings.llm_max_retries
        self.base_delay = base_delay if base_delay is not None else self.settings.llm_base_delay
        self.temperature = temperature
        self.n_predict = n_predict

    # ------------------------------------------------------------------ #
    # Órdenes del agente (system prompt)
    # ------------------------------------------------------------------ #
    def _system_prompt(self) -> str:
        return """Eres un asistente experto en documentación de incidencias de red e infraestructura TI para la Base del Conocimiento (Graph RAG).

Tu misión es tomar notas crudas de un incidente (caso, pruebas y resolución) y convertirlas en un archivo de incidencia estructurado y listo para indexar, siguiendo el estándar del proyecto.

Órdenes obligatorias:
1. Lee TODO el caso, las pruebas y la resolución proporcionados antes de organizar nada.
2. No inventes datos: si alguna información no aparece en las notas, usa un valor por defecto razonable o deja el campo vacío, pero nunca alucines fechas, direcciones IP, nombres de equipos ni clientes.
3. Organiza la información en el esquema de frontmatter YAML del proyecto con estos campos obligatorios:
   - id: identificador único del caso (ej. NET-IPTV-0042). Si el usuario no lo da, généralo como "<SISTEMA>-<TIPO>-NNNN" basado en el sistema y un número correlativo.
   - title: título descriptivo y corto del incidente.
   - caso: mismo valor que id.
   - tipo: siempre "incidencia".
   - categoria: categoría técnica (ej. redes_iptv, redes_xgspon, redes_switches, voip, tv, wifi, general).
   - sistema: sistema afectado (ej. iptv, xgspon, switches, voip, tv, wifi, general).
   - criticidad: baja, media, alta o critica.
   - tags: lista de etiquetas con prefijo # (ej. #incidencia, #iptv, #igmp).
   - clientes_afectados: lista de slugs de clientes afectados (ej. hotel_villa_cortes).
   - fecha_deteccion: fecha en formato YYYY-MM-DD (usa hoy si no se indica).
   - fecha_actualizacion: fecha en formato YYYY-MM-DD (usa hoy si no se indica).
4. Genera el cuerpo del documento en Markdown con estas secciones estándar:
   - ## 1. Síntoma del Problema
   - ## 2. Causa Raíz (Análisis Técnico)
   - ## 3. Protocolo de Resolución (incluye solución definitiva y workaround temporal si aplica)
   - ## 4. Comprobación de Verificación
5. Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después.
6. El JSON debe tener exactamente estas claves:
   - "frontmatter": objeto con los campos del punto 3.
   - "body": string con el cuerpo Markdown completo (sin el frontmatter YAML).
7. No uses bloques de código ```json ``` en la respuesta, solo el objeto JSON puro.

Hoy es {today}.""".format(today=date.today().isoformat())

    def _build_user_prompt(
        self,
        caso: str,
        pruebas: str,
        resolucion: str,
    ) -> str:
        return f"""# Caso del incidente:
{caso}

# Pruebas realizadas:
{pruebas}

# Resolución aplicada:
{resolucion}

Organiza esta información siguiendo las órdenes del sistema y devuélveme el objeto JSON.""".strip()

    # ------------------------------------------------------------------ #
    # Llamada al LLM local
    # ------------------------------------------------------------------ #
    def _call_llm_json(self, prompt: str) -> str:
        """Llama al LLM local (Ollama / llama.cpp) forzando salida JSON."""
        is_ollama = "ollama" in self.base_url.lower() or "/api/generate" in self.base_url

        if is_ollama:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.n_predict,
                },
            }
            url = f"{self.base_url}/api/generate"
        else:
            # llama.cpp /completion
            payload = {
                "prompt": prompt,
                "format": "json",
                "temperature": self.temperature,
                "n_predict": self.n_predict,
                "stream": False,
                "stop": ["\nCaso del incidente:", "\nPruebas realizadas:", "\nResolución aplicada:"],
            }
            url = f"{self.base_url}/completion"

        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "") if is_ollama else data.get("content", "")
                if response.status_code >= 500:
                    last_error = f"Server error {response.status_code}: {response.text}"
                else:
                    last_error = f"HTTP error {response.status_code}: {response.text}"
            except requests.Timeout:
                last_error = f"Timeout after {self.timeout}s"
            except requests.ConnectionError as e:
                last_error = f"Connection error: {e}"
            except Exception as e:
                last_error = f"Unexpected error: {e}"

            if attempt < self.max_retries - 1:
                delay = self.base_delay * (2 ** attempt)
                import time

                time.sleep(delay)

        raise requests.RequestException(
            f"Failed after {self.max_retries} retries to call LLM at {self.base_url}. Last error: {last_error}"
        )

    # ------------------------------------------------------------------ #
    # Parsado y validación de la salida del LLM
    # ------------------------------------------------------------------ #
    @staticmethod
    def _clean_json(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        return raw

    @staticmethod
    def _parse_output(raw: str) -> Dict[str, Any]:
        cleaned = DocumentationAgent._clean_json(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    raise ValueError(f"El LLM no devolvió JSON válido: {cleaned[:200]}...")
            raise ValueError(f"El LLM no devolvió JSON válido: {cleaned[:200]}...")

    @staticmethod
    def _build_frontmatter(data: Dict[str, Any]) -> IncidentFrontmatter:
        fm = data.get("frontmatter", {})
        missing = [f for f in IncidentFrontmatter.REQUIRED_FIELDS if not fm.get(f)]
        if missing:
            raise ValueError(f"El frontmatter falta campos obligatorios: {missing}")

        extra = {k: v for k, v in fm.items() if k not in IncidentFrontmatter.REQUIRED_FIELDS}
        return IncidentFrontmatter(
            id=str(fm["id"]),
            title=str(fm["title"]),
            caso=str(fm.get("caso", fm["id"])),
            tipo=str(fm.get("tipo", "incidencia")),
            categoria=str(fm.get("categoria", "general")),
            sistema=str(fm.get("sistema", "general")),
            criticidad=str(fm.get("criticidad", "media")),
            tags=list(fm.get("tags", [])),
            clientes_afectados=list(fm.get("clientes_afectados", [])),
            fecha_deteccion=str(fm.get("fecha_deteccion", date.today().isoformat())),
            fecha_actualizacion=str(fm.get("fecha_actualizacion", date.today().isoformat())),
            **extra,
        )

    # ------------------------------------------------------------------ #
    # Flujo principal
    # ------------------------------------------------------------------ #
    def organize(
        self,
        caso: str,
        pruebas: str,
        resolucion: str,
    ) -> DocumentationResult:
        """Organiza las notas del incidente usando el LLM local.

        Devuelve un DocumentationResult con frontmatter y cuerpo Markdown,
        pero NO escribe el archivo en disco. Usa ``create_file`` para
        persistirlo.
        """
        system_prompt = self._system_prompt()
        user_prompt = self._build_user_prompt(caso, pruebas, resolucion)
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        raw = self._call_llm_json(full_prompt)
        data = self._parse_output(raw)

        frontmatter = self._build_frontmatter(data)
        body = data.get("body", "").strip()

        return DocumentationResult(
            frontmatter=frontmatter,
            body=body,
            raw_llm_output=raw,
        )

    def create_file(
        self,
        result: DocumentationResult,
        overwrite: bool = False,
    ) -> Path:
        """Escribe el resultado en ``data/incidencias/<id>.md`` y devuelve la ruta."""
        file_path = self.incidencias_dir / f"{result.frontmatter.id}.md"
        if file_path.exists() and not overwrite:
            raise FileExistsError(
                f"El archivo ya existe: {file_path}. Pasa overwrite=True para reemplazarlo."
            )

        file_path.write_text(result.full_markdown, encoding="utf-8")
        result.file_path = file_path
        return file_path

    def run(
        self,
        caso: str,
        pruebas: str,
        resolucion: str,
        write_file: bool = True,
        overwrite: bool = False,
    ) -> DocumentationResult:
        """Flujo completo: organiza con el LLM y (opcionalmente) guarda el archivo."""
        result = self.organize(caso, pruebas, resolucion)
        if write_file:
            self.create_file(result, overwrite=overwrite)
        return result
