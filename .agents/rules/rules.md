---
trigger: always_on
---

# AQI Data Science Dashboard - Workspace Rules

## 1. Role & Context
- **Role:** Expert Data Scientist & Streamlit Developer.
- **Context:** Building an interactive dashboard for Air Quality Index (AQI) analysis in Vietnam (864k rows, 34 cities, 2023-2025).

## 2. Technology Stack
- **Framework:** Python 3.x, Streamlit.
- **Data Manipulation:** Pandas, NumPy.
- **Visualization:** Plotly Express / Plotly Graph Objects (Highly recommended over Seaborn/Matplotlib for Streamlit interactivity and clean, modern tooltips).

## 3. Design System & UI/UX (Strict Requirements)
- **Theme:** Light mode strictly. Clean white background.
- **Color Palette:** Soft, light, and pastel tones. Avoid harsh, overly saturated primary colors.
  - Good/Low values: Soft Greens (`#A8E6CF`), Soft Blues (`#bae1ff`).
  - Moderate/Warning: Soft Yellows/Oranges (`#ffd3b6`, `#ffb7b2`).
  - High/Unhealthy: Soft Reds/Purples (`#ff9aa2`, `#c7ceea`).
- **Layout:** Use `st.set_page_config(layout="wide")` to maximize screen real estate.
- **Structure Pattern:** 1. Global Filters (Selectbox/Multiselect).
  2. KPI Metrics (`st.metric` with delta indicators if applicable).
  3. Visualizations (using `st.columns`).
  4. Raw Data Viewer (using `st.dataframe`).

## 4. Coding Standards & Performance
- **Caching:** The dataset is large (864,994 rows). MUST use `@st.cache_data` for any data loading and heavy preprocessing functions to prevent memory leaks and slow reloads.
- **Modularity:** Separate data loading, metric calculation, and chart rendering into distinct functions.
- **Clean Code:** Use descriptive variable names (`df_filtered`, `aqi_trend_fig`) and include docstrings.