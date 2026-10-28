#!/usr/bin/env python3
"""
Script para crear la estructura de directorios y los documentos Markdown
iniciales de un cliente en la Base del Conocimiento (Graph RAG).

Crea bajo data/clientes/<slug>/:
    - <slug>.md             -> índice central / muro de conocimiento del cliente
    - <slug>_<sistema>.md   -> un documento por sistema (iptv, xgspon, ...)

Cada documento incluye frontmatter YAML y enlaces wiki bidireccionales
([[target]]) que el indexer y el retriever del proyecto esperan.

También puede inicializar la estructura raíz de data/ (clientes/, incidencias/,
vectorstore/) si aún no existe.

Sistemas soportados por defecto: iptv, xgspon, switches, voip, tv, wifi.

Uso:
    PYTHONPATH=. python3 scripts/crear_estructura.py "Hotel Guayarmina"
    PYTHONPATH=. python3 scripts/crear_estructura.py "Hotel Guayarmina" iptv switches wifi
    PYTHONPATH=. python3 scripts/crear_estructura.py --init-data-dir
    PYTHONPATH=. python3 scripts/crear_estructura.py "Hotel Guayarmina" --force
    PYTHONPATH=. python3 scripts/crear_estructura.py "Hotel Guayarmina" --data-dir /ruta/datos
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Catálogo de sistemas soportados.
# Cada entrada define los metadatos por defecto que se escriben en el
# frontmatter del documento de ese sistema.
# ---------------------------------------------------------------------------
SISTEMAS_POR_DEFECTO = ["iptv", "xgspon", "switches", "voip", "tv", "wifi"]

SISTEMA_META = {
    "iptv": {
        "nombre": "IPTV",
        "descripcion": "STB, televisores y streaming IPTV",
        "categoria": "infraestructura_red",
        "criticidad": "alta",
        "tags": ["#iptv", "#red", "#streaming"],
    },
    "xgspon": {
        "nombre": "XGS-PON",
        "descripcion": "OLT principal y red XGS-PON",
        "categoria": "infraestructura_red",
        "criticidad": "alta",
        "tags": ["#xgspon", "#olt", "#red", "#fibra"],
    },
    "switches": {
        "nombre": "Switches",
        "descripcion": "Conmutadores de acceso y VLANs",
        "categoria": "infraestructura_red",
        "criticidad": "alta",
        "tags": ["#switch", "#red", "#vlan", "#conmutador"],
    },
    "voip": {
        "nombre": "VoIP",
        "descripcion": "Telefonía IP y centrales VoIP",
        "categoria": "infraestructura_red",
        "criticidad": "media",
        "tags": ["#voip", "#telefonia", "#ip"],
    },
    "tv": {
        "nombre": "TV",
        "descripcion": "Televisión y distribución de señal",
        "categoria": "infraestructura_red",
        "criticidad": "media",
        "tags": ["#tv", "#senal"],
    },
    "wifi": {
        "nombre": "WiFi",
        "descripcion": "Redes inalámbricas y puntos de acceso",
        "categoria": "infraestructura_red",
        "criticidad": "media",
        "tags": ["#wifi", "#inalambrico", "#wlan"],
    },
}

# Directorios raíz que se crean bajo data/ cuando se pide --init-data-dir.
DATA_SUBDIRS = ["clientes", "incidencias", "vectorstore"]


def slugify(nombre: str) -> str:
    """Convierte un nombre legible en un slug válido para ids y nombres de archivo."""
    slug = nombre.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)  # quitar caracteres especiales
    slug = re.sub(r"[\s_-]+", "_", slug)  # espacios/guiones -> guion bajo
    return slug


def validar_sistemas(sistemas: list) -> list:
    """Valida que los sistemas solicitados existan en el catálogo.

    Devuelve la lista filtrada (sin duplicados, preservando orden). Sistemas
    desconocidos se ignoran con una advertencia en stderr.
    """
    vistos = set()
    validos = []
    for s in sistemas:
        clave = s.strip().lower()
        if not clave:
            continue
        if clave in vistos:
            continue
        if clave not in SISTEMA_META:
            print(
                f"Advertencia: sistema desconocido '{s}', se omite. "
                f"Sistemas válidos: {', '.join(SISTEMA_META)}",
                file=sys.stderr,
            )
            continue
        vistos.add(clave)
        validos.append(clave)
    return validos


def frontmatter(
    cliente_nombre: str,
    slug: str,
    sistema: str,
    categoria: str,
    criticidad: str,
    tags: list,
    link_to: list | str,
    fecha: str,
    autor: str = "Departamento TI",
) -> str:
    """Genera el bloque YAML de frontmatter."""
    lines = [
        "---",
        f"id: {slug}",
        f"title: {slug}",
        f"cliente: {cliente_nombre}",
        f"sistema: {sistema}",
        f"categoria: {categoria}",
        f"criticidad: {criticidad}",
        f"autor: {autor}",
    ]
    lines.append("tags:")
    for t in tags:
        lines.append(f"  - \"{t}\"")
    if isinstance(link_to, list):
        lines.append("link_to:")
        for l in link_to:
            lines.append(f"  - {l}")
    else:
        lines.append(f"link_to: {link_to}")
    lines.append(f"fecha_actualizacion: {fecha}")
    lines.append("---")
    return "\n".join(lines)


def inicializar_data_dir(data_dir: str = "data", force: bool = False) -> None:
    """Crea la estructura raíz de data/ si no existe."""
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    for sub in DATA_SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)
    print(f"Estructura raíz inicializada en: {root.resolve()}")


def crear_cliente(
    cliente_nombre: str,
    sistemas: list,
    data_dir: str = "data",
    fecha: str | None = None,
    force: bool = False,
    autor: str = "Departamento TI",
) -> Path:
    """Crea el directorio y los archivos Markdown para un cliente.

    Devuelve la ruta al directorio del cliente creado.
    """
    if fecha is None:
        fecha = date.today().isoformat()

    slug = slugify(cliente_nombre)
    base = Path(data_dir) / "clientes" / slug

    if base.exists() and not force:
        print(f"El cliente ya existe en {base}. Usa --force para sobrescribir.", file=sys.stderr)
        return base

    base.mkdir(parents=True, exist_ok=True)

    tag_cliente = f"#{slug.upper()}"
    link_subsistemas = [f"[[{slug}_{s}]]" for s in sistemas]

    # ==================== Archivo índice central ====================
    central_path = base / f"{slug}.md"
    if central_path.exists() and not force:
        print(f"  (omitido, ya existe) {central_path}")
    else:
        central_fm = frontmatter(
            cliente_nombre=cliente_nombre,
            slug=slug,
            sistema="central",
            categoria="base_conocimiento",
            criticidad="alta",
            tags=[tag_cliente, "#red", "#central", "#infraestructura"],
            link_to=link_subsistemas,
            fecha=fecha,
            autor=autor,
        )
        central_body = f"""# {cliente_nombre} - Base del Conocimiento

