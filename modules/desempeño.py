import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from utils.helpers import find_site_column, clean_numeric_data, parse_datetime_column

def create_performance_dashboard(df_performance):
    """
    Crea el dashboard completo de desempeño
    """
    st.markdown('<h2 class="module-header">🚀 Análisis de Desempeño</h2>', unsafe_allow_html=True)
    
    if df_performance is None:
        st.warning("⚠️ No se ha cargado el archivo de Desempeño")
        st.info("Sube un archivo CSV desde el panel lateral para ver el análisis.")
        return
    
    # Variables numéricas disponibles
    numeric_columns = [
        "dl_data_traffic_mb", "ul_data_traffic_mb", "enodeb_dl_tgput_mb",
        "lte_dl_cell_tgput_mb", "lte_ul_cell_tgput_mb", "lte_tu_prb_dl",
        "average_number_user", "enodeb_ul_tgput_mb", "latency", 
        "tcp_pckt_loss_ratio", "voice_traffic"
    ]
    
    # Limpiar datos numéricos
    df_clean = clean_numeric_data(df_performance, numeric_columns)

    # Convertir start_time y end_time
    df_clean, date_conversion_success = parse_datetime_column(df_clean, "start_time")
    df_clean, _ = parse_datetime_column(df_clean, "end_time", create_derived_fields=False)
       
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
            # Calcular rango de fechas
            min_date = df_clean["start_time"].min()
            max_date = df_clean["start_time"].max()
            date_range = (max_date - min_date).days
            st.metric("Rango de Datos (días)", date_range)
        else:
            st.metric("Columnas", len(df_clean.columns))
    
    with col4:
        # Mostrar cantidad de métricas numéricas disponibles
        available_metrics = [col for col in numeric_columns if col in df_clean.columns]
        st.metric("Métricas Disponibles", len(available_metrics))
    
    # === FILTROS PRINCIPALES ===
    st.subheader("🎛️ Filtros de Análisis")
    
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    
    with filter_col1:
        # Filtro por Site
        site_col = find_site_column(df_clean)
        if site_col:
            all_sites = sorted(df_clean[site_col].unique())
            selected_sites = st.multiselect(
                "🗼 Seleccionar Sites",
                all_sites,
                default=all_sites[:1] if len(all_sites) >= 1 else all_sites,
                help="Selecciona uno o más sites para analizar",
                key="desempeño_sites"
            )
        else:
            selected_sites = []
            st.error("No se encontró columna de sites")
    
    with filter_col2:
        # Filtro por Métricas
        available_metrics = [col for col in numeric_columns if col in df_clean.columns]
        
        # Crear nombres más amigables para las métricas
        metric_labels = {
            "dl_data_traffic_mb": "📥 Tráfico DL (MB)",
            "ul_data_traffic_mb": "📤 Tráfico UL (MB)", 
            "enodeb_dl_tgput_mb": "🚀 eNodeB DL Throughput (MB)",
            "lte_dl_cell_tgput_mb": "📶 LTE DL Cell Throughput (MB)",
            "lte_ul_cell_tgput_mb": "📶 LTE UL Cell Throughput (MB)",
            "lte_tu_prb_dl": "📡 PRB DL Utilization (%)",
            "average_number_user": "👥 Usuarios Promedio",
            "enodeb_ul_tgput_mb": "🚀 eNodeB UL Throughput (MB)",
            "latency": "⚡ Latencia (ms)",
            "tcp_pckt_loss_ratio": "📉 TCP Packet Loss Ratio",
            "voice_traffic": "📞 Tráfico de Voz"
        }
        
        selected_metrics = st.multiselect(
            "📊 Seleccionar Métricas",
            available_metrics,
            default=available_metrics[:2] if len(available_metrics) >= 2 else available_metrics,
            format_func=lambda x: metric_labels.get(x, x),
            help="Selecciona las métricas que quieres visualizar",
            key="desempeño_metrics"
        )
    
    with filter_col3:
        # Filtro de tiempo (solo si las fechas se convirtieron correctamente)
        if date_conversion_success:
            min_date = df_clean["start_time"].min().date()
            max_date = df_clean["start_time"].max().date()
            
            # Selector de rango rápido
            time_range_option = st.selectbox(
                "⏰ Rango de Tiempo",
                ["Todos los datos", "Último día", "Últimos 3 días", "Última semana", "Personalizado"],
                key="desempeño_time_range"
            )
            
            if time_range_option == "Último día":
                start_date = max_date
                end_date = max_date
            elif time_range_option == "Últimos 3 días":
                start_date = max_date - timedelta(days=2)
                end_date = max_date
            elif time_range_option == "Última semana":
                start_date = max_date - timedelta(days=6)
                end_date = max_date
            elif time_range_option == "Personalizado":
                col_start, col_end = st.columns(2)
                with col_start:
                    start_date = st.date_input("Fecha inicio", min_date, min_value=min_date, max_value=max_date)
                with col_end:
                    end_date = st.date_input("Fecha fin", max_date, min_value=min_date, max_value=max_date)
            else:  # Todos los datos
                start_date = min_date
                end_date = max_date
        else:
            start_date = None
            end_date = None
    
    # === APLICAR FILTROS ===
    df_filtered = df_clean.copy()
    
    # Filtrar por sites
    if selected_sites and site_col:
        df_filtered = df_filtered[df_filtered[site_col].isin(selected_sites)]
    
    # Filtrar por fechas
    if date_conversion_success and start_date and end_date:
        mask = (df_filtered["start_time"].dt.date >= start_date) & (df_filtered["start_time"].dt.date <= end_date)
        df_filtered = df_filtered[mask]
    
    # Verificar que hay datos después del filtrado
    if len(df_filtered) == 0:
        st.error("❌ No hay datos que coincidan con los filtros seleccionados")
        return
    
    # === MÉTRICAS FILTRADAS ===
    st.subheader("📈 Resultados Filtrados")
    
    result_col1, result_col2, result_col3, result_col4 = st.columns(4)
    
    with result_col1:
        st.metric("Registros Filtrados", f"{len(df_filtered):,}")
    
    with result_col2:
        if site_col:
            st.metric("Sites Seleccionados", df_filtered[site_col].nunique())
    
    with result_col3:
        st.metric("Métricas Seleccionadas", len(selected_metrics))
    
    with result_col4:
        if date_conversion_success:
            days_selected = (end_date - start_date).days + 1
            st.metric("Días Analizados", days_selected)
    
    # === GRÁFICO PRINCIPAL ===
    if selected_metrics and len(df_filtered) > 0:
        st.subheader("📊 Gráfico Principal - Timeline de Métricas")
        
        # Opciones de visualización
        viz_col1, viz_col2, viz_col3 = st.columns(3)
        
        with viz_col1:
            chart_type = st.radio(
                "Tipo de Gráfico",
                ["Líneas", "Barras", "Área"],
                horizontal=True
            )
        
        with viz_col2:
            if len(selected_sites) > 1:
                show_by_site = st.checkbox("Separar por Site", value=True, key="desempeño_show_by_site")
            else:
                show_by_site = False
        
        with viz_col3:
            normalize_data = st.checkbox("Normalizar datos (0-100%)", help="Útil para comparar métricas con diferentes escalas", key="desempeño_normalize_data")
        
        # Preparar datos para el gráfico
        if date_conversion_success:
            # Crear gráfico temporal
            fig = go.Figure()
            
            # Preparar datos
            plot_data = df_filtered.copy()
            
            # Normalizar si está seleccionado
            if normalize_data:
                for metric in selected_metrics:
                    if metric in plot_data.columns:
                        min_val = plot_data[metric].min()
                        max_val = plot_data[metric].max()
                        if max_val != min_val:
                            plot_data[f"{metric}_norm"] = ((plot_data[metric] - min_val) / (max_val - min_val)) * 100
                        else:
                            plot_data[f"{metric}_norm"] = 0
                selected_metrics_plot = [f"{metric}_norm" for metric in selected_metrics]  # MOVER ESTA LÍNEA AQUÍ
            else:
                selected_metrics_plot = selected_metrics
            
            # Crear gráfico según el tipo seleccionado
            if chart_type == "Líneas":
                if show_by_site and site_col:
                    # Gráfico con múltiples sites
                    for site in selected_sites:
                        site_data = plot_data[plot_data[site_col] == site]
                        for metric in selected_metrics_plot:
                            if metric in site_data.columns:
                                display_name = f"{metric_labels.get(metric.replace('_norm', ''), metric)} - {site}"
                                fig.add_trace(go.Scatter(
                                    x=site_data["start_time"],
                                    y=site_data[metric],
                                    mode='lines+markers',
                                    name=display_name,
                                    line=dict(width=2)
                                ))
                else:
                    # Gráfico con múltiples métricas
                    for metric in selected_metrics_plot:
                        if metric in plot_data.columns:
                            display_name = metric_labels.get(metric.replace('_norm', ''), metric)
                            fig.add_trace(go.Scatter(
                                x=plot_data["start_time"],
                                y=plot_data[metric],
                                mode='lines+markers',
                                name=display_name,
                                line=dict(width=2)
                            ))
            
            elif chart_type == "Barras":
                # Para barras, agrupar por hora o por intervalo
                plot_data["hour_bin"] = plot_data["start_time"].dt.floor('H')
                hourly_data = plot_data.groupby("hour_bin")[selected_metrics_plot].mean().reset_index()
                
                for metric in selected_metrics_plot:
                    if metric in hourly_data.columns:
                        display_name = metric_labels.get(metric.replace('_norm', ''), metric)
                        fig.add_trace(go.Bar(
                            x=hourly_data["hour_bin"],
                            y=hourly_data[metric],
                            name=display_name,
                            opacity=0.7
                        ))
            
            elif chart_type == "Área":
                for metric in selected_metrics_plot:
                    if metric in plot_data.columns:
                        display_name = metric_labels.get(metric.replace('_norm', ''), metric)
                        fig.add_trace(go.Scatter(
                            x=plot_data["start_time"],
                            y=plot_data[metric],
                            mode='lines',
                            name=display_name,
                            fill='tonexty' if metric != selected_metrics_plot[0] else 'tozeroy',
                            line=dict(width=0)
                        ))
            
            # Configurar layout
            fig.update_layout(
                title=f"Timeline de Métricas - {', '.join(selected_sites) if len(selected_sites) <= 3 else f'{len(selected_sites)} sites'}",
                xaxis_title="Tiempo",
                yaxis_title="Valores" + (" (Normalizados 0-100%)" if normalize_data else ""),
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
    
    # === ANÁLISIS POR HORA DEL DÍA ===
    if date_conversion_success and selected_metrics:
        st.subheader("🕐 Análisis por Hora del Día")
        
        # Calcular promedios por hora
        hourly_data = df_filtered.groupby("hour")[selected_metrics].mean().reset_index()
        
        # Gráfico de barras por hora
        fig_hourly = go.Figure()
        
        for metric in selected_metrics:
            if metric in hourly_data.columns:
                display_name = metric_labels.get(metric, metric)
                fig_hourly.add_trace(go.Bar(
                    x=hourly_data["hour"],
                    y=hourly_data[metric],
                    name=display_name,
                    opacity=0.8
                ))
        
        fig_hourly.update_layout(
            title="Promedios por Hora del Día",
            xaxis_title="Hora",
            yaxis_title="Valor Promedio",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig_hourly, use_container_width=True)
    
    # === COMPARACIÓN ENTRE SITES ===
    if len(selected_sites) > 1 and selected_metrics and site_col:
        st.subheader("🏆 Comparación entre Sites")
        
        # Calcular promedios por site
        site_averages = df_filtered.groupby(site_col)[selected_metrics].mean().reset_index()
        
        # Seleccionar métrica para comparar
        comparison_metric = st.selectbox(
            "Métrica para comparación:",
            selected_metrics,
            format_func=lambda x: metric_labels.get(x, x),
            key="desempeño_comparison_metric"
        )
        
        if comparison_metric in site_averages.columns:
            # Gráfico de barras horizontal
            fig_comparison = px.bar(
                site_averages,
                x=comparison_metric,
                y=site_col,
                orientation='h',
                title=f"Comparación de {metric_labels.get(comparison_metric, comparison_metric)} entre Sites",
                labels={'x': metric_labels.get(comparison_metric, comparison_metric), 'y': 'Site'}
            )
            fig_comparison.update_layout(height=max(400, len(selected_sites) * 30))
            st.plotly_chart(fig_comparison, use_container_width=True)
    
    # === ESTADÍSTICAS RESUMEN ===
    if selected_metrics:
        st.subheader("📊 Estadísticas Resumen")
        
        stats_data = []
        for metric in selected_metrics:
            if metric in df_filtered.columns:
                metric_data = df_filtered[metric].dropna()
                if len(metric_data) > 0:
                    stats_data.append({
                        "Métrica": metric_labels.get(metric, metric),
                        "Promedio": f"{metric_data.mean():.3f}",
                        "Mínimo": f"{metric_data.min():.3f}",
                        "Máximo": f"{metric_data.max():.3f}",
                        "Desv. Estándar": f"{metric_data.std():.3f}",
                        "Registros": len(metric_data)
                    })
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    # === TABLA DE DATOS FILTRADOS ===
    st.subheader("📋 Datos filtrados")
    
    # Controles de tabla
    table_col1, table_col2 = st.columns(2)
    
    with table_col1:
        max_rows = st.slider("Número de filas a mostrar:", 10, 500, 100, key="desempeño_rows")
    
    with table_col2:
        show_all_columns = st.checkbox("Mostrar todas las columnas", value=False, key="desempeño_show_all_columns")
    
    # Preparar columnas para mostrar
    if show_all_columns:
        display_columns = list(df_filtered.columns)
    else:
        # Mostrar columnas esenciales
        essential_columns = ["start_time", "end_time"]
        if site_col:
            essential_columns.append(site_col)
        essential_columns.extend(selected_metrics)
        display_columns = [col for col in essential_columns if col in df_filtered.columns]
    
    # Mostrar datos
    st.dataframe(df_filtered[display_columns].head(max_rows), use_container_width=True, hide_index=True)
    
    # Botón de descarga
    csv = df_filtered.to_csv(index=False)
    st.download_button(
        label="📥 Descargar datos filtrados (CSV)",
        data=csv,
        file_name=f"desempeño_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key="desempeño_download_filtered"
    )