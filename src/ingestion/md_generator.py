#!/usr/bin/env python3
"""
Generador de Markdown estructurado para Graph RAG Base del Conocimiento.

Crea archivos Markdown con frontmatter YAML válido y jerarquía de encabezados
compatible con el pipeline: Parser → Chunker → Grafo → VectorStore.

Campos del frontmatter (según src/config/settings.py y parser.py):
  - id: identificador único del documento
  - title: título legible
  - cliente: nombre del cliente
  - sistema: subsistema (GPON, IPTV, network, etc.)
  - categoria: infraestructura_red, base_conocimiento, etc.
  - criticidad: alta, media, baja
  - autor: Departamento TI
  - tags: lista de etiquetas
  - link_to: enlaces wiki [[nodo]] para crear aristas en el grafo
  - fecha_actualizacion: YYYY-MM-DD
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import List, Optional

import yaml

# ---------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------

DATA_DIR = Path("data")
VALID_CATEGORIAS = {
    "infraestructura_red",
    "base_conocimiento",
    "procedimiento",
    "incidencia",
    "configuracion",
    "inventario",
}
VALID_CRITICIDAD = {"alta", "media", "baja"}
VALID_SISTEMAS = {"GPON", "IPTV", "network", "central", "voip", "wifi", "seguridad"}

# Expresión para validar enlaces wiki: [[target]] o [[target|alias]]
WIKI_LINK_RE = re.compile(r"^\[\[([^\]]+)\]](?:\|([^\]]+)\]])?$")

# ---------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------


def slugify(text: str) -> str:
    """Convierte texto en slug seguro para usar como parte de un id."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def sugerir_id(cliente: str, sistema: str, numero: int = 1) -> str:
    """Genera un id sugerido basado en cliente y sistema."""
    return f"{slugify(cliente)}_{slugify(sistema)}_{numero:03d}"


def validar_fecha(fecha: str) -> bool:
    """Valida que la fecha tenga formato YYYY-MM-DD."""
    try:
        date.fromisoformat(fecha)
        return True
    except ValueError:
        return False


def validar_link_to(valor: str) -> bool:
    """Valida que un enlace wiki tenga la forma [[target]] o [[target|alias]]."""
    return bool(WIKI_LINK_RE.match(valor.strip()))


def parse_link_to(valor: str) -> List[str]:
    """Extrae los targets de una lista de enlaces wiki."""
    targets = []
    for item in valor.split(","):
        item = item.strip()
        if not item:
            continue
        m = WIKI_LINK_RE.match(item)
        if m:
            targets.append(m.group(1).strip())
    return targets


# ---------------------------------------------------------------
# Generador de frontmatter YAML
# ---------------------------------------------------------------


def generar_frontmatter(
    id_: str,
    title: str,
    cliente: str,
    sistema: str,
    categoria: str,
    criticidad: str,
    autor: str,
    tags: List[str],
    link_to: List[str],
    fecha_actualizacion: str,
) -> str:
    """Construye el bloque YAML del frontmatter."""
    link_to_yaml = "\n  - " + "\n  - ".join(link_to) if link_to else ""
    tags_yaml = "\n  - " + "\n  - ".join(tags) if tags else ""

    return (
        f"---\n"
        f"id: {id_}\n"
        f"title: {title}\n"
        f"cliente: {cliente}\n"
        f"sistema: {sistema}\n"
        f"categoria: {categoria}\n"
        f"criticidad: {criticidad}\n"
        f"autor: {autor}\n"
        f"tags:{tags_yaml}\n"
        f"link_to:{link_to_yaml}\n"
        f"fecha_actualizacion: {fecha_actualizacion}\n"
        f"---\n"
    )


# ---------------------------------------------------------------
# Generador de cuerpo Markdown
# ---------------------------------------------------------------


def generar_cuerpo(
    fecha_principal: str,
    secciones: List[dict],
) -> str:
    """
    Genera el cuerpo del Markdown con jerarquía de encabezados.

    Parameters
    ----------
    fecha_principal : str
        Fecha del incidente / entrada principal (ej. "2025-10-05").
    secciones : list[dict]
        Lista de secciones con claves: titulo, nivel, contenido (lista de líneas).
    """
    lineas: List[str] = []
    lineas.append(f"**Cronología de acciones sobre [[{secciones[0].get('cliente', 'Parque Santiago')}]]**.")
    lineas.append("")
    lineas.append(f"# {fecha_principal}")
    lineas.append("")

    for seccion in secciones:
        nivel = seccion.get("nivel", 2)
        titulo = seccion["titulo"]
        lineas.append(f"{'#' * nivel} {titulo}")
        lineas.append("")

        for linea in seccion.get("contenido", []):
            lineas.append(linea)
        lineas.append("")

    return "\n".join(lineas)


# ---------------------------------------------------------------
# Aplicación CLI interactiva
# ---------------------------------------------------------------


def solicitar_entrada(prompt: str, valor_defecto: Optional[str] = None) -> str:
    if valor_defecto:
        prompt = f"{prompt} [{valor_defecto}]: "
    else:
        prompt = f"{prompt}: "
    valor = input(prompt).strip()
    return valor or valor_defecto or ""


def solicitar_lista(prompt: str) -> List[str]:
    print(prompt)
    items: List[str] = []
    while True:
        item = input("  > (Enter para terminar): ").strip()
        if not item:
            break
        items.append(item)
    return items


def solicitar_link_to() -> List[str]:
    """Solicita enlaces wiki y los valida."""
    print("\nEnlaces wiki (link_to) - formato: [[NombreNodo]] o [[NombreNodo|alias]]")
    print("Ejemplo: [[Parque Santiago]]")
    enlaces = solicitar_lista("  Agregar enlaces (uno por línea):")
    for enlace in enlaces:
        if not validar_link_to(enlace):
            print(f"  ⚠️  Formato inválido: {enlace}. Debe ser [[target]] o [[target|alias]]")
    return enlaces