## Resumen

Sitio central de documentación para el cliente **{cliente_nombre}**. Este nodo agrupa los subsistemas de red, XGS-PON, IPTV, switches, VoIP, TV y WiFi.

## Sistemas activos

"""
        for s in sistemas:
            meta = SISTEMA_META[s]
            central_body += f"- [[{slug}_{s}]] - {meta['descripcion']}\n"

        central_body += f"""

## Incidencias destacadas

<!-- Rellena aquí las incidencias del cliente {cliente_nombre} -->
"""
        central_path.write_text(central_fm + "\n\n" + central_body, encoding="utf-8")
        print(f"Creado: {central_path}")

    # ==================== Archivos de subsistema ====================
    for s in sistemas:
        meta = SISTEMA_META[s]
        sub_path = base / f"{slug}_{s}.md"
        if sub_path.exists() and not force:
            print(f"  (omitido, ya existe) {sub_path}")
            continue

        sub_fm = frontmatter(
            cliente_nombre=cliente_nombre,
            slug=slug,
            sistema=meta["nombre"],
            categoria=meta["categoria"],
            criticidad=meta["criticidad"],
            tags=[tag_cliente] + meta["tags"],
            link_to=f"[[{slug}]]",
            fecha=fecha,
            autor=autor,
        )
        sub_body = f"""# {slug}_{s}

