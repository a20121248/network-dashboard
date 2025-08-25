# bitel_dashboard.py
import io
import zipfile
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

# --------------------------------------------
# CONFIG
# --------------------------------------------
st.set_page_config(page_title="Bitel Network Dashboard", layout="wide")
st.title("📡 Bitel Network Dashboard")
st.caption("Alarmas · Desempeño · Configuración · Provisionamiento · Disponibilidad · Calidad")

DATE_FMT = '%b %d, %Y @ %H:%M:%S.%f'  # Ej: "Aug 18, 2025 @ 06:00:00.000"

# --------------------------------------------
# HELPERS
# --------------------------------------------
@st.cache_data(show_spinner=False)
def read_semicolon_csv(file_like, force_numeric_cols=None, parse_dates=None, dayfirst=False):
    """
    Lee CSV separados por ';' con comillas dobles, interpreta miles=',' y decimal='.'.
    'force_numeric_cols' intenta coaccionar esas columnas a numeric.
    'parse_dates' aplica to_datetime con formato DATE_FMT cuando corresponda.
    """
    df = pd.read_csv(
        file_like,
        sep=';',
        quotechar='"',
        thousands=',',   # "14,956.687" -> 14956.687
        dtype=str        # leemos como str primero para limpiar
    )
    # Strip de espacios y normalización de nombres duplicados básicos
    df.columns = [c.strip() for c in df.columns]

    # Resolver duplicados de columnas de tiempo (p.ej., dos "start_time")
    # Si hay duplicados, pandas les añade '.1', '.2', etc.
    cols_lower = [c.lower() for c in df.columns]
    # Normalizar "End_time" -> "end_time"
    rename_map = {c: c.strip().replace(" ", "_") for c in df.columns}
    df.rename(columns=rename_map, inplace=True)

    # Parseo de fechas
    if parse_dates:
        for col in parse_dates:
            # Buscar la columna (puede venir como 'start_time' o 'start_time.1')
            candidates = [c for c in df.columns if c.lower() == col.lower() or c.lower().startswith(col.lower()+'.')]
            if not candidates:
                continue
            # Tomar la primera como "oficial"
            main_col = candidates[0]
            # Intentar parseo con formato conocido; si falla, usar dateutil
            def _parse_datetime(series):
                # Primero intento el formato específico
                dt = pd.to_datetime(series, format=DATE_FMT, errors='coerce')
                # Donde quedó NaT, intento sin formato (dateutil) como fallback
                if dt.isna().any():
                    dt2 = pd.to_datetime(series, errors='coerce', dayfirst=dayfirst)
                    dt = dt.fillna(dt2)
                return dt

            df[main_col] = _parse_datetime(df[main_col])

            # Si hay más candidatos, descartarlos o combinarlos si el principal está vacío
            for extra in candidates[1:]:
                # Rellenar vacíos desde columna extra
                mask = df[main_col].isna()
                if mask.any():
                    dt_extra = pd.to_datetime(df[extra], format=DATE_FMT, errors='coerce')
                    dt_extra2 = pd.to_datetime(df[extra], errors='coerce', dayfirst=dayfirst)
                    dt_extra = dt_extra.fillna(dt_extra2)
                    df.loc[mask, main_col] = dt_extra[mask]
                # Eliminar columna extra para evitar confusión
                if extra != main_col:
                    df.drop(columns=[extra], inplace=True)

            # Renombrar a nombre canónico en minúscula
            if main_col != col:
                df.rename(columns={main_col: col}, inplace=True)

    # Forzar numéricos
    if force_numeric_cols:
        for c in force_numeric_cols:
            if c in df.columns:
                df[c] = (df[c].astype(str)
                               .str.replace(' ', '', regex=False)
                               .str.replace(',', '', regex=False))  # quitar miles residuales si quedaron
                df[c] = pd.to_numeric(df[c], errors='coerce')

    # Trimear strings
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].str.strip()

    return df


def apply_global_date_filter(df, start_col='start_time', date_range=None):
    if df is None or start_col not in df.columns:
        return df
    if date_range and len(date_range) == 2 and not pd.isna(date_range[0]) and not pd.isna(date_range[1]):
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        m = (df[start_col] >= start_date) & (df[start_col] <= end_date + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1))
        return df.loc[m].copy()
    return df


