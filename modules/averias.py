import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from utils.helpers import find_site_column, parse_datetime_column
from io import BytesIO

def create_site_location_mapping(df_proyectos):
    """Crea un mapeo único de sites a ubicaciones geográficas"""
    if df_proyectos is None:
        return pd.DataFrame()
    
    required_cols = ['SITE_NAME', 'Región', 'Provincia', 'Distrito', 'Localidad']
    existing_cols = [col for col in required_cols if col in df_proyectos.columns]
    
    if len(existing_cols) < 2:
        return pd.DataFrame()
    
    return df_proyectos[existing_cols].drop_duplicates()

def filter_averias_by_geography(df_averias, df_proyectos, region_sel=None, provincia_sel=None, distrito_sel=None, localidad_sel=None):
    """
    Filtra averías por jerarquía geográfica sin duplicar registros
    """
    if df_proyectos is None:
        return df_averias.copy()
    
    # Crear mapeo único
    required_cols = ['SITE_NAME', 'Región', 'Provincia', 'Distrito', 'Localidad']
    existing_cols = [col for col in required_cols if col in df_proyectos.columns]
    
    if len(existing_cols) < 2:
        return df_averias.copy()
    
    site_mapping = df_proyectos[existing_cols].drop_duplicates()
    
    # Aplicar filtros jerárquicos al mapeo
    filtered_mapping = site_mapping.copy()
    
    if region_sel and "Región" in filtered_mapping.columns:
        filtered_mapping = filtered_mapping[filtered_mapping["Región"].isin(region_sel)]
    if provincia_sel and "Provincia" in filtered_mapping.columns:
        filtered_mapping = filtered_mapping[filtered_mapping["Provincia"].isin(provincia_sel)]
    if distrito_sel and "Distrito" in filtered_mapping.columns:
        filtered_mapping = filtered_mapping[filtered_mapping["Distrito"].isin(distrito_sel)]
    if localidad_sel and "Localidad" in filtered_mapping.columns:
        filtered_mapping = filtered_mapping[filtered_mapping["Localidad"].isin(localidad_sel)]
    
    # Obtener sites únicos que cumplen criterios geográficos
    sites_validos = filtered_mapping["SITE_NAME"].unique()
    
    # Filtrar averías por estos sites
    site_column = find_site_column(df_averias)
    if site_column is None:
        return df_averias.copy()
    
    df_filtered = df_averias[df_averias[site_column].isin(sites_validos)].copy()
    
    # Agregar información geográfica
    site_geo_info = filtered_mapping.groupby("SITE_NAME").first().reset_index()
    df_result = df_filtered.merge(
        site_geo_info,
        how="left",
        left_on=site_column,
        right_on="SITE_NAME"
    )
    
    return df_result