**Cronología de acciones sobre [[{slug}]].**

<!-- Rellena aquí el conocimiento de {meta['nombre']} para {cliente_nombre} -->
"""
        sub_path.write_text(sub_fm + "\n\n" + sub_body, encoding="utf-8")
        print(f"Creado: {sub_path}")

    return base


def listar_sistemas() -> None:
    """Imprime el catálogo de sistemas disponibles."""
    print("Sistemas disponibles:")
    for clave, meta in SISTEMA_META.items():
        marca = " (por defecto)" if clave in SISTEMAS_POR_DEFECTO else ""
        print(f"  - {clave:10s} -> {meta['nombre']} ({meta['categoria']}, {meta['criticidad']}){marca}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Crea la estructura de directorios y los documentos Markdown iniciales "
            "de un cliente en la Base del Conocimiento."
        ),
        epilog=(
            "Ejemplos:\n"
            "  %(prog)s \"Hotel Guayarmina\"\n"
            "  %(prog)s \"Hotel Guayarmina\" iptv switches wifi\n"
            "  %(prog)s --init-data-dir\n"
            "  %(prog)s \"Hotel Guayarmina\" --force\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "nombre",
        nargs="?",
        help="Nombre del cliente (ej. 'Hotel Guayarmina'). Opcional si usas --init-data-dir o --listar-sistemas.",
    )
    parser.add_argument(
        "sistemas",
        nargs="*",
        default=SISTEMAS_POR_DEFECTO,
        help="Lista de sistemas a crear (por defecto: iptv xgspon switches voip tv wifi).",
    )
    parser.add_argument(
        "--init-data-dir",
        action="store_true",
        help="Inicializa solo la estructura raíz de data/ (clientes/, incidencias/, vectorstore/).",
    )
    parser.add_argument(
        "--listar-sistemas",
        action="store_true",
        help="Lista los sistemas disponibles y sale.",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directorio base de datos (por defecto: data).",
    )
    parser.add_argument(
        "--fecha",
        default=None,
        help="Fecha de actualización en formato YYYY-MM-DD (por defecto: hoy).",
    )
    parser.add_argument(
        "--autor",
        default="Departamento TI",
        help="Autor que se registra en el frontmatter (por defecto: Departamento TI).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribe archivos existentes en lugar de omitirlos.",
    )
    args = parser.parse_args()

    if args.listar_sistemas:
        listar_sistemas()
        return

    if args.init_data_dir:
        inicializar_data_dir(args.data_dir, force=args.force)
        if args.nombre is None:
            return

    if args.nombre is None:
        parser.error(
            "se requiere el nombre del cliente (usa --init-data-dir para solo inicializar data/ o --listar-sistemas)"
        )

    sistemas = validar_sistemas(args.sistemas)
    if not sistemas:
        parser.error("no se especificó ningún sistema válido")

    base = crear_cliente(
        cliente_nombre=args.nombre,
        sistemas=sistemas,
        data_dir=args.data_dir,
        fecha=args.fecha,
        force=args.force,
        autor=args.autor,
    )

    print(f"\nCliente '{args.nombre}' listo en {base.resolve()}")
    print(f"Sistemas: {', '.join(sistemas)}")
    print(f"\nPara indexar el nuevo contenido ejecuta:")
    print(f"  PYTHONPATH=. python3 -m src.vectorstore.indexer")


if __name__ == "__main__":
    main()