def kpi_card_row(items):
    cols = st.columns(len(items))
    for col, (label, value, helptext) in zip(cols, items):
        col.metric(label, value)
        if helptext:
            col.caption(helptext)


def detect_slot_from_filename(name: str):
    """Devuelve a qué pestaña pertenece el archivo por su nombre."""
    n = name.lower()
    if n.startswith('1.') or 'averias' in n or 'alarm' in n:
        return "Alarmas"
    if n.startswith('2.') or 'desempe' in n:
        return "Desempeño"
    if n.startswith('3.') or 'config' in n:
        return "Configuración"
    if n.startswith('4.') or 'provision' in n:
        return "Provisionamiento"
    if n.startswith('5.') or 'dispon' in n:
        return "Disponibilidad"
    if n.startswith('6.') or 'calidad' in n or 'quality' in n:
        return "Calidad"
    return None


# --------------------------------------------
# SESSION INIT
# --------------------------------------------
if "data" not in st.session_state:
    st.session_state["data"] = {
        "Alarmas": None,
        "Desempeño": None,
        "Configuración": None,
        "Provisionamiento": None,
        "Disponibilidad": None,
        "Calidad": None,
    }

# --------------------------------------------
# SIDEBAR: LOADERS + GLOBAL FILTERS
# --------------------------------------------
with st.sidebar:
    st.header("⚙️ Datos & Filtros")

    # Toggle de carga múltiple
    multi_mode = st.toggle("Subir múltiples archivos a la vez", value=False, help="Acepta varios CSV o un ZIP con todos.")

    if multi_mode:
        files = st.file_uploader("Sube tus archivos (CSV o ZIP)", type=["csv", "zip"], accept_multiple_files=True)
        if files:
            for f in files:
                if f.name.lower().endswith(".zip"):
                    # Explorar ZIP
                    with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                        for member in z.infolist():
                            if member.filename.lower().endswith(".csv"):
                                with z.open(member) as csvf:
                                    slot = detect_slot_from_filename(member.filename)
                                    if slot:
                                        # Cargar según slot
                                        if slot == "Alarmas":
                                            st.session_state["data"][slot] = read_semicolon_csv(
                                                csvf,
                                                parse_dates=["start_time", "End_time", "end_time"],  # por si viene variación
                                            )
                                        elif slot == "Desempeño":
                                            st.session_state["data"][slot] = read_semicolon_csv(
                                                csvf,
                                                parse_dates=["start_time", "end_time"],
                                                force_numeric_cols=[
                                                    "dl_data_traffic_mb","ul_data_traffic_mb",
                                                    "enodeb_dl_tgput_mb","lte_dl_cell_tgput_mb","lte_ul_cell_tgput_mb",
                                                    "lte_tu_prb_dl","average_number_user","enodeb_ul_tgput_mb",
                                                    "latency","tcp_pckt_loss_ratio","voice_traffic"
                                                ]
                                            )
                                        elif slot == "Configuración":
                                            st.session_state["data"][slot] = read_semicolon_csv(
                                                csvf,
                                                force_numeric_cols=[
                                                    "Longitud","Latitud","TAC","TOTAL SECTOR","BW",
                                                    "Total PRB","Transmission Capacity (Mbps)","Total Batteries","Autonomy (h)"
                                                ]
                                            )
                                        elif slot == "Provisionamiento":
                                            st.session_state["data"][slot] = read_semicolon_csv(
                                                csvf,
                                                parse_dates=["Fecha_Activacion"],
                                                dayfirst=True
                                            )
                                        elif slot == "Disponibilidad":
                                            st.session_state["data"][slot] = read_semicolon_csv(
                                                csvf,
                                                parse_dates=["start_time"],
                                                force_numeric_cols=["cell_serv_time"]
                                            )
                                        elif slot == "Calidad":
                                            st.session_state["data"][slot] = read_semicolon_csv(
                                                csvf,
                                                parse_dates=["start_time"],
                                                force_numeric_cols=[
                                                    "lte_rrc_setup_suc","lte_rrc_attempt","fails_rrc_setup","lte_rrc_sr",
                                                    "init_e_rab_suc_setup","add_e_rab_suc_setup","add_e_rab_setup_att",
                                                    "init_e_rab_setup_att","lte_e_rab_sr","lte_call_drop",
                                                    "lte_call_attempt","lte_cdr"
                                                ]
                                            )
                else:
                    slot = detect_slot_from_filename(f.name)
                    if slot:
                        if slot == "Alarmas":
                            st.session_state["data"][slot] = read_semicolon_csv(
                                f, parse_dates=["start_time", "End_time", "end_time"]
                            )
                        elif slot == "Desempeño":
                            st.session_state["data"][slot] = read_semicolon_csv(
                                f,
                                parse_dates=["start_time", "end_time"],
                                force_numeric_cols=[
                                    "dl_data_traffic_mb","ul_data_traffic_mb",
                                    "enodeb_dl_tgput_mb","lte_dl_cell_tgput_mb","lte_ul_cell_tgput_mb",
                                    "lte_tu_prb_dl","average_number_user","enodeb_ul_tgput_mb",
                                    "latency","tcp_pckt_loss_ratio","voice_traffic"
                                ]
                            )
                        elif slot == "Configuración":
                            st.session_state["data"][slot] = read_semicolon_csv(
                                f,
                                force_numeric_cols=[
                                    "Longitud","Latitud","TAC","TOTAL SECTOR","BW",
                                    "Total PRB","Transmission Capacity (Mbps)","Total Batteries","Autonomy (h)"
                                ]
                            )
                        elif slot == "Provisionamiento":
                            st.session_state["data"][slot] = read_semicolon_csv(
                                f, parse_dates=["Fecha_Activacion"], dayfirst=True
                            )
                        elif slot == "Disponibilidad":
                            st.session_state["data"][slot] = read_semicolon_csv(
                                f, parse_dates=["start_time"], force_numeric_cols=["cell_serv_time"]
                            )
                        elif slot == "Calidad":
                            st.session_state["data"][slot] = read_semicolon_csv(
                                f,
                                parse_dates=["start_time"],
                                force_numeric_cols=[
                                    "lte_rrc_setup_suc","lte_rrc_attempt","fails_rrc_setup","lte_rrc_sr",
                                    "init_e_rab_suc_setup","add_e_rab_suc_setup","add_e_rab_setup_att",
                                    "init_e_rab_setup_att","lte_e_rab_sr","lte_call_drop",
                                    "lte_call_attempt","lte_cdr"
                                ]
                            )

    else:
        st.write("### Subir archivos individualmente")
        a1 = st.file_uploader("1) Alarmas", type=["csv"], key="u1")
        a2 = st.file_uploader("2) Desempeño", type=["csv"], key="u2")
        a3 = st.file_uploader("3) Configuración", type=["csv"], key="u3")
        a4 = st.file_uploader("4) Provisionamiento", type=["csv"], key="u4")
        a5 = st.file_uploader("5) Disponibilidad", type=["csv"], key="u5")
        a6 = st.file_uploader("6) Calidad", type=["csv"], key="u6")

        if a1:
            st.session_state["data"]["Alarmas"] = read_semicolon_csv(a1, parse_dates=["start_time", "End_time", "end_time"])
        if a2:
            st.session_state["data"]["Desempeño"] = read_semicolon_csv(
                a2,
                parse_dates=["start_time", "end_time"],
                force_numeric_cols=[
                    "dl_data_traffic_mb","ul_data_traffic_mb",
                    "enodeb_dl_tgput_mb","lte_dl_cell_tgput_mb","lte_ul_cell_tgput_mb",
                    "lte_tu_prb_dl","average_number_user","enodeb_ul_tgput_mb",
                    "latency","tcp_pckt_loss_ratio","voice_traffic"
                ]
            )
        if a3:
            st.session_state["data"]["Configuración"] = read_semicolon_csv(
                a3,
                force_numeric_cols=[
                    "Longitud","Latitud","TAC","TOTAL SECTOR","BW",
                    "Total PRB","Transmission Capacity (Mbps)","Total Batteries","Autonomy (h)"
                ]
            )
        if a4:
            st.session_state["data"]["Provisionamiento"] = read_semicolon_csv(a4, parse_dates=["Fecha_Activacion"], dayfirst=True)
        if a5:
            st.session_state["data"]["Disponibilidad"] = read_semicolon_csv(a5, parse_dates=["start_time"], force_numeric_cols=["cell_serv_time"])
        if a6:
            st.session_state["data"]["Calidad"] = read_semicolon_csv(
                a6,
                parse_dates=["start_time"],
                force_numeric_cols=[
                    "lte_rrc_setup_suc","lte_rrc_attempt","fails_rrc_setup","lte_rrc_sr",
                    "init_e_rab_suc_setup","add_e_rab_suc_setup","add_e_rab_setup_att",
                    "init_e_rab_setup_att","lte_e_rab_sr","lte_call_drop",
                    "lte_call_attempt","lte_cdr"
                ]
            )

    st.divider()
    # GLOBAL DATE FILTER (si hay datos con start_time)
    # Encontrar min y max entre todos los DF con 'start_time'
    all_dates = []
    for key, df in st.session_state["data"].items():
        if df is not None and "start_time" in df.columns and pd.api.types.is_datetime64_any_dtype(df["start_time"]):
            all_dates.append(df["start_time"].min())
            all_dates.append(df["start_time"].max())
    if all_dates:
        global_min = pd.to_datetime(min(all_dates))
        global_max = pd.to_datetime(max(all_dates))
        st.write("### Filtros globales")
        apply_globally = st.checkbox("Aplicar a todas las pestañas", value=True)
        date_range = st.date_input(
            "Rango de fechas (global)",
            value=[global_min.date(), global_max.date()],
            min_value=global_min.date(),
            max_value=global_max.date(),
        )
    else:
        apply_globally = False
        date_range = None
        st.info("Carga archivos con `start_time` para activar el filtro global de fechas.")

    if st.button("🧹 Limpiar todo"):
        st.session_state.clear()
        st.rerun()

