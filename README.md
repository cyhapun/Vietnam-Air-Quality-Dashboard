# Vietnam Air Quality Dashboard

**Vietnam Air Quality Dashboard** is an interactive, data-driven web application built with **Streamlit** and **Plotly** to visualize and analyze air quality across Vietnam. The dashboard provides real-time and historical air quality data, weather conditions, and interactive visualizations to help users understand pollution levels and their impact.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B.svg?style=for-the-badge&logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-2C97D1.svg?style=for-the-badge&logo=plotly&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-181717.svg?style=for-the-badge&logo=github&logoColor=white)

## 🚀 Key Features

### 📊 Comprehensive Air Quality Monitoring
- **Real-time AQI Data**: Display current Air Quality Index (AQI) for major cities and provinces
- **Pollutant Breakdown**: Detailed breakdown of major pollutants (PM2.5, PM10, O3, NO2, SO2, CO)
- **Historical Analysis**: Interactive time-series charts to track air quality trends
- **AQI Calculation**: Automatic AQI calculation based on EPA standards

### 🌍 Interactive Visualization
- **Vietnam Map**: Interactive choropleth map showing air quality by province
- **Time-series Charts**: Zoomable and pannable charts for hourly, daily, and monthly analysis
- **Comparison Tools**: Compare air quality across different cities and time periods
- **Heatmaps**: Visualize pollution patterns across different times and locations

### 🧠 Machine Learning Insights
- **AQI Prediction**: Real-time AQI prediction using RandomForestRegressor
- **Trend Forecasting**: 24-hour air quality forecasts
- **Causality Analysis**: Identify relationships between weather and pollution
- **Model Explainability**: SHAP values to explain model predictions

### 🌦️ Weather Integration
- **Weather Data**: Real-time weather conditions including temperature, humidity, wind speed, and precipitation
- **Weather Impact Analysis**: Analyze how weather conditions affect air quality
- **Visual Forecasts**: 24-hour weather forecasts

### ⚙️ Advanced Features
- **Colorblind Mode**: Alternative color palettes for accessibility
- **Data Export**: Export data to CSV for further analysis
- **Responsive Design**: Optimized for both desktop and mobile devices
- **Auto-refresh**: Automatic data updates every hour

## 🛠️ Getting Started

### Prerequisites

Ensure you have the following installed:

- Python 3.9+
- pip

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/Vietnam-Air-Quality-Dashboard.git
   cd Vietnam-Air-Quality-Dashboard
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the root directory with the following (optional):
   ```env
   # Add any API keys or configuration here
   ```

### Running the Application

**Production Mode (Recommended):**

```bash
streamlit run app.py
```

**Development Mode (with hot-reload):**

```bash
streamlit run app.py --server.runOnSave true --server.headless false