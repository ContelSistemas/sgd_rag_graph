#!/usr/bin/env python3
"""
Validador de archivos Markdown para Graph RAG.

Verifica que cada archivo .md en data/ tenga:
  - Frontmatter YAML válido con campos requeridos
  - Enlaces wiki [[...]] bien formados en link_to y cuerpo
  - Jerarquía de encabezados (#, ##, ###)
  - ID único en todo el proyecto
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

DATA_DIR = Path("data")

CAMPOS_REQUERIDOS = {
    "id",
    "title",
    "cliente",
    "sistema",
    "categoria",
    "criticidad",
    "autor",
    "tags",
    "link_to",
    "fecha_actualizacion",
}

WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]](?:\|([^\]]+)\]])?")


def validar_archivo(ruta: Path) -> List[str]:
    """Devuelve lista de errores encontrados en el archivo."""
    errores: List[str] = []
    contenido = ruta.read_text(encoding="utf-8")

    # --- Frontmatter ---
    if not contenido.startswith("---\n"):
        errores.append("Falta delimitador '---' de inicio del frontmatter")
        return errores

    partes = contenido.split("---", 2)
    if len(partes) < 3:
        errores.append("Frontmatter YAML incompleto (faltan delimitadores)")
        return errores

    try:
        frontmatter = yaml.safe_load(partes[1]) or {}
    except yaml.YAMLError as exc:
        errores.append(f"Error parseando YAML frontmatter: {exc}")
        return errores

    # Campos requeridos
    for campo in CAMPOS_REQUERIDOS:
        if campo not in frontmatter:
            errores.append(f"Campo requerido faltante: {campo}")

    # Validar fecha
    fecha = frontmatter.get("fecha_actualizacion", "")
    try:
        from datetime import date
        date.fromisoformat(str(fecha))
    except (ValueError, TypeError):
        errores.append(f"fecha_actualizacion inválida: {fecha} (esperado YYYY-MM-DD)")

    # Validar tags es lista
    tags = frontmatter.get("tags")
    if tags is not None and not isinstance(tags, list):
        errores.append("tags debe ser una lista YAML")

    # Validar link_to son enlaces wiki válidos
    link_to = frontmatter.get("link_to")
    if link_to:
        if isinstance(link_to, str):
            enlaces = [link_to]
        elif isinstance(link_to, list):
            enlaces = [str(e) for e in link_to]
        else:
            enlaces = []
        for enlace in enlaces:
            if not WIKI_LINK_RE.match(str(enlace).strip()):
                errores.append(f"Enlace wiki inválido en link_to: {enlace}")

    # --- Cuerpo: encabezados ---
    cuerpo = partes[2] if len(partes) >= 3 else ""
    encabezados = re.findall(r"^(#{1,6})\s+(.+)$", cuerpo, re.MULTILINE)
    if not encabezados:
        errores.append("No se encontraron encabezados (#, ##, ###) en el cuerpo")

    # --- Wiki links en cuerpo ---
    wiki_links_en_cuerpo = WIKI_LINK_RE.findall(contenido)
    if not wiki_links_en_cuerpo and not link_to:
        errores.append("No hay enlaces wiki [[...]] ni en frontmatter ni en cuerpo")

    return errores


def main() -> None:
    archivos = sorted(DATA_DIR.rglob("*.md"))
    if not archivos:
        print("No se encontraron archivos .md en data/")
        return

    ids_vistos: Dict[str, Path] = {}
    total_errores = 0

    print("=" * 70)
    print("  Validación de archivos Markdown para Graph RAG")
    print("=" * 70)

    for ruta in archivos:
        if "vectorstore" in ruta.parts:
            continue
        errores = validar_archivo(ruta)

        # Verificar ID único
        try:
            contenido = ruta.read_text(encoding="utf-8")
            partes = contenido.split("---", 2)
            if len(partes) >= 3:
                fm = yaml.safe_load(partes[1]) or {}
                id_ = fm.get("id")
                if id_:
                    if id_ in ids_vistos:
                        errores.append(f"ID duplicado: {id_} (ya en {ids_vistos[id_]})")
                    else:
                        ids_vistos[id_] = ruta
        except Exception:  # noqa: BLE001
            pass

        estado = "✅ OK" if not errores else "❌ ERRORES"
        print(f"\n{estado} | {ruta}")
        for err in errores:
            print(f"   ⚠️  {err}")
        total_errores += len(errores)

    print("\n" + "=" * 70)
    print(f" Total archivos: {len(archivos)} | Errores: {total_errores}")
    print("=" * 70)


if __name__ == "__main__":
    main()