# --------------------------------------------
# TABS
# --------------------------------------------
tab_names = ["Alarmas", "Desempeño", "Configuración", "Provisionamiento", "Disponibilidad", "Calidad"]
tabs = st.tabs(tab_names)

# -------- TAB: ALARMAS --------
with tabs[0]:
    df = st.session_state["data"]["Alarmas"]
    st.header("🔔 Alarmas")
    if df is None:
        st.info("Sube el archivo de alarmas para visualizar esta sección.")
    else:
        # Filtro global
        dfv = apply_global_date_filter(df, start_col="start_time", date_range=date_range) if apply_globally else df.copy()

        # Filtros específicos
        c1, c2, c3 = st.columns(3)
        with c1:
            alarm_types = st.multiselect("Tipo de alarma", sorted(dfv["Alarm_Name"].dropna().unique().tolist()), default=None)
        with c2:
            statuses = st.multiselect("Estado", sorted(dfv["alarm_status"].dropna().unique().tolist()), default=None)
        with c3:
            site_sel = st.multiselect("Site", sorted(dfv["Site_Name"].dropna().unique().tolist()), default=None)

        m = pd.Series(True, index=dfv.index)
        if alarm_types: m &= dfv["Alarm_Name"].isin(alarm_types)
        if statuses:    m &= dfv["alarm_status"].isin(statuses)
        if site_sel:    m &= dfv["Site_Name"].isin(site_sel)
        dff = dfv.loc[m].copy()

        # Duración
        if "End_time" in dff.columns and "start_time" in dff.columns:
            dff["duration_min"] = (pd.to_datetime(dff["End_time"]) - pd.to_datetime(dff["start_time"])).dt.total_seconds() / 60

        total_alarms = len(dff)
        active_alarms = (dff["alarm_status"] == "active").sum() if "alarm_status" in dff.columns else np.nan
        mttr = dff.loc[(dff.get("duration_min").notna() if "duration_min" in dff else []), "duration_min"].mean() if "duration_min" in dff.columns else np.nan

        kpi_card_row([
            ("Total de alarmas", f"{total_alarms:,}", None),
            ("Activas", f"{active_alarms:,}" if pd.notna(active_alarms) else "N/A", None),
            ("MTTR (min)", f"{mttr:.1f}" if pd.notna(mttr) else "N/A", "Promedio de duración de alarmas resueltas"),
        ])

        # Alarms over time
        if "start_time" in dff.columns and not dff.empty:
            series = (dff
                      .assign(date=dff["start_time"].dt.floor("D"))
                      .groupby("date").size().reset_index(name="count"))
            fig = px.line(series, x="date", y="count", title="Alarmas por día")
            st.plotly_chart(fig, use_container_width=True)

        # Top sites
        if "Site_Name" in dff.columns and not dff.empty:
            top_sites = dff["Site_Name"].value_counts().head(10).reset_index()
            top_sites.columns = ["Site_Name", "count"]
            fig2 = px.bar(top_sites, x="Site_Name", y="count", title="Top 10 sitios con más alarmas")
            st.plotly_chart(fig2, use_container_width=True)

        # Alarm types dist
        if "Alarm_Name" in dff.columns and not dff.empty:
            dist = dff["Alarm_Name"].value_counts().reset_index()
            dist.columns = ["Alarm_Name", "count"]
            fig3 = px.bar(dist, x="Alarm_Name", y="count", title="Distribución por tipo de alarma")
            st.plotly_chart(fig3, use_container_width=True)

        st.expander("Ver tabla").dataframe(dff, use_container_width=True)