def confirmar(campos: dict) -> bool:
    """Muestra resumen y pide confirmación."""
    print("\n" + "=" * 60)
    print(" RESUMEN DEL ARCHIVO A GENERAR")
    print("=" * 60)
    for clave, valor in campos.items():
        print(f"  {clave}: {valor}")
    print("=" * 60)
    return input("\n¿Generar archivo? (s/N): ").strip().lower() == "s"


def generar_archivo_markdown(campos: dict, ruta_salida: Path) -> str:
    """Genera el contenido completo del Markdown y lo escribe en disco."""
    frontmatter = generar_frontmatter(
        id_=campos["id"],
        title=campos["title"],
        cliente=campos["cliente"],
        sistema=campos["sistema"],
        categoria=campos["categoria"],
        criticidad=campos["criticidad"],
        autor=campos["autor"],
        tags=campos["tags"],
        link_to=campos["link_to"],
        fecha_actualizacion=campos["fecha_actualizacion"],
    )

    cuerpo = generar_cuerpo(
        fecha_principal=campos.get("fecha_principal", campos["fecha_actualizacion"]),
        secciones=campos.get("secciones", []),
    )

    contenido = frontmatter + "\n" + cuerpo + "\n"
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_text(contenido, encoding="utf-8")
    return contenido


def main() -> None:
    print("=" * 60)
    print("  Generador de Markdown para Graph RAG - Base del Conocimiento")
    print("=" * 60)

    # --- Campos obligatorios ---
    cliente = solicitar_entrada("Cliente", "Parque Santiago")
    sistema = solicitar_entrada("Sistema (GPON, IPTV, network, etc.)", "GPON")
    categoria = solicitar_entrada(
        f"Categoría ({', '.join(sorted(VALID_CATEGORIAS))})",
        "infraestructura_red",
    )
    if categoria not in VALID_CATEGORIAS:
        print(f"  ⚠️  Categoría '{categoria}' no está en la lista estándar.")

    criticidad = solicitar_entrada("Criticidad (alta, media, baja)", "alta")
    if criticidad not in VALID_CRITICIDAD:
        print(f"  ⚠️  Criticidad '{criticidad}' no estándar.")

    autor = solicitar_entrada("Autor", "Departamento TI")
    fecha = solicitar_entrada("Fecha actualización (YYYY-MM-DD)", str(date.today()))
    if not validar_fecha(fecha):
        print(f"  ⚠️  Fecha '{fecha}' no tiene formato YYYY-MM-DD.")

    id_sugerido = sugerir_id(cliente, sistema)
    id_ = solicitar_entrada("ID del documento", id_sugerido)
    title = solicitar_entrada("Título", f"{cliente} - {sistema}")

    tags = solicitar_lista("\nTags (uno por línea, ej. #PQS, #red):")
    link_to = solicitar_link_to()

    # --- Cuerpo del documento ---
    print("\n--- Cuerpo del documento ---")
    print("Estructura recomendada:")
    print("  # Fecha del incidente")
    print("  ## Título de la sección")
    print("  ### Subsección (opcional)")
    print("  * contenido...")

    fecha_principal = solicitar_entrada("Fecha principal del encabezado #", fecha)

    secciones: List[dict] = []
    while True:
        print(f"\nSección {len(secciones) + 1}:")
        titulo = input("  Título de la sección: ").strip()
        if not titulo:
            break
        nivel = input("  Nivel de encabezado (2=##, 3=###) [2]: ").strip() or "2"
        try:
            nivel_int = int(nivel)
        except ValueError:
            nivel_int = 2
        contenido: List[str] = []
        print("  Líneas de contenido (Enter vacío para terminar):")
        while True:
            linea = input("    > ").strip()
            if not linea:
                break
            contenido.append(linea)
        secciones.append({"titulo": titulo, "nivel": nivel_int, "contenido": contenido})
        if input("  ¿Agregar otra sección? (s/N): ").strip().lower() != "s":
            break

    campos = {
        "id": id_,
        "title": title,
        "cliente": cliente,
        "sistema": sistema,
        "categoria": categoria,
        "criticidad": criticidad,
        "autor": autor,
        "tags": tags,
        "link_to": link_to,
        "fecha_actualizacion": fecha,
        "fecha_principal": fecha_principal,
        "secciones": secciones,
    }

    if not confirmar(campos):
        print("❌ Operación cancelada.")
        return

    # --- Ruta de salida ---
    ruta_sugerida = DATA_DIR / "clientes" / f"{slugify(cliente)}_{slugify(sistema)}.md"
    ruta_input = input(f"\nRuta de salida [{ruta_sugerida}]: ").strip()
    ruta_salida = Path(ruta_input) if ruta_input else ruta_sugerida

    try:
        contenido = generar_archivo_markdown(campos, ruta_salida)
        print(f"\n✅ Archivo generado: {ruta_salida}")
        print("\n📋 Contenido generado:")
        print(contenido[:500] + ("..." if len(contenido) > 500 else ""))

        # Validar con el parser si está disponible
        try:
            from src.ingestion.parser import MarkdownParser
            parser = MarkdownParser()
            resultado = parser.parse_content(contenido, source_path=str(ruta_salida))
            print("\n✅ Validación con MarkdownParser: OK")
            print(f"   - Frontmatter extraído: {list(resultado['frontmatter'].keys())}")
            print(f"   - Wiki links detectados: {[w['target'] for w in resultado['wiki_links']]}")
        except ImportError:
            pass

    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ Error generando el archivo: {exc}")
        raise


if __name__ == "__main__":
    main()
```
