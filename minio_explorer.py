"""
AeroTrack Travel — MinIO Admin Explorer v3
Detecta collectionName dentro de los registros y lo usa como colección virtual.
Ejecutar: python -m streamlit run minio_explorer.py
Requiere:  pip install streamlit minio pandas
"""
import json, pandas as pd, streamlit as st
from minio import Minio
from minio.error import S3Error

st.set_page_config(
    page_title="MinIO Admin · AeroTrack",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background:#1e293b; min-width:250px; }
[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
.grp-label {
    font-size:10px; font-weight:700; letter-spacing:.1em;
    text-transform:uppercase; color:#64748b !important;
    padding:12px 12px 2px 12px; margin:0; display:block;
}
div[data-testid="stButton"] > button {
    background:transparent; border:none; text-align:left;
    width:100%; padding:4px 12px; border-radius:5px;
    font-size:12.5px; color:#cbd5e1 !important;
}
div[data-testid="stButton"] > button:hover { background:#334155 !important; }
.coll-header {
    display:flex; align-items:center; gap:10px;
    padding:0 0 12px 0; border-bottom:1px solid #e2e8f0; margin-bottom:14px;
}
.coll-header h2 { margin:0; font-size:1.2rem; color:#1e293b; }
.badge { border-radius:12px; padding:2px 10px; font-size:12px; font-weight:600; }
.op  { background:#dcfce7; color:#166534; }
.cat { background:#fff7ed; color:#c2410c; }
.dim { background:#f3e8ff; color:#7e22ce; }
.cnt { font-size:11px; color:#64748b; margin-left:auto; }
</style>
""", unsafe_allow_html=True)

BUCKETS = [
    ("aerotrack-travel-operational", "🟢 OPERACIONAL",  "op"),
    ("aerotrack-travel-catalog",     "🟠 CATÁLOGO APIs","cat"),
    ("aerotrack-travel-dims",        "🟣 DIMS BTS/FAA", "dim"),
]

# ── Cliente ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client(host, port, ak, sk):
    return Minio(f"{host}:{port}", access_key=ak, secret_key=sk, secure=False)

# ── Carga todos los registros de un bucket (una sola vez, cacheado) ───────────
@st.cache_data(ttl=120, show_spinner=False)
def load_all_records(_client, bucket, max_objs=5000):
    records = []
    try:
        for obj in _client.list_objects(bucket, recursive=True):
            if obj.is_dir: continue
            name = obj.object_name
            try:
                if name.endswith(".json"):
                    r = _client.get_object(bucket, name)
                    d = json.loads(r.read())
                    d["_path"] = name
                    records.append(d)
                elif name.endswith(".ndjson"):
                    r = _client.get_object(bucket, name)
                    src = name.split("/")[-1].replace(".ndjson","")
                    for line in r.read().decode("utf-8").strip().split("\n"):
                        if line.strip():
                            d = json.loads(line)
                            d["_path"]    = name
                            d["_src"]     = src
                            records.append(d)
                elif name.endswith(".parquet"):
                    records.append({
                        "_path": name,
                        "_note": "Parquet binario — solo metadatos",
                        "_src":  name.split("/")[-1].replace(".parquet",""),
                    })
            except Exception:
                pass
            if len(records) >= max_objs: break
    except S3Error as e:
        st.sidebar.error(f"Error: {e}")
    return records

def get_collection_from_path(path):
    """
    Extrae el nombre de colección desde el path del objeto en MinIO.
    Ejemplos:
      operacional/pasajeros/abc123.json   → "pasajeros"
      operacional/abc123.json             → "(raíz)"
      catalogo/vuelos_catalogo.ndjson     → "vuelos_catalogo"
      dim_aeropuerto.parquet              → "dim_aeropuerto"
    """
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    if len(parts) >= 3:
        # operacional / coleccion / id.json  → parts[1]
        return parts[-2]
    elif len(parts) == 2:
        # prefijo / archivo.ext → nombre del archivo sin extensión
        nombre = parts[-1]
        for ext in [".ndjson", ".parquet", ".json"]:
            nombre = nombre.replace(ext, "")
        return nombre
    else:
        # archivo en raíz
        nombre = parts[0] if parts else "(raíz)"
        for ext in [".ndjson", ".parquet", ".json"]:
            nombre = nombre.replace(ext, "")
        return nombre

def get_virtual_collections(records):
    """
    Agrupa registros por colección usando el PATH del objeto como fuente principal.
    El path refleja la estructura real de carpetas en MinIO.
    """
    colls = {}
    for r in records:
        path = r.get("_path", "")
        coll = get_collection_from_path(path)
        if coll not in colls:
            colls[coll] = []
        colls[coll].append(r)
    return colls, "_path"

# ── Estado ────────────────────────────────────────────────────────────────────
for k, v in {
    "connected": False, "client": None,
    "cache": {},          # {bucket: {coll_name: [records]}}
    "coll_field": {},     # {bucket: field_name}
    "sel_bucket": None, "sel_coll": None,
    "page": 0, "search": "",
}.items():
    if k not in st.session_state: st.session_state[k] = v

# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        "<div style='padding:14px 12px 6px'>"
        "<b style='font-size:1rem'>🗄️ MinIO Admin</b><br>"
        "<span style='font-size:11px;color:#94a3b8!important'>AeroTrack Travel</span>"
        "</div>", unsafe_allow_html=True
    )

    with st.expander("⚙️ Conexión", expanded=not st.session_state.connected):
        host = st.text_input("Host",        "localhost", key="h")
        port = st.number_input("Puerto",    9002,        key="p")
        ak   = st.text_input("Access key",  "admin",     key="ak")
        sk   = st.text_input("Secret key",  "admin1234", key="sk", type="password")
        if st.button("Conectar", use_container_width=True):
            try:
                c = get_client(host, int(port), ak, sk)
                c.list_buckets()
                st.session_state.update({
                    "client": c, "connected": True,
                    "cache": {}, "coll_field": {},
                    "sel_bucket": None, "sel_coll": None,
                })
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if not st.session_state.connected:
        st.info("Configura la conexión."); st.stop()

    st.markdown(
        "<div style='padding:2px 12px 6px;font-size:12px;color:#4ade80!important'>"
        "● Conectado</div>", unsafe_allow_html=True
    )

    client = st.session_state.client

    # ── Colecciones por bucket ─────────────────────────────────────────────
    for bucket, label, badge in BUCKETS:
        st.markdown(f"<span class='grp-label'>{label}</span>",
                    unsafe_allow_html=True)

        # Cargar bucket si no está en caché
        if bucket not in st.session_state.cache:
            with st.spinner(f"Cargando {label}…"):
                all_recs = load_all_records(client, bucket)
            colls, cf = get_virtual_collections(all_recs)
            st.session_state.cache[bucket]      = colls
            st.session_state.coll_field[bucket] = cf

        colls = st.session_state.cache[bucket]

        if not colls:
            st.markdown(
                "<div style='padding:2px 12px 6px;font-size:12px;"
                "color:#475569!important'>Sin datos</div>",
                unsafe_allow_html=True
            )
        else:
            for coll_name in sorted(colls.keys()):
                n      = len(colls[coll_name])
                active = (st.session_state.sel_bucket == bucket and
                          st.session_state.sel_coll   == coll_name)
                prefix = "▌ " if active else "   "
                label_btn = f"{prefix}{coll_name}  ({n:,})"
                if st.button(label_btn, key=f"{bucket}__{coll_name}",
                             use_container_width=True):
                    st.session_state.update({
                        "sel_bucket": bucket,
                        "sel_coll":   coll_name,
                        "page":       0,
                        "search":     "",
                    })
                    st.rerun()

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Botón para limpiar caché y recargar todo
    st.divider()
    if st.button("🔄 Recargar todo", use_container_width=True):
        st.cache_data.clear()
        st.session_state.cache     = {}
        st.session_state.coll_field = {}
        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# ÁREA PRINCIPAL
# ════════════════════════════════════════════════════════════════════════════
sel_bucket = st.session_state.sel_bucket
sel_coll   = st.session_state.sel_coll

if sel_bucket is None:
    st.markdown("## 🗄️ MinIO Admin — AeroTrack Travel")
    st.info("Selecciona una colección en el sidebar para ver sus registros.")
    st.stop()

colls    = st.session_state.cache.get(sel_bucket, {})
records  = colls.get(sel_coll, [])
bkt_info = next((b for b in BUCKETS if b[0] == sel_bucket), None)
_, label_b, badge_cls = bkt_info

# ── Header ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="coll-header">
  <h2>{sel_coll}</h2>
  <span class="badge {badge_cls}">{label_b}</span>
  <span class="cnt">{len(records):,} registros</span>
</div>
""", unsafe_allow_html=True)

# ── Toolbar ───────────────────────────────────────────────────────────────
t1, t2, t3 = st.columns([4, 1, 1])
with t1:
    search = st.text_input("🔍", value=st.session_state.search,
                            placeholder="Filtrar en todas las columnas…",
                            label_visibility="collapsed")
    st.session_state.search = search
with t2:
    page_size = st.selectbox("Filas/pág", [25, 50, 100, 200],
                              index=1, label_visibility="collapsed")
with t3:
    if st.button("🔄 Recargar", use_container_width=True):
        st.cache_data.clear()
        st.session_state.cache     = {}
        st.session_state.coll_field = {}
        st.rerun()

# ── DataFrame ─────────────────────────────────────────────────────────────
if not records:
    st.info("Colección vacía."); st.stop()

df = pd.DataFrame(records)

# Limpiar columnas internas de display
internal = ["_path", "_src", "_note"]
cols_show = [c for c in df.columns if c not in internal]
# id primero
cols_pri  = [c for c in ["id","ID","_id","uuid"] if c in cols_show]
cols_rest = [c for c in cols_show if c not in cols_pri]
df_clean  = df[cols_pri + cols_rest]

# Filtro
if search:
    mask = df_clean.apply(
        lambda col: col.astype(str).str.contains(search, case=False, na=False)
    ).any(axis=1)
    df_clean = df_clean[mask]

total       = len(df_clean)
page        = min(st.session_state.page,
                  max(0, (total - 1) // page_size))
df_page     = df_clean.iloc[page * page_size : (page+1) * page_size]
total_pages = max(1, (total + page_size - 1) // page_size)

st.dataframe(df_page, use_container_width=True, hide_index=True, height=430)

# ── Paginación ────────────────────────────────────────────────────────────
pc1,pc2,pc3,pc4,pc5 = st.columns([1,1,3,1,1])
with pc1:
    if st.button("⏮", disabled=page==0, key="pf"):
        st.session_state.page=0; st.rerun()
with pc2:
    if st.button("◀", disabled=page==0, key="pp"):
        st.session_state.page=page-1; st.rerun()
with pc3:
    st.markdown(
        f"<div style='text-align:center;padding-top:7px;color:#64748b;font-size:13px'>"
        f"Página {page+1} / {total_pages}  ({total:,} registros)</div>",
        unsafe_allow_html=True
    )
with pc4:
    if st.button("▶", disabled=page>=total_pages-1, key="pn"):
        st.session_state.page=page+1; st.rerun()
with pc5:
    if st.button("⏭", disabled=page>=total_pages-1, key="pl"):
        st.session_state.page=total_pages-1; st.rerun()

# ── Detalle de registro ───────────────────────────────────────────────────
st.divider()
st.markdown("#### Detalle de registro")

id_cols = [c for c in ["id","ID","_id","uuid"] if c in df_page.columns]
if id_cols:
    id_col  = id_cols[0]
    opciones = ["— elige —"] + df_page[id_col].astype(str).tolist()
    sel_id  = st.selectbox(f"Seleccionar por `{id_col}`", opciones)
    if sel_id != "— elige —":
        row = df[df[id_col].astype(str) == sel_id]
        if not row.empty:
            rec = {k: v for k, v in row.iloc[0].to_dict().items()
                   if k not in internal}
            simples   = {k: v for k, v in rec.items()
                         if isinstance(v, (str, int, float, bool, type(None)))}
            complejos = {k: v for k, v in rec.items() if k not in simples}
            if simples:
                for i in range(0, len(simples), 4):
                    items = list(simples.items())[i:i+4]
                    cols  = st.columns(4)
                    for j,(k,v) in enumerate(items):
                        cols[j].markdown(
                            f"<small style='color:#94a3b8;font-size:11px'>{k}</small>"
                            f"<br><span style='font-size:13px'>{v}</span>",
                            unsafe_allow_html=True
                        )
                st.markdown("")
            if complejos:
                with st.expander("Campos anidados"):
                    st.json(complejos)
            with st.expander("JSON completo"):
                st.json(rec)
else:
    idx = st.number_input("Índice", 0, max(0, len(df_page)-1), 0)
    rec = {k: v for k, v in df_page.iloc[int(idx)].to_dict().items()
           if k not in internal}
    st.json(rec)