# -------- TAB: DESEMPEÑO --------
with tabs[1]:
    df = st.session_state["data"]["Desempeño"]
    st.header("📈 Desempeño")
    if df is None:
        st.info("Sube el archivo de desempeño para visualizar esta sección.")
    else:
        dfv = apply_global_date_filter(df, start_col="start_time", date_range=date_range) if apply_globally else df.copy()

        # Filtros
        c1, c2 = st.columns(2)
        with c1:
            sites = st.multiselect("Site", sorted(dfv.get("site_name", pd.Series(dtype=str)).dropna().unique().tolist()), default=None)
        with c2:
            kpi_pick = st.multiselect(
                "KPIs a graficar",
                [c for c in ["dl_data_traffic_mb","ul_data_traffic_mb","enodeb_dl_tgput_mb",
                             "enodeb_ul_tgput_mb","average_number_user","latency","tcp_pckt_loss_ratio","voice_traffic"]
                 if c in dfv.columns],
                default=["dl_data_traffic_mb","ul_data_traffic_mb"]
            )

        m = pd.Series(True, index=dfv.index)
        if sites and "site_name" in dfv.columns:
            m &= dfv["site_name"].isin(sites)
        dff = dfv.loc[m].copy()

        # KPIs
        sum_dl = dff.get("dl_data_traffic_mb", pd.Series(dtype=float)).astype(float).sum(skipna=True)
        sum_ul = dff.get("ul_data_traffic_mb", pd.Series(dtype=float)).astype(float).sum(skipna=True)
        avg_users = dff.get("average_number_user", pd.Series(dtype=float)).astype(float).mean(skipna=True)

        kpi_card_row([
            ("Tráfico DL (MB)", f"{sum_dl:,.0f}", None),
            ("Tráfico UL (MB)", f"{sum_ul:,.0f}", None),
            ("Usuarios promedio", f"{avg_users:,.1f}" if pd.notna(avg_users) else "N/A", None),
        ])

        # Serie temporal por KPI
        if "start_time" in dff.columns and not dff.empty and kpi_pick:
            g = (dff.assign(ts=dff["start_time"].dt.floor("H"))
                    .groupby("ts")[kpi_pick].sum(min_count=1).reset_index())
            fig = px.line(g, x="ts", y=kpi_pick, title="Serie temporal de KPIs seleccionados")
            st.plotly_chart(fig, use_container_width=True)

        # Top sitios por tráfico DL
        if "site_name" in dff.columns and "dl_data_traffic_mb" in dff.columns and not dff.empty:
            top = dff.groupby("site_name")["dl_data_traffic_mb"].sum(min_count=1).sort_values(ascending=False).head(10).reset_index()
            fig2 = px.bar(top, x="site_name", y="dl_data_traffic_mb", title="Top 10 sitios por tráfico DL (MB)")
            st.plotly_chart(fig2, use_container_width=True)

        st.expander("Ver tabla").dataframe(dff, use_container_width=True)

