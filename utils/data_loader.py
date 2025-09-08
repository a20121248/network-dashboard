import streamlit as st
import pandas as pd

def initialize_session_state():
    """Inicializa el estado de la sesión con todos los datasets"""
    if "datasets" not in st.session_state:
        st.session_state["datasets"] = {
            "Averias": None,
            "Desempeño": None,
            "Configuration": None,
            "Provision": None,
            "Disponibilidad": None,
            "Calidad": None,
            "Proyectos": None
        }

def detect_dataset_type(filename: str) -> str:
    """Detecta el tipo de dataset basado en el nombre del archivo"""
    name = filename.lower()
    
    detection_rules = {
        "Averias": ["averia", "alarm", "fault"],
        "Desempeño": ["desempe", "performance", "kpi"],
        "Configuration": ["config", "configuracion"],
        "Provision": ["provision", "provisi"],
        "Disponibilidad": ["dispon", "availability"],
        "Calidad": ["calidad", "quality"],
        "Proyectos": ["proyecto", "project", "site"]
    }
    
    for dataset_type, keywords in detection_rules.items():
        if any(keyword in name for keyword in keywords):
            return dataset_type
    
    return None

def clean_and_reorder_columns(df):
    """Función auxiliar para limpiar y reordenar columnas"""
    columns_lower = [col.lower() for col in df.columns]
    columns = list(df.columns)
    
    # Eliminar start_time.1 si existe
    if 'start_time.1' in columns_lower:
        start_time_1_idx = columns_lower.index('start_time.1')
        original_start_time_1_name = columns[start_time_1_idx]
        df = df.drop(original_start_time_1_name, axis=1)
        columns = list(df.columns)
        columns_lower = [col.lower() for col in df.columns]
    
    priority_columns = []
    
    # Buscar start_time
    if 'start_time' in columns_lower:
        start_time_idx = columns_lower.index('start_time')
        original_start_name = columns[start_time_idx]
        priority_columns.append(original_start_name)
        columns.remove(original_start_name)
    
    # Buscar end_time
    if 'end_time' in columns_lower:
        # Actualizar columns_lower después de remover start_time
        columns_lower = [col.lower() for col in columns]
        if 'end_time' in columns_lower:
            end_time_idx = columns_lower.index('end_time')
            original_end_name = columns[end_time_idx]
            priority_columns.append(original_end_name)
            columns.remove(original_end_name)
    
    new_column_order = priority_columns + columns
    return df[new_column_order]

def load_csv_file(file, separator=";"):
    """Carga un archivo CSV con manejo de errores y eliminación de columnas duplicadas"""    
    try:
        df = pd.read_csv(file, sep=separator, dtype=str, encoding='utf-8')
        print(df.columns)
        df = clean_and_reorder_columns(df)
        print(df.columns)
        return df, None
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(file, sep=separator, dtype=str, encoding='latin-1')
            df = clean_and_reorder_columns(df)
            return df, None
        except Exception as e:
            return None, f"Error de codificación: {str(e)}"
    except Exception as e:
        return None, f"Error al cargar archivo: {str(e)}"