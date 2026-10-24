#!/usr/bin/env python3
"""
Script para crear un nuevo cliente en la Base del Conocimiento.

Crea el directorio bajo data/clientes/<slug>/ con:
- Un archivo índice central (<slug>.md)
- Un archivo por sistema (<slug>_<sistema>.md)

Cada archivo incluye frontmatter YAML y enlaces wiki bidireccionales.

Uso:
    PYTHONPATH=. python3 scripts/crear_cliente.py "Hotel Guayarmina" iptv xgspon switches voip tv wifi
    PYTHONPATH=. python3 scripts/crear_cliente.py "Hotel Guayarmina"          # usa sistemas por defecto
"""

import argparse
import re
from datetime import date
from pathlib import Path

# Sistemas por defecto (mismos que Los Olivos)
SISTEMAS_POR_DEFECTO = ["iptv", "xgspon", "switches", "voip", "tv", "wifi"]

# Mapeo de sistema -> categoria y criticidad por defecto
SISTEMA_META = {
    "iptv":    {"categoria": "infraestructura_red", "criticidad": "alta",   "tags": ["#iptv", "#red"]},
    "xgspon":  {"categoria": "infraestructura_red", "criticidad": "alta",   "tags": ["#xgspon", "#olt", "#red"]},
    "switches":{"categoria": "infraestructura_red", "criticidad": "alta",   "tags": ["#switch", "#red", "#vlan"]},
    "voip":    {"categoria": "infraestructura_red", "criticidad": "media",  "tags": ["#voip", "#telefonia"]},
    "tv":      {"categoria": "infraestructura_red", "criticidad": "media",  "tags": ["#tv", "#senal"]},
    "wifi":    {"categoria": "infraestructura_red", "criticidad": "media",  "tags": ["#wifi", "#inalambrico"]},
}


def slugify(nombre: str) -> str:
    """Convierte un nombre legible en un slug válido para ids y nombres de archivo."""
    slug = nombre.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)      # quitar caracteres especiales
    slug = re.sub(r'[\s_-]+', '_', slug)      # espacios/guiones -> guion bajo
    return slug


def frontmatter(cliente_nombre: str, slug: str, sistema: str, categoria: str,
                criticidad: str, tags: list, link_to: list | str, fecha: str) -> str:
    """Genera el bloque YAML de frontmatter."""
    lines = [
        "---",
        f"id: {slug}",
        f"title: {slug}",
        f"cliente: {cliente_nombre}",
        f"sistema: {sistema}",
        f"categoria: {categoria}",
        f"criticidad: {criticidad}",
        "autor: Departamento TI",
    ]
    # tags como lista YAML
    lines.append("tags:")
    for t in tags:
        lines.append(f"  - \"{t}\"")
    # link_to
    if isinstance(link_to, list):
        lines.append("link_to:")
        for l in link_to:
            lines.append(f"  - {l}")
    else:
        lines.append(f"link_to: {link_to}")
    lines.append(f"fecha_actualizacion: {fecha}")
    lines.append("---")
    return "\n".join(lines)


def crear_cliente(cliente_nombre: str, sistemas: list, data_dir: str = "data",
                  fecha: str | None = None):
    """Crea el directorio y los archivos Markdown para un cliente."""
    if fecha is None:
        fecha = date.today().isoformat()

    slug = slugify(cliente_nombre)
    base = Path(data_dir) / "clientes" / slug
    base.mkdir(parents=True, exist_ok=True)

    tag_cliente = f"#{slug.upper()}"
    link_subsistemas = [f"[[{slug}_{s}]]" for s in sistemas]

    # --- Archivo índice central ---
    central_path = base / f"{slug}.md"
    central_fm = frontmatter(
        cliente_nombre=cliente_nombre,
        slug=slug,
        sistema="central",
        categoria="base_conocimiento",
        criticidad="alta",
        tags=[tag_cliente, "#red", "#central", "#infraestructura"],
        link_to=link_subsistemas,
        fecha=fecha,
    )
    central_body = f"""# {cliente_nombre} - Base del Conocimiento

## Resumen

Sitio central de documentación para el cliente **{cliente_nombre}**. Este nodo agrupa los subsistemas de red, XGS-PON, IPTV, switches, VoIP, TV y WiFi.

## Sistemas activos

"""
    for s in sistemas:
        meta = SISTEMA_META.get(s, {})
        nombre_sistema = s.upper()
        central_body += f"- [[{slug}_{s}]] - {nombre_sistema}\n"

    central_body += f"""

## Incidencias destacadas

<!-- Rellena aquí las incidencias del cliente {cliente_nombre} -->
"""
    central_path.write_text(central_fm + "\n\n" + central_body, encoding="utf-8")
    print(f"Creado: {central_path}")

    # --- Archivos de subsistema ---
    for s in sistemas:
        meta = SISTEMA_META.get(s, {"categoria": "infraestructura_red", "criticidad": "media", "tags": []})
        sub_path = base / f"{slug}_{s}.md"
        sub_fm = frontmatter(
            cliente_nombre=cliente_nombre,
            slug=slug,
            sistema=s,
            categoria=meta["categoria"],
            criticidad=meta["criticidad"],
            tags=[tag_cliente] + meta["tags"],
            link_to=f"[[{slug}]]",
            fecha=fecha,
        )
        sub_body = f"""# {slug}_{s}

**Cronología de acciones sobre [[{slug}]].**

<!-- Rellena aquí el conocimiento de {s} para {cliente_nombre} -->
"""
        sub_path.write_text(sub_fm + "\n\n" + sub_body, encoding="utf-8")
        print(f"Creado: {sub_path}")

    print(f"\nCliente '{cliente_nombre}' creado en {base}")
    print(f"Sistemas: {', '.join(sistemas)}")
    print(f"\nPara indexar ejecuta:")
    print(f"  PYTHONPATH=. python3 -m src.vectorstore.indexer")


def main():
    parser = argparse.ArgumentParser(
        description="Crea un nuevo cliente en la Base del Conocimiento con sus sistemas y frontmatter."
    )
    parser.add_argument("nombre", help="Nombre del cliente (ej. 'Hotel Guayarmina')")
    parser.add_argument(
        "sistemas",
        nargs="*",
        default=SISTEMAS_POR_DEFECTO,
        help="Lista de sistemas a crear (por defecto: iptv xgspon switches voip tv wifi)",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directorio base de datos (por defecto: data)",
    )
    parser.add_argument(
        "--fecha",
        default=None,
        help="Fecha de actualización en formato YYYY-MM-DD (por defecto: hoy)",
    )
    args = parser.parse_args()

    crear_cliente(
        cliente_nombre=args.nombre,
        sistemas=args.sistemas,
        data_dir=args.data_dir,
        fecha=args.fecha,
    )


if __name__ == "__main__":
    main()