# -------- TAB: CONFIGURACIÓN --------
with tabs[2]:
    df = st.session_state["data"]["Configuración"]
    st.header("🧩 Configuración")
    if df is None:
        st.info("Sube el archivo de configuración para visualizar esta sección.")
    else:
        dff = df.copy()
        # KPIs
        total_sites = dff.get("SITE_NAME", pd.Series(dtype=str)).nunique()
        avg_aut = dff.get("Autonomy (h)", pd.Series(dtype=float)).astype(float).mean(skipna=True)

        kpi_card_row([
            ("Total sitios", f"{total_sites:,}", None),
            ("Autonomía promedio (h)", f"{avg_aut:.2f}" if pd.notna(avg_aut) else "N/A", None),
        ])

        # Distribución por tipo de energía
        if "Kind of Energy" in dff.columns:
            energy = dff["Kind of Energy"].value_counts().reset_index()
            energy.columns = ["Kind of Energy", "count"]
            fig = px.bar(energy, x="Kind of Energy", y="count", title="Distribución por tipo de energía")
            st.plotly_chart(fig, use_container_width=True)

        # Mapa (si hay Lat/Long)
        if {"Latitud", "Longitud"}.issubset(dff.columns):
            m = dff.dropna(subset=["Latitud", "Longitud"]).copy()
            m["Latitud"] = pd.to_numeric(m["Latitud"], errors='coerce')
            m["Longitud"] = pd.to_numeric(m["Longitud"], errors='coerce')
            m = m.dropna(subset=["Latitud", "Longitud"])
            if not m.empty:
                st.map(m.rename(columns={"Latitud": "lat", "Longitud": "lon"})[["lat","lon"]], zoom=5)
        st.expander("Ver tabla").dataframe(dff, use_container_width=True)

