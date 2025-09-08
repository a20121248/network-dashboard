# Network KPI Dashboard
An interactive dashboard built with **Streamlit** for analyzing telecom network KPIs from multiple CSV data sources.  

## Features
- Upload multiple network performance files:
  - **Alarms**
  - **Performance**
  - **Configuration**
  - **Provision**
  - **Availability**
  - **Quality**
- Interactive filters (year, month, site, department)
- KPI visualizations using **Plotly**
- Tabs for each dataset
- Persistent session state for uploaded files

## Project Structure
```
network_dashboard/
├── app.py                 # Archivo principal
├── modules/
│   ├── __init__.py
│   ├── averias.py         # Módulo de averías
│   ├── desempeño.py       # Módulo de desempeño
│   ├── configuration.py   # Módulo de configuración
│   ├── provision.py       # Módulo de provisionamiento
│   ├── disponibilidad.py  # Módulo de disponibilidad
│   └── calidad.py         # Módulo de calidad
├── utils/
│   ├── __init__.py
│   ├── data_loader.py     # Funciones de carga
│   └── helpers.py         # Funciones auxiliares
└── requirements.txt       # Dependencies de Python
├── README.md
└── .gitignore
````

## Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/network-kpi-dashboard.git
cd network-kpi-dashboard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Run the App
```bash
streamlit run app.py
```

## Deployment
You can deploy the dashboard using:
* [Streamlit Cloud](https://streamlit.io/cloud)
* [Render](https://render.com/)
* [Docker](https://www.docker.com/) for containerization

## Notes
* The `data/` folder is ignored in `.gitignore`. Use it for local CSV files.
* Uploaded files are processed in-memory during the session.
