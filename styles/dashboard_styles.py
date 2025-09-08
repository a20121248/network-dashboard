import streamlit as st

def get_dashboard_styles():
    return """
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
        
        /* Estilos adicionales para mejorar la apariencia */
        .metric-container {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #1f77b4;
            margin-bottom: 1rem;
        }
        
        .status-success {
            color: #28a745;
            font-weight: bold;
        }
        
        .status-error {
            color: #dc3545;
            font-weight: bold;
        }
        
        .status-warning {
            color: #ffc107;
            font-weight: bold;
        }
        
        /* Estilos para mapas */
        .map-container {
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
            margin: 1rem 0;
        }
        
        /* Estilos para filtros */
        .filter-section {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        /* Estilos para debug */
        .debug-info {
            background-color: #f1f3f4;
            border-left: 4px solid #6c757d;
            padding: 0.75rem;
            margin: 0.5rem 0;
            font-family: monospace;
            font-size: 0.9rem;
        }
    </style>
    """

def apply_dashboard_styles():
    st.markdown(get_dashboard_styles(), unsafe_allow_html=True)