# -------- TAB: PROVISIONAMIENTO --------
with tabs[3]:
    df = st.session_state["data"]["Provisionamiento"]
    st.header("🧪 Provisionamiento")
    if df is None:
        st.info("Sube el archivo de provisionamiento para visualizar esta sección.")
    else:
        dff = df.copy()
        # Filtros
        cols = ["Departamento","Provincia","Distrito","Site_Name","Fecha_Activacion"]
        colmap = {c:c for c in cols if c in dff.columns}
        c1, c2, c3 = st.columns(3)
        with c1:
            deps = st.multiselect("Departamento", sorted(dff.get("Departamento", pd.Series(dtype=str)).dropna().unique().tolist()), default=None)
        with c2:
            provs = st.multiselect("Provincia", sorted(dff.get("Provincia", pd.Series(dtype=str)).dropna().unique().tolist()), default=None)
        with c3:
            dists = st.multiselect("Distrito", sorted(dff.get("Distrito", pd.Series(dtype=str)).dropna().unique().tolist()), default=None)

        m = pd.Series(True, index=dff.index)
        if deps:  m &= dff["Departamento"].isin(deps)
        if provs: m &= dff["Provincia"].isin(provs)
        if dists: m &= dff["Distrito"].isin(dists)
        dff = dff.loc[m].copy()

        # KPIs
        total_sites = dff.get("Site_Name", pd.Series(dtype=str)).nunique()
        kpi_card_row([
            ("Sitios provisionados", f"{total_sites:,}", None),
            ("Ventana de fechas", f"{dff['Fecha_Activacion'].min().date()} → {dff['Fecha_Activacion'].max().date()}" if "Fecha_Activacion" in dff.columns else "N/A", None),
        ])

        # Sitios por mes
        if "Fecha_Activacion" in dff.columns and not dff.empty:
            g = dff.assign(month=dff["Fecha_Activacion"].dt.to_period("M").dt.to_timestamp())
            g = g.groupby("month").size().reset_index(name="count")
            fig = px.bar(g, x="month", y="count", title="Sitios activados por mes")
            st.plotly_chart(fig, use_container_width=True)

        st.expander("Ver tabla").dataframe(dff, use_container_width=True)

