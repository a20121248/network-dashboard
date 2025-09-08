import streamlit as st
import pandas as pd
from datetime import datetime
from utils.helpers import find_site_column

def create_configuration_dashboard(df_config):
    """
    Crea el dashboard básico de configuración
    """
    st.markdown('<h2 class="module-header">⚙️ Análisis de Configuración</h2>', unsafe_allow_html=True)
    
    if df_config is None:
        st.warning("⚠️ No se ha cargado el archivo de Configuración")
        st.info("Sube un archivo CSV desde el panel lateral para ver el análisis.")
        return
    
    # Métricas básicas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Configuraciones", f"{len(df_config):,}")
    
    with col2:
        site_col = find_site_column(df_config)
        if site_col:
            st.metric("Sites Configurados", df_config[site_col].nunique())
        else:
            st.metric("Sites Configurados", "N/A")
    
    with col3:
        st.metric("Columnas", len(df_config.columns))
    
    with col4:
        # Buscar alguna métrica específica de configuración
        if "Operation Band" in df_config.columns:
            st.metric("Bandas Operativas", df_config["Operation Band"].nunique())
        elif "TYPE BTS" in df_config.columns:
            st.metric("Tipos BTS", df_config["TYPE BTS"].nunique())
        else:
            st.metric("Estado", "✅ Cargado")
       
    # Conteos rápidos de valores únicos
    st.subheader("🔢 Conteos Básicos")
    
    # Buscar columnas categóricas importantes
    categorical_cols = []
    for col in df_config.columns:
        if any(keyword in col.lower() for keyword in ['type', 'band', 'transmission', 'energy', 'provider', 'battery']):
            categorical_cols.append(col)
    
    if categorical_cols:
        cols = st.columns(min(len(categorical_cols), 4))
        
        for i, cat_col in enumerate(categorical_cols[:4]):
            with cols[i]:
                unique_count = df_config[cat_col].nunique()
                st.metric(f"{cat_col}", f"{unique_count} únicos")
    
    # Vista previa de datos
    st.subheader("📋 Vista Previa de Datos")
    
    # Control de filas a mostrar
    max_rows = st.slider("Número de filas a mostrar:", 10, 500, 100, key="configuration_rows")
    
    # Mostrar datos
    st.dataframe(df_config.head(max_rows), use_container_width=True, hide_index=True)
    
    # Botón de descarga
    csv = df_config.to_csv(index=False)
    st.download_button(
        label="📥 Descargar datos de configuración (CSV)",
        data=csv,
        file_name=f"configuracion_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key="configuration_download_filtered"
    )