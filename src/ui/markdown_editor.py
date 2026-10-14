import streamlit as st
from pathlib import Path
import yaml
import re
from typing import Dict, Any, List, Optional
from datetime import date

DATA_DIR = Path("data")

REQUIRED_FIELDS = [
    ("id", "str", "Identificador único del documento"),
    ("title", "str", "Título legible"),
    ("categoria", "str", "Categoría (ej: Normativa, Procedimientos, Plantillas)"),
    ("autor", "str", "Autor del documento"),
    ("creado", "date", "Fecha de creación (YYYY-MM-DD)"),
    ("tags", "list", "Lista de etiquetas"),
    ("status", "str", "Estado: borrador, revisado, aprobado, obsoleto"),
]

WIKI_LINK_REGEX = re.compile(r'\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]')

def parse_markdown(content: str) -> tuple[Dict[str, Any], str]:
    frontmatter = {}
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                frontmatter = {}
            body = parts[2]
    return frontmatter, body.strip()

def serialize_markdown(frontmatter: Dict[str, Any], body: str) -> str:
    fm_yaml = yaml.dump(frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False).strip()
    return f"---\n{fm_yaml}\n---\n\n{body}"

def get_markdown_files() -> List[Path]:
    files = []
    for f in DATA_DIR.rglob("*.md"):
        if f.is_file() and "vectorstore" not in f.parts and "test_vectorstore" not in f.parts:
            files.append(f)
    return sorted(files)

def get_field_value(frontmatter: Dict, field: str, default: Any = "") -> Any:
    return frontmatter.get(field, default)

def render_field_editor(field_name: str, field_type: str, description: str, value: Any) -> Any:
    help_text = f"{description} (tipo: {field_type})"
    
    if field_type == "str":
        return st.text_input(field_name, value=str(value), help=help_text)
    elif field_type == "date":
        if isinstance(value, str):
            try:
                value = date.fromisoformat(value)
            except ValueError:
                value = date.today()
        elif not isinstance(value, date):
            value = date.today()
        return st.date_input(field_name, value=value, help=help_text)
    elif field_type == "list":
        if isinstance(value, str):
            value = [v.strip() for v in value.split(",") if v.strip()]
        elif not isinstance(value, list):
            value = []
        tags_str = ", ".join(value)
        new_tags = st.text_input(field_name, value=tags_str, help=help_text + " (separados por comas)")
        return [v.strip() for v in new_tags.split(",") if v.strip()]
    else:
        return st.text_input(field_name, value=str(value), help=help_text)

def extract_wiki_links(content: str) -> List[Dict[str, str]]:
    links = []
    for match in WIKI_LINK_REGEX.finditer(content):
        target = match.group(1).strip()
        alias = match.group(2).strip() if match.group(2) else target
        links.append({"target": target, "alias": alias})
    return links

def render_markdown_editor():
    st.header("📝 Editor de Documentos Markdown SGD")
    st.markdown("Gestiona el frontmatter obligatorio y el contenido de tus documentos `.md` en `/data`.")
    
    files = get_markdown_files()
    
    if not files:
        st.warning("No se encontraron archivos `.md` en `/data`.")
        return
    
    file_options = {f.relative_to(DATA_DIR).as_posix(): f for f in files}
    selected_rel = st.selectbox("Seleccionar documento", options=list(file_options.keys()))
    selected_file = file_options[selected_rel]
    
    content = selected_file.read_text(encoding="utf-8")
    frontmatter, body = parse_markdown(content)
    
    st.markdown("---")
    st.subheader("📋 Frontmatter (campos obligatorios)")
    
    with st.form(f"frontmatter_form_{selected_rel}"):
        new_frontmatter = {}
        for field_name, field_type, description in REQUIRED_FIELDS:
            current_value = get_field_value(frontmatter, field_name)
            new_frontmatter[field_name] = render_field_editor(field_name, field_type, description, current_value)
        
        required_field_names = {field[0] for field in REQUIRED_FIELDS}
        extra_fields = {k: v for k, v in frontmatter.items() if k not in required_field_names}
        if extra_fields:
            st.markdown("**Campos adicionales detectados:**")
            for k, v in extra_fields.items():
                new_frontmatter[k] = st.text_input(f"Extra: {k}", value=str(v))
        
        submitted = st.form_submit_button("💾 Guardar Frontmatter", type="primary")
        if submitted:
            if not new_frontmatter.get("id"):
                st.error("El campo 'id' es obligatorio")
            else:
                new_content = serialize_markdown(new_frontmatter, body)
                selected_file.write_text(new_content, encoding="utf-8")
                st.success(f"Frontmatter guardado en {selected_rel}")
                st.rerun()
    
    st.markdown("---")
    st.subheader("📄 Contenido del documento")
    
    wiki_links = extract_wiki_links(body)
    if wiki_links:
        link_strs = [f"[[{l['target']}]]" for l in wiki_links]
        st.info(f"🔗 Enlaces wiki detectados: {', '.join(link_strs)}")
    
    new_body = st.text_area("Contenido Markdown", value=body, height=400, key=f"body_{selected_rel}")
    
    if st.button("💾 Guardar Contenido", key=f"save_body_{selected_rel}"):
        current_frontmatter, _ = parse_markdown(selected_file.read_text(encoding="utf-8"))
        new_content = serialize_markdown(current_frontmatter, new_body)
        selected_file.write_text(new_content, encoding="utf-8")
        st.success("Contenido guardado")
        st.rerun()
    
    st.markdown("---")
    st.subheader("➕ Crear nuevo documento")
    
    with st.form("new_doc_form"):
        new_rel_path = st.text_input("Ruta relativa (ej: normativa/nuevo_doc.md)", placeholder="carpeta/archivo.md")
        new_title = st.text_input("Título")
        new_categoria = st.selectbox("Categoría", ["Normativa", "Procedimientos", "Plantillas", "General", "Otros"])
        new_id = st.text_input("ID único", placeholder="doc_nuevo_001")
        
        if st.form_submit_button("Crear documento"):
            if not new_rel_path or not new_rel_path.endswith(".md"):
                st.error("La ruta debe terminar en .md")
            elif not new_title or not new_id:
                st.error("Título e ID son obligatorios")
            else:
                new_path = DATA_DIR / new_rel_path
                if new_path.exists():
                    st.error("El archivo ya existe")
                else:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    frontmatter = {
                        "id": new_id,
                        "title": new_title,
                        "categoria": new_categoria,
                        "autor": "Usuario SGD",
                        "creado": date.today().isoformat(),
                        "tags": ["#sgd"],
                        "status": "borrador"
                    }
                    body = f"# {new_title}\n\nContenido del documento..."
                    content = serialize_markdown(frontmatter, body)
                    new_path.write_text(content, encoding="utf-8")
                    st.success(f"Documento creado: {new_rel_path}")
                    st.rerun()