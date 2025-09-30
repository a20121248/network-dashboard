import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Importar módulos
from modules.averias import create_averias_dashboard
from modules.desempeño import create_performance_dashboard
from modules.configuration import create_configuration_dashboard
from modules.provision import create_provision_dashboard
from modules.disponibilidad import create_availability_dashboard
from modules.calidad import create_quality_dashboard
from utils.data_loader import initialize_session_state, detect_dataset_type, load_csv_file
from utils.helpers import get_dataset_info

# Configuración de la página
st.set_page_config(
    page_title="Network Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuración de estilo
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        color: #1f77b4;
    }
    .module-header {
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 1rem;
        color: #2e4057;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding: 10px 12px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f77b4;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # Inicializar estado
    initialize_session_state()
    
    # Título principal
    st.markdown('<h1 class="main-header">🌐 Dashboard - Network Management</h1>', unsafe_allow_html=True)
    
    # Sidebar para carga de archivos
    with st.sidebar:
        st.header("📁 Gestión de Archivos")
        
        uploaded_files = st.file_uploader(
            "Cargar archivos CSV",
            type=["csv"],
            accept_multiple_files=True,
            help="Selecciona múltiples archivos CSV para analizar"
        )
        
        if uploaded_files:
            st.subheader("📊 Estado de Carga")
            
            for file in uploaded_files:
                dataset_type = detect_dataset_type(file.name)
                
                if dataset_type:
                    df, error = load_csv_file(file)
                    
                    if error:
                        st.error(f"❌ {file.name}: {error}")
                    else:
                        st.session_state["datasets"][dataset_type] = df
                        st.success(f"✅ {dataset_type}: {len(df):,} registros")
                else:
                    st.warning(f"⚠️ {file.name}: Tipo no reconocido")
        
        st.divider()
        
        # Panel de estado de datasets
        st.subheader("📋 Estado de Datasets")
        
        for dataset_name, dataset in st.session_state["datasets"].items():
            status, rows, columns = get_dataset_info(dataset, dataset_name)
            
            if status == "Cargado":
                st.success(f"✅ {dataset_name}: {rows:,} registros")
            else:
                st.error(f"❌ {dataset_name}: No cargado")
        
        # Controles adicionales
        if st.button("🗑️ Limpiar todos los datos", type="secondary"):
            for key in st.session_state["datasets"]:
                st.session_state["datasets"][key] = None
            st.rerun()
    
    # Panel principal con tabs
    tab_names = ["🏠 Resumen", "📊 Averías", "🚀 Desempeño", "⚙️ Configuración", "🏗️ Provisión", "🟢 Disponibilidad", "⭐ Calidad"]
    tabs = st.tabs(tab_names)
    
    # --- TAB OVERVIEW ---
    with tabs[0]:
        st.markdown('<h2 class="module-header">🏠 Resumen general del sistema</h2>', unsafe_allow_html=True)
        
        # Métricas generales del sistema
        col1, col2, col3, col4 = st.columns(4)
        
        datasets_loaded = sum(1 for df in st.session_state["datasets"].values() if df is not None)
        total_records = sum(len(df) for df in st.session_state["datasets"].values() if df is not None)
        
        with col1:
            st.metric("📁 Datasets cargados", f"{datasets_loaded}/7")
        
        with col2:
            st.metric("📋 Total de registros", f"{total_records:,}")
        
        with col3:
            # Sites únicos (de múltiples fuentes)
            unique_sites = set()
            for dataset_name, df in st.session_state["datasets"].items():
                if df is not None:
                    site_cols = ["Site_Name", "site_name", "SITE_NAME", "site"]
                    for col in site_cols:
                        if col in df.columns:
                            unique_sites.update(df[col].unique())
                            break
            
            st.metric("🗼 Sites únicos", len(unique_sites))
        
        with col4:
            st.metric("🕐 Última actualización", datetime.now().strftime("%H:%M"))
        
        # Estado detallado de cada módulo
        st.subheader("📊 Estado Detallado por Módulo")
        
        modules_info = [
            ("Averias", "📊"),
            ("Desempeño", "🚀"),
            ("Configuration", "⚙️"),
            ("Provision", "🏗️"),
            ("Disponibilidad", "🟢"),
            ("Calidad", "⭐"),
            ("Proyectos", "🗺️")
        ]
        
        for i in range(0, len(modules_info), 3):
            cols = st.columns(3)
            
            for j, col in enumerate(cols):
                if i + j < len(modules_info):
                    module_name, icon = modules_info[i + j]
                    df = st.session_state["datasets"][module_name]
                    
                    with col:
                        if df is not None:
                            st.success(f"{icon} **{module_name}**")
                            st.write(f"📋 {len(df):,} registros")
                            st.write(f"📊 {len(df.columns)} columnas")
                        else:
                            st.error(f"{icon} **{module_name}**")
                            st.write("📋 No cargado")
    
    # --- TABS DE MÓDULOS ---
    
    # Tab Averías
    with tabs[1]:
        create_averias_dashboard(st.session_state["datasets"]["Averias"], st.session_state["datasets"]["Proyectos"])
    
    # Tab Desempeño
    with tabs[2]:
        create_performance_dashboard(st.session_state["datasets"]["Desempeño"])
    
    # Tab Configuration
    with tabs[3]:
        create_configuration_dashboard(st.session_state["datasets"]["Configuration"])
    
    # Tab Provision
    with tabs[4]:
        create_provision_dashboard(st.session_state["datasets"]["Provision"])
    
    # Tab Disponibilidad
    with tabs[5]:
        create_availability_dashboard(st.session_state["datasets"]["Disponibilidad"])
    
    # Tab Calidad
    with tabs[6]:
        create_quality_dashboard(st.session_state["datasets"]["Calidad"])

if __name__ == "__main__":
    main()