# -------- TAB: DISPONIBILIDAD --------
with tabs[4]:
    df = st.session_state["data"]["Disponibilidad"]
    st.header("🟢 Disponibilidad")
    if df is None:
        st.info("Sube el archivo de disponibilidad para visualizar esta sección.")
    else:
        dfv = apply_global_date_filter(df, start_col="start_time", date_range=date_range) if apply_globally else df.copy()

        # Filtros
        c1, c2 = st.columns(2)
        with c1:
            deps = st.multiselect("Departamento", sorted(dfv.get("department", pd.Series(dtype=str)).dropna().unique().tolist()), default=None)
        with c2:
            dists = st.multiselect("Distrito", sorted(dfv.get("district", pd.Series(dtype=str)).dropna().unique().tolist()), default=None)

        m = pd.Series(True, index=dfv.index)
        if deps and "department" in dfv.columns: m &= dfv["department"].isin(deps)
        if dists and "district" in dfv.columns:   m &= dfv["district"].isin(dists)
        dff = dfv.loc[m].copy()

        # Calcular disponibilidad (%) asumiendo ventana de 24h = 86400s si es por día
        # Si son agregaciones de 6/12/24h puede requerir ajustar "target"
        target_secs = 86400
        if "cell_serv_time" in dff.columns:
            dff["availability_pct"] = (pd.to_numeric(dff["cell_serv_time"], errors='coerce') / target_secs) * 100

        avg_av = dff.get("availability_pct", pd.Series(dtype=float)).mean(skipna=True)
        kpi_card_row([
            ("Disponibilidad promedio", f"{avg_av:.2f} %" if pd.notna(avg_av) else "N/A", None),
            ("Registros", f"{len(dff):,}", None),
        ])

        # Ranking de sitios con menor disponibilidad
        if {"site", "availability_pct"}.issubset(dff.columns) and not dff.empty:
            rk = (dff.groupby("site")["availability_pct"]
                    .mean().sort_values().head(10).reset_index())
            fig = px.bar(rk, x="site", y="availability_pct", title="Top 10 sitios con menor disponibilidad (%)")
            st.plotly_chart(fig, use_container_width=True)

        st.expander("Ver tabla").dataframe(dff, use_container_width=True)

# -------- TAB: CALIDAD --------
with tabs[5]:
    df = st.session_state["data"]["Calidad"]
    st.header("🧪 Calidad")
    if df is None:
        st.info("Sube el archivo de calidad para visualizar esta sección.")
    else:
        dfv = apply_global_date_filter(df, start_col="start_time", date_range=date_range) if apply_globally else df.copy()

        # Filtros
        sites = st.multiselect("Site", sorted(dfv.get("site_name", pd.Series(dtype=str)).dropna().unique().tolist()), default=None)
        m = pd.Series(True, index=dfv.index)
        if sites and "site_name" in dfv.columns: m &= dfv["site_name"].isin(sites)
        dff = dfv.loc[m].copy()

        # KPIs principales
        sr_rrc = dff.get("lte_rrc_sr", pd.Series(dtype=float)).astype(float).mean(skipna=True)
        sr_erab = dff.get("lte_e_rab_sr", pd.Series(dtype=float)).astype(float).mean(skipna=True)
        cdr = dff.get("lte_cdr", pd.Series(dtype=float)).astype(float).mean(skipna=True)

        kpi_card_row([
            ("RRC SR (%)", f"{sr_rrc:.3f}" if pd.notna(sr_rrc) else "N/A", None),
            ("E-RAB SR (%)", f"{sr_erab:.3f}" if pd.notna(sr_erab) else "N/A", None),
            ("CDR", f"{cdr:.6f}" if pd.notna(cdr) else "N/A", None),
        ])

        # Dispersión RRC vs E-RAB
        if {"lte_rrc_sr","lte_e_rab_sr"}.issubset(dff.columns) and not dff.empty:
            fig = px.scatter(
                dff,
                x="lte_rrc_sr", y="lte_e_rab_sr",
                color=dff.get("site_name") if "site_name" in dff.columns else None,
                title="RRC SR vs E-RAB SR"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Evolución temporal (si aplica)
        if "start_time" in dff.columns and not dff.empty:
            series_cols = [c for c in ["lte_rrc_sr","lte_e_rab_sr","lte_cdr"] if c in dff.columns]
            if series_cols:
                g = (dff.assign(ts=dff["start_time"].dt.floor("H"))
                        .groupby("ts")[series_cols].mean().reset_index())
                fig2 = px.line(g, x="ts", y=series_cols, title="Evolución de KPIs de calidad")
                st.plotly_chart(fig2, use_container_width=True)

        st.expander("Ver tabla").dataframe(dff, use_container_width=True)
