import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.helpers import find_site_column, clean_numeric_data, parse_datetime_column

def create_availability_dashboard(df_availability):
    """
    Crea el dashboard completo de disponibilidad - VERSIÓN MEJORADA
    """
    st.markdown('<h2 class="module-header">🟢 Análisis de Disponibilidad</h2>', unsafe_allow_html=True)
    
    if df_availability is None:
        st.warning("⚠️ No se ha cargado el archivo de Disponibilidad")
        st.info("Sube un archivo CSV desde el panel lateral para ver el análisis.")
        return
    
    # Variables numéricas disponibles
    numeric_columns = ["cell_serv_time"]
    
    # Limpiar datos numéricos usando utilidad centralizada
    df_clean = clean_numeric_data(df_availability, numeric_columns)
    
    # Parsear fechas usando utilidad centralizada
    df_clean, date_conversion_success = parse_datetime_column(df_clean, "start_time")
    
    # Métricas básicas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Registros", f"{len(df_clean):,}")
    
    with col2:
        site_col = find_site_column(df_clean)
        if site_col:
            st.metric("Sites Únicos", df_clean[site_col].nunique())
        else:
            st.metric("Sites Únicos", "N/A")
    
    with col3:
        if date_conversion_success:
            # Usar la nueva columna de datetime
            min_date = df_clean["start_time"].min()
            max_date = df_clean["start_time"].max()
            date_range = (max_date - min_date).days
            st.metric("Rango de Datos (días)", date_range)
        else:
            st.metric("Columnas", len(df_clean.columns))
    
    with col4:
        if "cell_serv_time" in df_clean.columns:
            avg_service_time = df_clean["cell_serv_time"].mean()
            if not pd.isna(avg_service_time):
                # Convertir segundos a horas
                avg_hours = avg_service_time / 3600
                st.metric("Tiempo Servicio Promedio (h)", f"{avg_hours:.2f}")
            else:
                st.metric("Tiempo Servicio Promedio", "N/A")
        else:
            st.metric("Datos Disponibles", "✅ Cargado")
    
    # === FILTROS PRINCIPALES ===
    st.subheader("🎛️ Filtros de Análisis")
    
    # FILTRO POR MÚLTIPLES SITES
    site_col = find_site_column(df_clean)
    if site_col:
        all_sites = sorted(df_clean[site_col].unique())
        selected_sites = st.multiselect(
            "🗼 Seleccionar Sites",
            all_sites,
            default=all_sites[:1] if len(all_sites) >= 1 else all_sites,
            help="Selecciona uno o más sites para analizar su disponibilidad",
            key="disponibilidad_sites"
        )
    else:
        selected_sites = []
        st.error("No se encontró columna de sites")
    
    # === APLICAR FILTROS ===
    df_filtered = df_clean.copy()
    
    # Filtrar por sites
    if selected_sites and site_col:
        df_filtered = df_filtered[df_filtered[site_col].isin(selected_sites)]
    
    # Verificar que hay datos después del filtrado
    if len(df_filtered) == 0:
        st.error("❌ No hay datos que coincidan con los filtros seleccionados")
        return
    
    # === MÉTRICAS FILTRADAS ===
    st.subheader("📈 Resultados Filtrados")
    
    result_col1, result_col2 = st.columns(2)
    
    with result_col1:
        st.metric("Registros Filtrados", f"{len(df_filtered):,}")
    
    with result_col2:
        if selected_sites:
            st.metric("Sites Seleccionados", len(selected_sites))
        else:
            st.metric("Sites", "Ninguno seleccionado")
    
    # === GRÁFICO PRINCIPAL ===
    if "cell_serv_time" in df_filtered.columns and len(df_filtered) > 0 and len(selected_sites) > 0:
        st.subheader(f"📊 Timeline de Disponibilidad - {len(selected_sites)} site(s)")
        
        # Opción para convertir segundos a horas
        convert_to_hours = st.checkbox(
            "Mostrar en horas", 
            value=True, 
            help="Convierte segundos a horas para mejor legibilidad",
            key="disponibilidad_convert_hours"
        )
        
        # Preparar datos para el gráfico
        if date_conversion_success:
            # Preparar datos - usar la nueva columna de datetime
            plot_data = df_filtered.copy().sort_values('start_time')
            
            # Convertir a horas si está seleccionado
            if convert_to_hours:
                plot_data["cell_serv_time_hours"] = plot_data["cell_serv_time"] / 3600
                y_column = "cell_serv_time_hours"
                y_label = "Tiempo de Servicio (horas)"
            else:
                y_column = "cell_serv_time"
                y_label = "Tiempo de Servicio (segundos)"
            
            # Crear gráfico con múltiples sites
            fig = go.Figure()
            
            # Agregar línea para cada site
            for site in selected_sites:
                site_data = plot_data[plot_data[site_col] == site].sort_values('start_time')
                if len(site_data) > 0:
                    fig.add_trace(go.Scatter(
                        x=site_data["start_time"],
                        y=site_data[y_column],
                        mode='lines+markers',
                        name=f"🗼 {site}",
                        line=dict(width=2),
                        marker=dict(size=4)
                    ))
            
            # Configurar layout
            fig.update_layout(
                title=f"Disponibilidad - {', '.join(selected_sites) if len(selected_sites) <= 3 else f'{len(selected_sites)} sites'}",
                xaxis_title="Tiempo",
                yaxis_title=y_label,
                hovermode='x unified',
                height=500,
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=1.01
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        else:
            st.error("❌ No se pueden crear gráficos temporales sin fechas válidas")
    
    elif len(selected_sites) == 0:
        st.info("ℹ️ Selecciona uno o más sites para ver el gráfico de disponibilidad")
    
    else:
        st.warning("⚠️ No hay datos de disponibilidad para mostrar")
    
    # === ANÁLISIS POR HORA DEL DÍA ===
    if date_conversion_success and "cell_serv_time" in df_filtered.columns and len(df_filtered) > 0 and len(selected_sites) > 0:
        st.subheader("🕐 Análisis por Hora del Día")
        
        # Preparar datos
        hourly_data = df_filtered.groupby("hour")["cell_serv_time"].mean().reset_index()
        
        # Usar la misma configuración que el gráfico principal
        if convert_to_hours:
            hourly_data["cell_serv_time_hours"] = hourly_data["cell_serv_time"] / 3600
            y_col_hourly = "cell_serv_time_hours"
            y_label_hourly = "Tiempo Servicio Promedio (h)"
        else:
            y_col_hourly = "cell_serv_time"
            y_label_hourly = "Tiempo Servicio Promedio (s)"
        
        # Gráfico de barras por hora
        fig_hourly = go.Figure()
        fig_hourly.add_trace(go.Bar(
            x=hourly_data["hour"],
            y=hourly_data[y_col_hourly],
            name="Tiempo de Servicio",
            opacity=0.8
        ))
        
        fig_hourly.update_layout(
            title=f"Tiempo de Servicio Promedio por Hora - {len(selected_sites)} site(s)",
            xaxis_title="Hora",
            yaxis_title=y_label_hourly,
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    # === ESTADÍSTICAS RESUMEN ===
    if "cell_serv_time" in df_filtered.columns and len(df_filtered) > 0 and len(selected_sites) > 0:
        st.subheader("📊 Estadísticas Resumen")
        
        service_time_data = df_filtered["cell_serv_time"].dropna()
        if len(service_time_data) > 0:
            
            stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
            
            with stats_col1:
                avg_seconds = service_time_data.mean()
                avg_hours = avg_seconds / 3600
                st.metric("⏱️ Promedio", f"{avg_hours:.2f}h")
            
            with stats_col2:
                min_seconds = service_time_data.min()
                min_hours = min_seconds / 3600
                st.metric("📉 Mínimo", f"{min_hours:.2f}h")
            
            with stats_col3:
                max_seconds = service_time_data.max()
                max_hours = max_seconds / 3600
                st.metric("📈 Máximo", f"{max_hours:.2f}h")
            
            with stats_col4:
                # Calcular disponibilidad como porcentaje (24h = 100%)
                avg_availability = (avg_hours / 24) * 100
                st.metric("📊 Disponibilidad (%)", f"{avg_availability:.1f}%")
    
    # === TABLA DE DATOS FILTRADOS ===
    st.subheader("📋 Datos Filtrados")
    
    # Controles de tabla
    table_col1, table_col2 = st.columns(2)
    
    with table_col1:
        max_rows = st.slider("Número de filas a mostrar:", 10, 500, 100, key="disponibilidad_rows")
    
    with table_col2:
        show_all_columns = st.checkbox(
            "Mostrar todas las columnas", 
            value=False,
            key="disponibilidad_show_all_columns"
        )
    
    # Preparar columnas para mostrar
    if show_all_columns:
        display_columns = list(df_filtered.columns)
    else:
        # Mostrar columnas esenciales - usar la columna de datetime parseada
        essential_columns = ["start_time"]  # Usar la nueva columna parseada
        if site_col:
            essential_columns.append(site_col)
        essential_columns.append("cell_serv_time")
        display_columns = [col for col in essential_columns if col in df_filtered.columns]
    
    # Mostrar tabla
    st.dataframe(df_filtered[display_columns].head(max_rows), use_container_width=True, hide_index=True)
    
    # === BOTÓN DE DESCARGA ===
    csv = df_filtered.to_csv(index=False)
    st.download_button(
        label="📥 Descargar datos filtrados (CSV)",
        data=csv,
        file_name=f"disponibilidad_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key="disponibilidad_download"
    )