import pandas as pd
from typing import List, Optional

def get_dataset_info(df, dataset_type):
    """Obtiene información básica del dataset"""
    if df is None or len(df) == 0:
        return "No cargado", 0, []
    
    return "Cargado", len(df), list(df.columns)

def find_site_column(df):
    """Encuentra la columna que contiene información de sites"""
    if df is None:
        return None
    
    site_columns = ["Site_Name", "site_name", "SITE_NAME", "site"]
    
    for col in site_columns:
        if col in df.columns:
            return col
    
    return None

def clean_date_format(date_str) -> Optional[str]:
    """
    Limpia el formato de fecha removiendo caracteres especiales
    
    Args:
        date_str: String de fecha a limpiar
        
    Returns:
        String de fecha limpio o None si es inválido
    """
    if pd.isna(date_str) or date_str == '' or str(date_str).lower() == 'nan':
        return None
    
    # Convertir "Aug 18, 2025 @ 06:00:00.000" a formato estándar
    cleaned = str(date_str).replace(' @ ', ' ').replace('.000', '')
    return cleaned.strip()

def clean_numeric_data(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    """
    Limpia y convierte datos numéricos que pueden tener comas como separadores decimales
    
    Args:
        df: DataFrame a procesar
        columns: Lista de columnas numéricas a limpiar
        
    Returns:
        DataFrame con datos numéricos limpiados
    """
    df_clean = df.copy()
    
    for col in columns:
        if col in df_clean.columns:
            def clean_european_number(value):
                if pd.isna(value):
                    return None
                
                # Convertir a string y limpiar
                str_val = str(value).strip().replace('"', '')
                
                # Si no contiene números, retornar NaN
                if not any(c.isdigit() for c in str_val):
                    return None
                
                # Manejar formato europeo: "23,418.082"
                if ',' in str_val and '.' in str_val:
                    # Eliminar comas (separador de miles) y mantener punto (decimal)
                    cleaned = str_val.replace(',', '')
                elif ',' in str_val and '.' not in str_val:
                    # Solo coma, podría ser decimal o miles
                    parts = str_val.split(',')
                    if len(parts) == 2 and len(parts[1]) <= 3 and len(parts[1]) > 0:
                        # Probablemente decimal: "123,45" -> "123.45"
                        cleaned = str_val.replace(',', '.')
                    else:
                        # Probablemente separador de miles: "1,234" -> "1234"
                        cleaned = str_val.replace(',', '')
                else:
                    # Solo números y puntos, mantener como está
                    cleaned = str_val
                
                return cleaned
            
            # Aplicar limpieza y convertir a numérico
            df_clean[col] = df_clean[col].apply(clean_european_number)
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    return df_clean

def parse_datetime_column(df: pd.DataFrame, 
                         column_name: str, 
                         target_format: str = '%b %d, %Y %H:%M:%S',
                         create_derived_fields: bool = True) -> tuple[pd.DataFrame, bool]:
    """
    Parsea una columna de datetime en un DataFrame, siempre sobreescribiendo la original
    
    Args:
        df: DataFrame a procesar
        column_name: Nombre de la columna a parsear
        target_format: Formato esperado de la fecha
        create_derived_fields: Si crear campos derivados (hour, date, etc.)
        
    Returns:
        Tuple: (DataFrame procesado, éxito del parseo)
    """
    if column_name not in df.columns:
        return df.copy(), False
    
    df_result = df.copy()
    
    try:
        # Limpiar formato
        df_result[f"{column_name}_clean"] = df_result[column_name].apply(clean_date_format)
        
        # Convertir a datetime
        datetime_series = pd.to_datetime(
            df_result[f"{column_name}_clean"], 
            format=target_format, 
            errors='coerce'
        )
        
        # Verificar si la conversión fue exitosa
        valid_dates = (~datetime_series.isna()).sum()
        
        if valid_dates > 0:
            # Sobreescribir la columna original
            df_result[column_name] = datetime_series
            
            # Crear campos derivados solo si se solicita
            if create_derived_fields:
                df_result["hour"] = datetime_series.dt.hour
                df_result["date"] = datetime_series.dt.date
                df_result["day_of_week"] = datetime_series.dt.day_name()
                df_result["month"] = datetime_series.dt.month
                df_result["year"] = datetime_series.dt.year
            
            success = True
        else:
            success = False
        
        # Limpiar columnas temporales
        df_result.drop([f"{column_name}_clean"], axis=1, inplace=True, errors='ignore')
        
        # Crear columna duration si ambas columnas de tiempo existen
        if "start_time" in df_result.columns and "end_time" in df_result.columns:
            # Verificar que ambas sean datetime
            if (pd.api.types.is_datetime64_any_dtype(df_result["start_time"]) and 
                pd.api.types.is_datetime64_any_dtype(df_result["end_time"])):
                
                # Calcular duración en minutos
                duration_timedelta = df_result["end_time"] - df_result["start_time"]
                df_result["duration_minutes"] = duration_timedelta.dt.total_seconds() / 60
        
        return df_result, success
        
    except Exception:
        return df_result, False