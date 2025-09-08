import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

def create_provision_dashboard(df_provision):
    """
    Crea el dashboard de provisionamiento con drill-down jerárquico
    """
    st.markdown('<h2 class="module-header">🏗️ Análisis de Provisionamiento</h2>', unsafe_allow_html=True)
    
    if df_provision is None:
        st.warning("⚠️ No se ha cargado el archivo de Provisionamiento")
        st.info("Sube un archivo CSV desde el panel lateral para ver el análisis.")
        return
    
    # === FORMATEAR DATASET ===
    df_formatted = df_provision.copy()
    
    # Formatear columnas geográficas a mayúsculas
    geo_columns = ['Departamento', 'Provincia', 'Distrito', 'Localidad']
    for col in geo_columns:
        if col in df_formatted.columns:
            df_formatted[col] = df_formatted[col].astype(str).str.upper()
    
    # Formatear fecha
    if 'Fecha_Activacion' in df_formatted.columns:
        try:
            # Convertir fecha desde formato "10/04/2024" a datetime y luego formatear
            df_formatted['Fecha_Activacion_Clean'] = pd.to_datetime(df_formatted['Fecha_Activacion'], format='%d/%m/%Y', errors='coerce')
            df_formatted['Fecha_Activacion'] = df_formatted['Fecha_Activacion_Clean'].dt.strftime('%d/%m/%Y')
            df_formatted = df_formatted.drop('Fecha_Activacion_Clean', axis=1)
        except:
            # Si falla, mantener formato original
            pass
    
    # Usar dataset formateado de aquí en adelante
    df_provision = df_formatted
    
    # Verificar columnas jerárquicas
    hierarchy_columns = ['Departamento', 'Provincia', 'Distrito', 'Localidad']
    available_hierarchy = [col for col in hierarchy_columns if col in df_provision.columns]
    
    if len(available_hierarchy) < 2:
        st.error("❌ Se necesitan al menos 2 niveles jerárquicos (Departamento, Provincia, Distrito, Localidad)")
        return
    
    # === MÉTRICAS PRINCIPALES (CORREGIDAS PARA JERARQUÍA) ===
    st.subheader("📊 Resumen General")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("🏗️ Total Sites", f"{len(df_provision):,}")
    
    with col2:
        if "Departamento" in df_provision.columns:
            dept_count = df_provision["Departamento"].nunique()
            st.metric("🌍 Departamentos", dept_count)
        else:
            st.metric("🌍 Departamentos", "N/A")
    
    with col3:
        if "Provincia" in df_provision.columns and "Departamento" in df_provision.columns:
            # Contar provincias únicas considerando la jerarquía
            prov_count = df_provision.groupby(["Departamento", "Provincia"]).size().shape[0]
            st.metric("🏛️ Provincias", prov_count)
        elif "Provincia" in df_provision.columns:
            st.metric("🏛️ Provincias", df_provision["Provincia"].nunique())
        else:
            st.metric("🏛️ Provincias", "N/A")
    
    with col4:
        if "Distrito" in df_provision.columns and "Provincia" in df_provision.columns and "Departamento" in df_provision.columns:
            # Contar distritos únicos considerando la jerarquía completa
            dist_count = df_provision.groupby(["Departamento", "Provincia", "Distrito"]).size().shape[0]
            st.metric("🏘️ Distritos", dist_count)
        elif "Distrito" in df_provision.columns:
            st.metric("🏘️ Distritos", df_provision["Distrito"].nunique())
        else:
            st.metric("🏘️ Distritos", "N/A")
    
    with col5:
        if "Localidad" in df_provision.columns and "Distrito" in df_provision.columns and "Provincia" in df_provision.columns and "Departamento" in df_provision.columns:
            # Contar localidades únicas considerando la jerarquía completa
            loc_count = df_provision.groupby(["Departamento", "Provincia", "Distrito", "Localidad"]).size().shape[0]
            st.metric("📍 Localidades", loc_count)
        elif "Localidad" in df_provision.columns:
            st.metric("📍 Localidades", df_provision["Localidad"].nunique())
        else:
            st.metric("📍 Localidades", "N/A")
    
    st.divider()
    
    # === DRILL-DOWN JERÁRQUICO ===
    st.subheader("🔍 Explorador Jerárquico")
    st.caption("Navega nivel por nivel: Departamento → Provincia → Distrito → Localidad → Sites")
    
    # Variables de estado para el drill-down
    if "provision_drill_state" not in st.session_state:
        st.session_state.provision_drill_state = {
            "current_level": 0,
            "selected_departamento": None,
            "selected_provincia": None,
            "selected_distrito": None,
            "selected_localidad": None
        }
    
    # Función para resetear niveles inferiores
    def reset_lower_levels(from_level):
        if from_level <= 1:
            st.session_state.provision_drill_state["selected_provincia"] = None
        if from_level <= 2:
            st.session_state.provision_drill_state["selected_distrito"] = None
        if from_level <= 3:
            st.session_state.provision_drill_state["selected_localidad"] = None
    
    # NIVEL 1: DEPARTAMENTOS
    st.markdown("### 🌍 **Nivel 1: Departamentos**")
    
    # Calcular stats por departamento (CORREGIDO)
    if "Departamento" in df_provision.columns:
        dept_stats = df_provision.groupby("Departamento").agg({
            df_provision.columns[0]: 'count'  # Count de registros (sites)
        }).round(0)
        dept_stats.columns = ['Sites']
        
        # Calcular provincias y distritos únicos por departamento (considerando jerarquía)
        if "Provincia" in df_provision.columns:
            prov_por_dept = df_provision.groupby("Departamento")["Provincia"].nunique().reset_index()
            prov_por_dept.columns = ["Departamento", "Provincias"]
            dept_stats = dept_stats.reset_index().merge(prov_por_dept, on="Departamento")
        
        if "Distrito" in df_provision.columns and "Provincia" in df_provision.columns:
            # Contar distritos únicos por departamento considerando provincia
            dist_por_dept = df_provision.groupby("Departamento").apply(
                lambda x: x.groupby(["Provincia", "Distrito"]).size().shape[0]
            ).reset_index()
            dist_por_dept.columns = ["Departamento", "Distritos"]
            dept_stats = dept_stats.merge(dist_por_dept, on="Departamento")
        
        dept_stats = dept_stats.sort_values('Sites', ascending=False).reset_index(drop=True)
        
        # Selector de departamento
        dept_col1, dept_col2 = st.columns([1, 2])
        
        with dept_col1:
            departamentos = ["Seleccionar..."] + sorted(df_provision["Departamento"].unique().tolist())
            selected_dept = st.selectbox(
                "🎯 Seleccionar Departamento:",
                departamentos,
                index=0,
                key="provision_departamento"
            )
            
            if selected_dept != "Seleccionar...":
                if st.session_state.provision_drill_state["selected_departamento"] != selected_dept:
                    st.session_state.provision_drill_state["selected_departamento"] = selected_dept
                    reset_lower_levels(1)
        
        with dept_col2:
            # Gráfico de departamentos
            fig_dept = px.bar(
                dept_stats.head(10),
                x='Sites',
                y='Departamento',
                orientation='h',
                title="Top 10 Departamentos por Número de Sites",
                color='Sites',
                color_continuous_scale='viridis'
            )
            fig_dept.update_layout(height=400)
            st.plotly_chart(fig_dept, use_container_width=True)
    
    # NIVEL 2: PROVINCIAS (si hay departamento seleccionado)
    if st.session_state.provision_drill_state["selected_departamento"]:
        st.markdown("### 🏛️ **Nivel 2: Provincias**")
        st.info(f"📍 Departamento seleccionado: **{st.session_state.provision_drill_state['selected_departamento']}**")
        
        # Filtrar por departamento
        df_dept = df_provision[df_provision["Departamento"] == st.session_state.provision_drill_state["selected_departamento"]]
        
        if "Provincia" in df_dept.columns:
            # Stats por provincia (CORREGIDO)
            prov_stats = df_dept.groupby("Provincia").agg({
                df_dept.columns[0]: 'count'
            }).round(0)
            prov_stats.columns = ['Sites']
            
            # Calcular distritos únicos por provincia en este departamento
            if "Distrito" in df_dept.columns:
                dist_por_prov = df_dept.groupby("Provincia")["Distrito"].nunique().reset_index()
                dist_por_prov.columns = ["Provincia", "Distritos"]
                prov_stats = prov_stats.reset_index().merge(dist_por_prov, on="Provincia")
            
            prov_stats = prov_stats.sort_values('Sites', ascending=False).reset_index(drop=True)
            
            prov_col1, prov_col2 = st.columns([1, 2])
            
            with prov_col1:
                provincias = ["Seleccionar..."] + sorted(df_dept["Provincia"].unique().tolist())
                selected_prov = st.selectbox(
                    "🎯 Seleccionar Provincia:",
                    provincias,
                    index=0,
                    key="provision_provincia"
                )
                
                if selected_prov != "Seleccionar...":
                    if st.session_state.provision_drill_state["selected_provincia"] != selected_prov:
                        st.session_state.provision_drill_state["selected_provincia"] = selected_prov
                        reset_lower_levels(2)
                
                # Métricas de la provincia
                if selected_prov != "Seleccionar...":
                    prov_data = prov_stats[prov_stats["Provincia"] == selected_prov]
                    if len(prov_data) > 0:
                        st.metric("Sites en Provincia", int(prov_data["Sites"].iloc[0]))
                        if "Distritos" in prov_data.columns:
                            st.metric("Distritos", int(prov_data["Distritos"].iloc[0]))
            
            with prov_col2:
                # Gráfico de provincias
                fig_prov = px.bar(
                    prov_stats,
                    x='Sites',
                    y='Provincia',
                    orientation='h',
                    title=f"Provincias en {st.session_state.provision_drill_state['selected_departamento']}",
                    color='Sites',
                    color_continuous_scale='plasma'
                )
                fig_prov.update_layout(height=400)
                st.plotly_chart(fig_prov, use_container_width=True)
    
    # NIVEL 3: DISTRITOS (si hay provincia seleccionada)
    if st.session_state.provision_drill_state["selected_provincia"]:
        st.markdown("### 🏘️ **Nivel 3: Distritos**")
        st.info(f"📍 Ruta: **{st.session_state.provision_drill_state['selected_departamento']}** → **{st.session_state.provision_drill_state['selected_provincia']}**")
        
        # Filtrar por departamento y provincia
        df_prov = df_provision[
            (df_provision["Departamento"] == st.session_state.provision_drill_state["selected_departamento"]) &
            (df_provision["Provincia"] == st.session_state.provision_drill_state["selected_provincia"])
        ]
        
        if "Distrito" in df_prov.columns:
            # Stats por distrito (CORREGIDO)
            dist_stats = df_prov.groupby("Distrito").agg({
                df_prov.columns[0]: 'count'
            }).round(0)
            dist_stats.columns = ['Sites']
            
            # Calcular localidades únicas por distrito en esta provincia
            if "Localidad" in df_prov.columns:
                loc_por_dist = df_prov.groupby("Distrito")["Localidad"].nunique().reset_index()
                loc_por_dist.columns = ["Distrito", "Localidades"]
                dist_stats = dist_stats.reset_index().merge(loc_por_dist, on="Distrito")
            
            dist_stats = dist_stats.sort_values('Sites', ascending=False).reset_index(drop=True)
            
            dist_col1, dist_col2 = st.columns([1, 2])
            
            with dist_col1:
                distritos = ["Seleccionar..."] + sorted(df_prov["Distrito"].unique().tolist())
                selected_dist = st.selectbox(
                    "🎯 Seleccionar Distrito:",
                    distritos,
                    index=0,
                    key="provision_distrito"
                )
                
                if selected_dist != "Seleccionar...":
                    if st.session_state.provision_drill_state["selected_distrito"] != selected_dist:
                        st.session_state.provision_drill_state["selected_distrito"] = selected_dist
                        reset_lower_levels(3)
                
                # Métricas del distrito
                if selected_dist != "Seleccionar...":
                    dist_data = dist_stats[dist_stats["Distrito"] == selected_dist]
                    if len(dist_data) > 0:
                        st.metric("Sites en Distrito", int(dist_data["Sites"].iloc[0]))
                        if "Localidades" in dist_data.columns:
                            st.metric("Localidades", int(dist_data["Localidades"].iloc[0]))
            
            with dist_col2:
                # Gráfico de distritos
                fig_dist = px.bar(
                    dist_stats,
                    x='Sites',
                    y='Distrito',
                    orientation='h',
                    title=f"Distritos en {st.session_state.provision_drill_state['selected_provincia']}",
                    color='Sites',
                    color_continuous_scale='cividis'
                )
                fig_dist.update_layout(height=400)
                st.plotly_chart(fig_dist, use_container_width=True)
    
    # NIVEL 4: SITES (si hay distrito seleccionado)
    if st.session_state.provision_drill_state["selected_distrito"]:
        st.markdown("### 📍 **Nivel 4: Sites**")
        st.info(f"📍 Ruta: **{st.session_state.provision_drill_state['selected_departamento']}** → **{st.session_state.provision_drill_state['selected_provincia']}** → **{st.session_state.provision_drill_state['selected_distrito']}**")
        
        # Filtrar hasta distrito
        df_dist = df_provision[
            (df_provision["Departamento"] == st.session_state.provision_drill_state["selected_departamento"]) &
            (df_provision["Provincia"] == st.session_state.provision_drill_state["selected_provincia"]) &
            (df_provision["Distrito"] == st.session_state.provision_drill_state["selected_distrito"])
        ]
        
        # === TABLA DE SITES ===
        st.subheader("🗼 Sites en el Distrito")
        
        # Mostrar tabla con todas las columnas
        st.dataframe(
            df_dist,
            use_container_width=True,
            hide_index=True
        )
    
    # Botón para resetear navegación
    st.divider()
    if st.button("🔄 Reiniciar Navegación", type="secondary"):
        st.session_state.provision_drill_state = {
            "current_level": 0,
            "selected_departamento": None,
            "selected_provincia": None,
            "selected_distrito": None,
            "selected_localidad": None
        }
        st.rerun()
    
    # Botón de descarga (datos filtrados según navegación)
    df_export = df_provision.copy()
    if st.session_state.provision_drill_state["selected_departamento"]:
        df_export = df_export[df_export["Departamento"] == st.session_state.provision_drill_state["selected_departamento"]]
        if st.session_state.provision_drill_state["selected_provincia"]:
            df_export = df_export[df_export["Provincia"] == st.session_state.provision_drill_state["selected_provincia"]]
            if st.session_state.provision_drill_state["selected_distrito"]:
                df_export = df_export[df_export["Distrito"] == st.session_state.provision_drill_state["selected_distrito"]]
    
    csv = df_export.to_csv(index=False)
    download_name = "provisionamiento"
    if st.session_state.provision_drill_state["selected_distrito"]:
        download_name += f"_{st.session_state.provision_drill_state['selected_distrito']}"
    elif st.session_state.provision_drill_state["selected_provincia"]:
        download_name += f"_{st.session_state.provision_drill_state['selected_provincia']}"
    elif st.session_state.provision_drill_state["selected_departamento"]:
        download_name += f"_{st.session_state.provision_drill_state['selected_departamento']}"
    
    st.download_button(
        label=f"📥 Descargar datos filtrados ({len(df_export)} registros)",
        data=csv,
        file_name=f"{download_name}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key="provision_download_filtered"
    )