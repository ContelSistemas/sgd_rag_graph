#!/usr/bin/env python3
"""CLI de ejemplo para documentar una incidencia con el DocumentationAgent.

Lee el caso, las pruebas y la resolución desde argumentos o stdin,
llama al LLM local para organizar la información y guarda el archivo
en data/incidencias/<ID>.md.

Uso:
    PYTHONPATH=. python3 scripts/documentar_incidencia.py \
        --caso "..." --pruebas "..." --resolucion "..."

O pasando las notas por stdin (una sección por línea precedida de CASO:/PRUEBAS:/RESOLUCION:).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.documentation import DocumentationAgent


def _leer_notas() -> dict:
    """Lee notas desde stdin si no se pasaron por argumentos."""
    notas = {"caso": "", "pruebas": "", "resolucion": ""}
    clave_actual = None
    for linea in sys.stdin:
        linea = linea.rstrip("\n")
        if linea.startswith("CASO:"):
            clave_actual = "caso"
            notas["caso"] += linea[len("CASO:"):].strip() + "\n"
        elif linea.startswith("PRUEBAS:"):
            clave_actual = "pruebas"
            notas["pruebas"] += linea[len("PRUEBAS:"):].strip() + "\n"
        elif linea.startswith("RESOLUCION:"):
            clave_actual = "resolucion"
            notas["resolucion"] += linea[len("RESOLUCION:"):].strip() + "\n"
        elif clave_actual:
            notas[clave_actual] += linea + "\n"
    return {k: v.strip() for k, v in notas.items()}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Documenta una incidencia usando el LLM local y la guarda en data/incidencias/."
    )
    parser.add_argument("--caso", help="Descripción del caso del incidente")
    parser.add_argument("--pruebas", help="Pruebas realizadas")
    parser.add_argument("--resolucion", help="Resolución aplicada")
    parser.add_argument(
        "--no-guardar",
        action="store_true",
        help="Solo organiza con el LLM, no escribe el archivo en disco",
    )
    parser.add_argument(
        "--sobreescribir",
        action="store_true",
        help="Sobreescribe el archivo si ya existe",
    )
    args = parser.parse_args()

    caso = args.caso
    pruebas = args.pruebas
    resolucion = args.resolucion

    # Si falta algo, intentar leer desde stdin
    if not (caso and pruebas and resolucion):
        notas = _leer_notas()
        caso = caso or notas["caso"]
        pruebas = pruebas or notas["pruebas"]
        resolucion = resolucion or notas["resolucion"]

    if not (caso and pruebas and resolucion):
        print("Error: se requieren caso, pruebas y resolución (por argumento o stdin).", file=sys.stderr)
        return 1

    agent = DocumentationAgent()
    try:
        result = agent.run(
            caso=caso,
            pruebas=pruebas,
            resolucion=resolucion,
            write_file=not args.no_guardar,
            overwrite=args.sobreescribir,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Error al documentar la incidencia: {exc}", file=sys.stderr)
        return 1

    print("=== Incidencia organizada ===")
    print(f"ID:           {result.frontmatter.id}")
    print(f"Título:       {result.frontmatter.title}")
    print(f"Sistema:      {result.frontmatter.sistema}")
    print(f"Categoría:    {result.frontmatter.categoria}")
    print(f"Criticidad:   {result.frontmatter.criticidad}")
    print(f"Clientes:     {', '.join(result.frontmatter.clientes_afectados) or '(ninguno)'}")
    print(f"Tags:         {', '.join(result.frontmatter.tags) or '(ninguno)'}")
    print(f"F. detección: {result.frontmatter.fecha_deteccion}")
    print(f"F. actualización: {result.frontmatter.fecha_actualizacion}")
    if result.file_path:
        print(f"\nArchivo guardado en: {result.file_path}")
        print("\nPuedes volver a indexar con:")
        print("    PYTHONPATH=. python3 -m src.vectorstore.indexer")
    else:
        print("\n(No se guardó el archivo. Pasa --guardar para persistirlo.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