def create_averias_dashboard(df_averias, df_proyectos):
    """
    Crea el dashboard completo de averías
    """
    st.markdown('<h2 class="module-header">📊 Análisis de Averías</h2>', unsafe_allow_html=True)
    
    if df_averias is None:
        st.warning("⚠️ No se ha cargado el archivo de Averías")
        st.info("Sube un archivo CSV desde el panel lateral para ver el análisis.")
        return
    
    # === FORMATEAR DATASET ===
    df_formatted = df_averias.copy()
    
    # Normalizar nombres de columnas a minúsculas
    df_formatted.columns = df_formatted.columns.str.lower()
    
    # Formatear columnas geográficas a mayúsculas si existen
    geo_columns = ['región', 'provincia', 'distrito', 'localidad', 'region']
    for col in geo_columns:
        if col in df_formatted.columns:
            df_formatted[col] = df_formatted[col].astype(str).str.upper()
    
    # Formatear columnas de estado
    status_columns = ['alarm_status', 'status', 'estado']
    for col in status_columns:
        if col in df_formatted.columns:
            df_formatted[col] = df_formatted[col].astype(str).str.lower()
    
    # Usar dataset formateado de aquí en adelante
    df_averias = df_formatted

    # Convertir start_time y end_time
    df_averias, start_time_date_conversion_success = parse_datetime_column(df_averias, "start_time")
    df_averias, _ = parse_datetime_column(df_averias, "end_time", create_derived_fields=False)
        
    # Usar el DataFrame principal para el resto del análisis
    df_averias_processed = df_averias
    
    # Métricas iniciales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Averías", f"{len(df_averias_processed):,}")
    
    with col2:
        if "alarm_status" in df_averias_processed.columns:
            averias_activas = len(df_averias_processed[df_averias_processed["alarm_status"] == "active"])
            
            # Métrica arriba
            st.metric("Averías Activas", averias_activas)
            
            # Botón debajo (solo si hay averías)
            if averias_activas > 0:
                # Preparar datos
                averias_activas_all = df_averias_processed[df_averias_processed["alarm_status"] == "active"]
                site_col = find_site_column(averias_activas_all)
                essential_columns = ["start_time", "end_time"]
                if site_col:
                    essential_columns.append(site_col)
                essential_columns.extend(["cell_name", "alarm_id", "alarm_name", "alarm_status"])
                download_columns = [col for col in essential_columns if col in averias_activas_all.columns]
                
                # Ordenar por start_time de más antiguo a más reciente
                if "start_time" in averias_activas_all.columns:
                    averias_activas_all = averias_activas_all.sort_values("start_time", ascending=True)
                
                # Crear Excel
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    averias_activas_all[download_columns].to_excel(
                        writer, 
                        sheet_name='Averias_Activas', 
                        index=False
                    )
                excel_data = buffer.getvalue()
                
                # Botón de descarga
                st.download_button(
                    label="📥 Descargar",
                    data=excel_data,
                    file_name=f"averias_activas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="averias_activas_download",
                    help=f"Descargar {averias_activas} averías activas en Excel"
                )
        else:
            st.metric("Averías Activas", "N/A")

    with col3:
        site_col = find_site_column(df_averias_processed)
        if site_col:
            st.metric("Sites Únicos", df_averias_processed[site_col].nunique())
        else:
            st.metric("Sites Únicos", "N/A")
    
    with col4:
        if df_proyectos is not None:
            st.metric("Proyectos Disponibles", f"{len(df_proyectos):,}")
        else:
            st.metric("Proyectos Disponibles", "No cargado")
    
    # Solo mostrar filtros geográficos si tenemos datos de proyectos
    if df_proyectos is not None and any(col in df_proyectos.columns for col in ['Región', 'Provincia', 'Distrito', 'Localidad']):
        st.subheader("🗺️ Filtros Geográficos Jerárquicos")
        
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        
        # Filtros jerárquicos
        df_temp = df_proyectos.copy()
        
        with filter_col1:
            if "Región" in df_proyectos.columns:
                regiones = sorted(df_proyectos["Región"].dropna().unique())
                region_sel = st.multiselect("🌍 Región", regiones, key="averias_region")
                if region_sel:
                    df_temp = df_temp[df_temp["Región"].isin(region_sel)]
            else:
                region_sel = None
        
        with filter_col2:
            if "Provincia" in df_temp.columns:
                provincias = sorted(df_temp["Provincia"].dropna().unique())
                provincia_sel = st.multiselect("🏛️ Provincia", provincias, key="averias_provincia")
                if provincia_sel:
                    df_temp = df_temp[df_temp["Provincia"].isin(provincia_sel)]
            else:
                provincia_sel = None
        
        with filter_col3:
            if "Distrito" in df_temp.columns:
                distritos = sorted(df_temp["Distrito"].dropna().unique())
                distrito_sel = st.multiselect("🏘️ Distrito", distritos, key="averias_distrito")
                if distrito_sel:
                    df_temp = df_temp[df_temp["Distrito"].isin(distrito_sel)]
            else:
                distrito_sel = None
        
        with filter_col4:
            if "Localidad" in df_temp.columns:
                localidades = sorted(df_temp["Localidad"].dropna().unique())
                localidad_sel = st.multiselect("📍 Localidad", localidades, key="averias_localidad")
            else:
                localidad_sel = None
        
        # Aplicar filtros
        if any([region_sel, provincia_sel, distrito_sel, localidad_sel]):
            df_filtrado = filter_averias_by_geography(
                df_averias_processed, df_proyectos, 
                region_sel, provincia_sel, distrito_sel, localidad_sel
            )
        else:
            df_filtrado = df_averias_processed.copy()
    else:
        df_filtrado = df_averias_processed.copy()
        st.info("ℹ️ Carga el archivo de Proyectos para usar filtros geográficos")
    
    # Eliminar duplicados si existe alarm_id
    if "alarm_id" in df_filtrado.columns:
        df_filtrado = df_filtrado.drop_duplicates(subset=["alarm_id"])
    
    result_col1, result_col2, result_col3 = st.columns(3)
    with result_col1:
        delta = len(df_filtrado) - len(df_averias_processed)
        st.metric("Averías Filtradas", f"{len(df_filtrado):,}", delta=delta)
    
    with result_col2:
        if "alarm_status" in df_filtrado.columns:
            activas_filtradas = len(df_filtrado[df_filtrado["alarm_status"] == "active"])
            st.metric("Activas Filtradas", activas_filtradas)
    
    with result_col3:
        site_col = find_site_column(df_filtrado)
        if site_col:
            sites_filtrados = df_filtrado[site_col].nunique()
            st.metric("Sites Únicos", sites_filtrados)
    
    # Tiempo Promedio de Resolución por Site
    if "duration_minutes" in df_filtrado.columns and site_col:      
        # Calcular solo para averías resueltas (que tienen end_time)
        averias_resueltas = df_filtrado.dropna(subset=["duration_minutes"])
        
        if len(averias_resueltas) > 0:
            tiempo_col1, tiempo_col2, tiempo_col3 = st.columns(3)
            
            with tiempo_col1:
                avg_resolution = averias_resueltas["duration_minutes"].mean()
                st.metric("⏱️ Tiempo Promedio Global", f"{avg_resolution:.1f} min")
            
            with tiempo_col2:
                median_resolution = averias_resueltas["duration_minutes"].median()
                st.metric("📊 Tiempo Mediano", f"{median_resolution:.1f} min")
            
            with tiempo_col3:
                max_resolution = averias_resueltas["duration_minutes"].max()
                st.metric("⚠️ Mayor Tiempo", f"{max_resolution:.1f} min")

            # Top/Bottom sites por tiempo de resolución
            ranking_col1, ranking_col2 = st.columns(2)
            
            with ranking_col1:
                # Sites con mayor tiempo de resolución
                site_avg_time = averias_resueltas.groupby(site_col)["duration_minutes"].agg(['mean', 'count']).reset_index()
                site_avg_time = site_avg_time[site_avg_time['count'] >= 3]  # Solo sites con 3+ averías
                top_slow = site_avg_time.nlargest(10, 'mean')
                
                if len(top_slow) > 0:
                    fig_slow = px.bar(
                        top_slow,
                        x='mean',
                        y=site_col,
                        orientation='h',
                        title="🌊 Sites con Mayor Tiempo de Resolución",
                        labels={'mean': 'Tiempo Promedio (min)', site_col: 'Site'},
                        color='mean',
                        color_continuous_scale='Reds'
                    )
                    fig_slow.update_layout(height=400)
                    st.plotly_chart(fig_slow, use_container_width=True)
            
            with ranking_col2:
                # Sites con averías activas con más tiempo abierto
                if "alarm_status" in df_filtrado.columns:
                    averias_activas_actual = df_filtrado[df_filtrado["alarm_status"] == "active"]
                    
                    if len(averias_activas_actual) > 0 and "start_time" in averias_activas_actual.columns:
                        # Calcular tiempo transcurrido desde inicio de avería activa
                        now = pd.Timestamp.now()
                        averias_activas_actual['tiempo_abierto_horas'] = (now - averias_activas_actual['start_time']).dt.total_seconds() / 3600
                        
                        # Agrupar por site y obtener el promedio de tiempo abierto
                        site_tiempo_abierto = averias_activas_actual.groupby(site_col)['tiempo_abierto_horas'].agg(['mean', 'count']).reset_index()
                        site_tiempo_abierto = site_tiempo_abierto[site_tiempo_abierto['count'] >= 1]  # Al menos 1 avería activa
                        top_tiempo_abierto = site_tiempo_abierto.nlargest(10, 'mean')
                        
                        if len(top_tiempo_abierto) > 0:
                            fig_tiempo_abierto = px.bar(
                                top_tiempo_abierto,
                                x='mean',
                                y=site_col,
                                orientation='h',
                                title="⏰ Sites con averías activas más tiempo abierto",
                                labels={'mean': 'Tiempo promedio abierto (horas)', site_col: 'Site'},
                                color='mean',
                                color_continuous_scale='Oranges'
                            )
                            fig_tiempo_abierto.update_layout(height=400)
                            st.plotly_chart(fig_tiempo_abierto, use_container_width=True)
                        else:
                            st.info("No hay suficientes averías activas para mostrar")
                    else:
                        st.info("No hay averías activas o faltan datos de tiempo")
                else:
                    st.warning("No se encontró la columna 'alarm_status'")

    # Análisis de distribución
    st.subheader("📈 Distribución de tiempos de resolución")

    # Selector de site para análisis detallado
    if "duration_minutes" in df_filtrado.columns and site_col:
        averias_resueltas = df_filtrado.dropna(subset=["duration_minutes"])
        sites_con_datos = averias_resueltas[site_col].value_counts()
        sites_disponibles = sites_con_datos[sites_con_datos >= 5].index.tolist()  # Solo sites con 5+ averías

        if sites_disponibles:
            selected_site_analysis = st.selectbox(
                "Seleccionar site para análisis detallado:",
                ["Todos"] + sites_disponibles,
                key="site_analysis_selector"
            )
            
            if selected_site_analysis == "Todos":
                analysis_data = averias_resueltas
                title_suffix = "Todos los Sites"
            else:
                analysis_data = averias_resueltas[averias_resueltas[site_col] == selected_site_analysis]
                title_suffix = selected_site_analysis
            
            # Histograma de distribución
            fig_hist = px.histogram(
                analysis_data,
                x="duration_minutes",
                nbins=30,
                title=f"Distribución de tiempos de resolución - {title_suffix}",
                labels={'duration_minutes': 'Tiempo de resolución (minutos)', 'count': 'Frecuencia'}
            )
            st.plotly_chart(fig_hist, use_container_width=True)

    # === TOP SITES EN DOS COLUMNAS ===
    site_col = find_site_column(df_filtrado)
    if site_col:
        st.subheader("🏆 Top Sites con averías")
        
        sites_col1, sites_col2 = st.columns(2)
        
        with sites_col1:
            # Top sites con más averías totales
            top_sites_total = df_filtrado[site_col].value_counts().head(10)
            
            if len(top_sites_total) > 0:
                fig_top_sites_total = px.bar(
                    x=top_sites_total.values,
                    y=top_sites_total.index,
                    orientation='h',
                    title="📊 Top 10 Sites - Averías Totales",
                    labels={'x': 'Número de Averías', 'y': 'Site'},
                    color=top_sites_total.values,
                    color_continuous_scale='Blues'
                )
                fig_top_sites_total.update_layout(height=400, showlegend=False, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_top_sites_total, use_container_width=True)
            else:
                st.info("No hay datos de averías para mostrar")
        
        with sites_col2:
            # Top sites con más averías activas
            if "alarm_status" in df_filtrado.columns:
                averias_activas = df_filtrado[df_filtrado["alarm_status"] == "active"]
                
                if len(averias_activas) > 0:
                    top_sites_activas = averias_activas[site_col].value_counts().head(10)
                    
                    if len(top_sites_activas) > 0:
                        fig_top_sites_activas = px.bar(
                            x=top_sites_activas.values,
                            y=top_sites_activas.index[::-1],  # Invertir orden para mostrar descendente
                            orientation='h',
                            title="🚨 Top 10 Sites - Averías Activas",
                            labels={'x': 'Número de Averías Activas', 'y': 'Site'},
                            color=top_sites_activas.values,
                            color_continuous_scale='Reds'
                        )
                        fig_top_sites_activas.update_layout(height=400, showlegend=False, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_top_sites_activas, use_container_width=True)
                    else:
                        st.info("No hay averías activas en los sites filtrados")
                else:
                    st.info("No hay averías activas para mostrar")
            else:
                st.warning("No se encontró la columna 'alarm_status'")
    
    # Análisis temporal
    if start_time_date_conversion_success:
        st.subheader("📅 Análisis Temporal")
        
        try:
            col_temp1, col_temp2 = st.columns(2)
            
            with col_temp1:
                # Averías por hora del día
                if "hour" in df_filtrado.columns:
                    hourly_alarms = df_filtrado.groupby("hour").size()
                    fig_hourly = px.bar(
                        x=hourly_alarms.index,
                        y=hourly_alarms.values,
                        title="Averías por Hora del Día",
                        labels={'x': 'Hora', 'y': 'Número de Averías'}
                    )
                    st.plotly_chart(fig_hourly, use_container_width=True)
            
            with col_temp2:
                # Averías por día de la semana
                if "day_of_week" in df_filtrado.columns:
                    daily_alarms = df_filtrado.groupby("day_of_week").size()
                    fig_daily = px.bar(
                        x=daily_alarms.index,
                        y=daily_alarms.values,
                        title="Averías por Día de la Semana",
                        labels={'x': 'Día', 'y': 'Número de Averías'}
                    )
                    st.plotly_chart(fig_daily, use_container_width=True)
        
        except Exception as e:
            st.warning(f"No se pudo procesar el análisis temporal: {str(e)}")
    else:
        st.info("ℹ️ No se pudieron procesar datos temporales. Verifica que existan columnas de fecha/hora válidas.")
    
    # === MAPA DE AVERÍAS ACTIVAS ===
    if df_proyectos is not None and len(df_filtrado) > 0:
        st.subheader("🗺️ Mapa de Averías Activas")
        
        # Filtrar solo averías activas
        if "alarm_status" in df_filtrado.columns:
            averias_activas = df_filtrado[df_filtrado["alarm_status"] == "active"]
            
            if len(averias_activas) > 0:
                site_col = find_site_column(averias_activas)
                if site_col:
                    # Obtener sites únicos con averías activas
                    sites_activos = averias_activas[site_col].unique()
                    
                    # Verificar si tenemos coordenadas en proyectos
                    coord_cols_options = [
                        ("Latitud (WGS 84)", "Longitud (WGS 84)"),
                        ("Latitud", "Longitud"),
                        ("lat", "lon")
                    ]
                    
                    coord_cols = None
                    for lat_col, lon_col in coord_cols_options:
                        if lat_col in df_proyectos.columns and lon_col in df_proyectos.columns:
                            coord_cols = (lat_col, lon_col)
                            break
                    
                    if coord_cols:
                        # Filtrar proyectos que tienen averías activas
                        proyectos_activos = df_proyectos[
                            df_proyectos["SITE_NAME"].isin(sites_activos)
                        ].copy()
                        
                        # Limpiar y convertir coordenadas
                        proyectos_activos["lat"] = pd.to_numeric(proyectos_activos[coord_cols[0]], errors='coerce')
                        proyectos_activos["lon"] = pd.to_numeric(proyectos_activos[coord_cols[1]], errors='coerce')
                        
                        # Filtrar coordenadas válidas
                        proyectos_mapa = proyectos_activos.dropna(subset=['lat', 'lon'])
                        
                        if len(proyectos_mapa) > 0:
                            # Buscar la columna de alarm_name normalizada (minúsculas)
                            alarm_name_col = None
                            for col in ["alarm_name", "alarm_Name", "Alarm_Name"]:
                                if col in averias_activas.columns:
                                    alarm_name_col = col
                                    break
                            
                            # Crear lista de columnas para el merge
                            merge_cols = [site_col]
                            if alarm_name_col:
                                merge_cols.append(alarm_name_col)
                            if "start_time" in averias_activas.columns:
                                merge_cols.append("start_time")
                            
                            # Agregar información de averías al mapa
                            mapa_data = proyectos_mapa.merge(
                                averias_activas[merge_cols],
                                left_on="SITE_NAME",
                                right_on=site_col,
                                how="inner"
                            )
                            
                            # Contar averías por site
                            alarmas_por_site = averias_activas.groupby(site_col).size().reset_index(name='num_alarmas')
                            mapa_data = mapa_data.merge(alarmas_por_site, left_on="SITE_NAME", right_on=site_col, how="left")
                            
                            # Preparar datos para hover
                            hover_data = {
                                "lat": False,
                                "lon": False,
                                "num_alarmas": True
                            }
                            
                            # Agregar campos disponibles al hover
                            hover_fields = ["Región", "Provincia", "Distrito", "start_time"]
                            if alarm_name_col:
                                hover_fields.append(alarm_name_col)
                            
                            for col in hover_fields:
                                if col in mapa_data.columns:
                                    hover_data[col] = True
                            
                            # Crear mapa con plotly - USANDO PUNTOS SIMPLES
                            fig_mapa = px.scatter_mapbox(
                                mapa_data,
                                lat="lat",
                                lon="lon",
                                hover_name="SITE_NAME",
                                hover_data=hover_data,
                                color="Región" if "Región" in mapa_data.columns else "num_alarmas",
                                zoom=5,
                                title=f"🚨 {len(mapa_data)} Sites con Averías Activas"
                            )
                            
                            # Si no hay región para colorear, usar escala de rojos para num_alarmas
                            if "Región" not in mapa_data.columns:
                                fig_mapa.update_traces(
                                    marker=dict(
                                        colorscale="Reds",
                                        colorbar=dict(title="Número de Alarmas")
                                    )
                                )
                            
                            # Configurar el mapa
                            fig_mapa.update_layout(
                                mapbox_style="open-street-map",
                                height=600,
                                showlegend=True,
                                title=f"🚨 {len(mapa_data)} Sites con Averías Activas",
                                mapbox=dict(
                                    center=dict(lat=-9.19, lon=-75.02),  # Centro de Perú
                                    zoom=5
                                )
                            )
                            
                            st.plotly_chart(fig_mapa, use_container_width=True)
                            
                            # Mostrar estadísticas del mapa
                            map_col1, map_col2, map_col3, map_col4 = st.columns(4)
                            
                            with map_col1:
                                st.metric("🗺️ Sites Mapeados", len(mapa_data))
                            
                            with map_col2:
                                total_alarmas = mapa_data["num_alarmas"].sum()
                                st.metric("🚨 Total Alarmas Activas", int(total_alarmas))
                            
                            with map_col3:
                                if "Región" in mapa_data.columns:
                                    regiones_afectadas = mapa_data["Región"].nunique()
                                    st.metric("🌍 Regiones Afectadas", regiones_afectadas)
                            
                            with map_col4:
                                promedio_alarmas = mapa_data["num_alarmas"].mean()
                                st.metric("📊 Promedio Alarmas/Site", f"{promedio_alarmas:.1f}")
                        
                        else:
                            st.warning("⚠️ No se encontraron coordenadas válidas para mostrar el mapa")
                    
                    else:
                        st.warning("⚠️ No se encontraron columnas de coordenadas en los datos de proyectos")
                        st.info("Columnas esperadas: 'Latitud (WGS 84)' y 'Longitud (WGS 84)' o similares")
                
                else:
                    st.warning("⚠️ No se encontró columna de sites en averías")
            
            else:
                st.info("ℹ️ No hay averías activas para mostrar en el mapa")
        
        else:
            st.warning("⚠️ No se encontró la columna 'alarm_status' para filtrar averías activas")
    
    # === TABLA DE DATOS FILTRADOS ===
    st.subheader("📋 Tabla de Averías")
    
    # Filtros adicionales por fechas y sites
    st.subheader("🔍 Filtros Adicionales")
    
    # Aplicar filtros paso a paso
    df_temp_filtros = df_filtrado.copy()
    
    # === FILTRO POR RANGO DE FECHAS ===
    if "start_time" in df_filtrado.columns and start_time_date_conversion_success:
        st.markdown("**📅 Filtro por Rango de Fechas**")
        
        # Obtener rango de fechas disponible
        min_date = df_filtrado["start_time"].min().date()
        max_date = df_filtrado["start_time"].max().date()
        
        date_col1, date_col2 = st.columns(2)
        
        with date_col1:
            fecha_inicio = st.date_input(
                "Fecha de inicio:",
                value=min_date,
                min_value=min_date,
                max_value=max_date,
                key="averias_fecha_inicio"
            )
        
        with date_col2:
            fecha_fin = st.date_input(
                "Fecha de fin:",
                value=max_date,
                min_value=min_date,
                max_value=max_date,
                key="averias_fecha_fin"
            )
        
        # Validar y aplicar filtro de fechas
        if fecha_inicio <= fecha_fin:
            # Filtrar por rango de fechas
            df_temp_filtros = df_temp_filtros[
                (df_temp_filtros["start_time"].dt.date >= fecha_inicio) &
                (df_temp_filtros["start_time"].dt.date <= fecha_fin)
            ].copy()
            
            # Mostrar métricas del filtro de fechas
            date_metrics_col1, date_metrics_col2, date_metrics_col3 = st.columns(3)
            
            with date_metrics_col1:
                delta_fechas = len(df_temp_filtros) - len(df_filtrado)
                st.metric("Registros en rango", f"{len(df_temp_filtros):,}", delta=delta_fechas)
            
            with date_metrics_col2:
                if "alarm_status" in df_temp_filtros.columns:
                    activas_rango = len(df_temp_filtros[df_temp_filtros["alarm_status"] == "active"])
                    st.metric("Activas en rango", activas_rango)
            
            with date_metrics_col3:
                dias_seleccionados = (fecha_fin - fecha_inicio).days + 1
                st.metric("Días seleccionados", dias_seleccionados)
        else:
            st.error("⚠️ La fecha de inicio debe ser menor o igual a la fecha de fin")
    else:
        st.info("ℹ️ No hay datos de fecha válidos para aplicar filtro temporal")
    
    # === FILTRO POR SITE NAME ===
    site_col = find_site_column(df_temp_filtros)
    if site_col:
        st.markdown("**🏗️ Filtro por Site Name**")
        
        # Obtener lista de sites únicos en los datos filtrados por fecha
        sites_disponibles = sorted(df_temp_filtros[site_col].dropna().unique())
        
        if sites_disponibles:
            site_filter_col1, site_filter_col2 = st.columns([3, 1])
            
            with site_filter_col1:
                sites_seleccionados = st.multiselect(
                    "Seleccionar sites:",
                    options=sites_disponibles,
                    default=[],
                    key="averias_sites_filter",
                    help=f"Disponibles: {len(sites_disponibles)} sites únicos"
                )
            
            with site_filter_col2:
                st.markdown("**Acciones rápidas:**")
                if st.button("Seleccionar todos", key="select_all_sites"):
                    st.session_state["averias_sites_filter"] = sites_disponibles
                    st.rerun()
                
                if st.button("Limpiar selección", key="clear_sites"):
                    st.session_state["averias_sites_filter"] = []
                    st.rerun()
            
            # Aplicar filtro de sites si hay selección
            if sites_seleccionados:
                df_temp_filtros = df_temp_filtros[
                    df_temp_filtros[site_col].isin(sites_seleccionados)
                ].copy()
                
                # Mostrar métricas del filtro de sites
                site_metrics_col1, site_metrics_col2, site_metrics_col3 = st.columns(3)
                
                with site_metrics_col1:
                    st.metric("Sites seleccionados", len(sites_seleccionados))
                
                with site_metrics_col2:
                    registros_sites = len(df_temp_filtros)
                    st.metric("Registros filtrados", f"{registros_sites:,}")
                
                with site_metrics_col3:
                    if "alarm_status" in df_temp_filtros.columns:
                        activas_sites = len(df_temp_filtros[df_temp_filtros["alarm_status"] == "active"])
                        st.metric("Activas filtradas", activas_sites)
        else:
            st.warning("⚠️ No hay sites disponibles en el rango de fechas seleccionado")
    else:
        st.warning("⚠️ No se encontró columna de sites para filtrar")
    
    # Usar el DataFrame con todos los filtros aplicados
    df_tabla = df_temp_filtros
    
    # Controles de tabla
    table_col1, table_col2 = st.columns(2)

    with table_col1:
        max_rows = st.slider("Número de filas a mostrar:", 10, 500, 100, key="averias_rows")
    
    with table_col2:
        show_all_columns = st.checkbox("Mostrar todas las columnas", value=False, key="averias_show_all_columns")

    # Preparar columnas para mostrar
    if show_all_columns:
        display_columns = list(df_tabla.columns)
    else:
        # Mostrar columnas esenciales
        essential_columns = ["start_time", "end_time", "duration_minutes"]
        if site_col:
            essential_columns.append(site_col)
        essential_columns.extend(["cell_name", "alarm_id", "alarm_name", "alarm_status"])
        display_columns = [col for col in essential_columns if col in df_tabla.columns]
    
    # Mostrar datos
    st.dataframe(df_tabla[display_columns].head(max_rows), use_container_width=True, hide_index=True)
    
    # Botones de descarga
    download_col1, download_col2 = st.columns(2)
    
    with download_col1:
        # Botón de descarga CSV
        csv = df_tabla.to_csv(index=False)
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"averias_filtradas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            key="averias_download_filtered_csv"
        )
    
    with download_col2:
        # Botón de descarga Excel
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_tabla.to_excel(writer, sheet_name='Averias_Filtradas', index=False)
        excel_data = buffer.getvalue()
        
        st.download_button(
            label="📥 Descargar Excel",
            data=excel_data,
            file_name=f"averias_filtradas_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="averias_download_filtered_excel"
        )