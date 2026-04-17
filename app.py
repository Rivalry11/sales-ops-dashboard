"""
app.py - Sales Operations Analytics Dashboard
Run locally: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Sales Operations Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for cleaner look
st.markdown("""
    <style>
    .main { padding-top: 1rem; }
    .stMetric { 
        background-color: #f8f9fa; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 4px solid #1f3864; 
        color: #262730 !important;
    }
    .stMetric label, .stMetric [data-testid="stMetricValue"], .stMetric [data-testid="stMetricLabel"] {
        color: #262730 !important;
    }
    .problem-box {
        background-color: #f0f4fa;
        border-left: 4px solid #1f3864;
        padding: 15px 20px;
        border-radius: 6px;
        margin-bottom: 20px;
        color: #262730 !important;
    }
    .problem-box strong {
        color: #1f3864 !important;
    }
    </style>
""", unsafe_allow_html=True)


# ==================== DATA LOADING ====================
@st.cache_data
def load_data():
    # Auto-generate data if not present (for Streamlit Cloud deploy)
    import os
    if not os.path.exists("data/sales_data.csv"):
        from generate_data import main as generate_main
        generate_main()
    df = pd.read_csv("data/sales_data.csv")
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["weekday"] = df["date"].dt.day_name()
    return df


df = load_data()

# ==================== HEADER ====================
st.title("📊 Sales Operations Analytics Dashboard")
st.markdown(
    """
    <div class="problem-box">
    <strong>🎯 Business Problem:</strong> Operations and BI teams need real-time visibility into sales performance vs. forecast
    to make staffing, inventory, and regional investment decisions. This dashboard analyzes 12 months of multi-region sales
    data to surface trends, deviations, and operational opportunities — enabling data-driven decisions instead of
    reactive ones.
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================== SIDEBAR FILTERS ====================
st.sidebar.header("🔍 Filters")
st.sidebar.markdown("Adjust filters to explore the data:")

# Date range filter
min_date = df["date"].min()
max_date = df["date"].max()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# Region filter
regions = st.sidebar.multiselect(
    "Region",
    options=sorted(df["region"].unique()),
    default=sorted(df["region"].unique()),
)

# Category filter
categories = st.sidebar.multiselect(
    "Product category",
    options=sorted(df["category"].unique()),
    default=sorted(df["category"].unique()),
)

# Channel filter
channels = st.sidebar.multiselect(
    "Sales channel",
    options=sorted(df["channel"].unique()),
    default=sorted(df["channel"].unique()),
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**About this dashboard**\n\n"
    "Built with Python, Pandas, Plotly, and Streamlit. "
    "Uses synthetic data designed to mirror real operational patterns "
    "(seasonality, Q4 peaks, weekend effects, regional variance)."
)
st.sidebar.markdown(
    "**Built by:** Camila Rubio Cuellar  \n"
    "[LinkedIn](https://linkedin.com/in/camila-rubio-cuellar/) · "
    "[GitHub](https://github.com/Rivalry11)"
)

# ==================== APPLY FILTERS ====================
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered = df[
        (df["date"] >= pd.Timestamp(start_date))
        & (df["date"] <= pd.Timestamp(end_date))
        & (df["region"].isin(regions))
        & (df["category"].isin(categories))
        & (df["channel"].isin(channels))
    ]
else:
    filtered = df[
        (df["region"].isin(regions))
        & (df["category"].isin(categories))
        & (df["channel"].isin(channels))
    ]

if filtered.empty:
    st.warning("⚠️ No data matches the selected filters. Adjust filters to see results.")
    st.stop()

# ==================== KPI CARDS ====================
st.markdown("### 📈 Key Performance Indicators")

# Calculate KPIs
total_revenue = filtered["revenue"].sum()
total_transactions = len(filtered)
avg_order_value = filtered["revenue"].mean()

# Forecast accuracy (MAPE-based, calculated at day/region level)
daily_by_region = (
    filtered.groupby(["date", "region"])
    .agg(actual=("revenue", "count"), forecast=("forecast_volume", "first"))
    .reset_index()
)
if len(daily_by_region) > 0:
    daily_by_region["abs_pct_error"] = (
        abs(daily_by_region["actual"] - daily_by_region["forecast"])
        / daily_by_region["actual"]
    )
    mape = daily_by_region["abs_pct_error"].mean() * 100
    forecast_accuracy = max(0, 100 - mape)
else:
    forecast_accuracy = 0

avg_fulfillment = filtered["fulfillment_hours"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total Revenue", f"${total_revenue/1_000_000:.2f}M")
col2.metric("🛒 Transactions", f"{total_transactions:,}")
col3.metric("🎯 Forecast Accuracy", f"{forecast_accuracy:.1f}%",
            help="100% - Mean Absolute Percentage Error between daily forecast and actual volume")
col4.metric("⏱️ Avg Fulfillment Time", f"{avg_fulfillment:.1f} hrs")

st.markdown("---")

# ==================== CHART 1: FORECAST VS ACTUAL (HERO CHART) ====================
st.markdown("### 📉 Forecast vs. Actual Volume")
st.caption(
    "Daily transaction volume (actual) compared against forecasted volume. "
    "Large gaps signal opportunities to improve forecasting models or investigate operational anomalies."
)

daily_data = (
    filtered.groupby(["date", "region"])
    .agg(actual=("revenue", "count"), forecast=("forecast_volume", "first"))
    .reset_index()
    .groupby("date")
    .agg(actual=("actual", "sum"), forecast=("forecast", "sum"))
    .reset_index()
)
# 7-day rolling for smoothing
daily_data["actual_7d"] = daily_data["actual"].rolling(7, min_periods=1).mean()
daily_data["forecast_7d"] = daily_data["forecast"].rolling(7, min_periods=1).mean()

fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=daily_data["date"], y=daily_data["forecast_7d"],
    name="Forecast (7-day avg)", line=dict(color="#9E9E9E", dash="dash", width=2),
))
fig1.add_trace(go.Scatter(
    x=daily_data["date"], y=daily_data["actual_7d"],
    name="Actual (7-day avg)", line=dict(color="#1f3864", width=3),
))
fig1.update_layout(
    height=400,
    hovermode="x unified",
    xaxis_title="Date",
    yaxis_title="Transactions per day",
    plot_bgcolor="white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
fig1.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
fig1.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
st.plotly_chart(fig1, use_container_width=True)

# ==================== CHART 2 & 3: REGION & CATEGORY ====================
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 🌎 Revenue by Region")
    region_rev = filtered.groupby("region")["revenue"].sum().reset_index().sort_values("revenue", ascending=True)
    fig2 = px.bar(
        region_rev, x="revenue", y="region", orientation="h",
        color="revenue", color_continuous_scale="Blues",
        labels={"revenue": "Revenue (USD)", "region": ""},
    )
    fig2.update_layout(height=350, plot_bgcolor="white", coloraxis_showscale=False)
    fig2.update_traces(texttemplate="$%{x:,.0f}", textposition="outside")
    st.plotly_chart(fig2, use_container_width=True)

with col_right:
    st.markdown("### 📦 Revenue by Category")
    cat_rev = filtered.groupby("category")["revenue"].sum().reset_index()
    fig3 = px.pie(
        cat_rev, values="revenue", names="category", hole=0.5,
        color_discrete_sequence=px.colors.sequential.Blues_r,
    )
    fig3.update_layout(height=350, legend=dict(orientation="v", x=1, y=0.5))
    st.plotly_chart(fig3, use_container_width=True)

# ==================== CHART 4: HEATMAP ====================
st.markdown("### 🔥 Operational Heatmap: Sales Intensity by Day")
st.caption("Identifies peak operational periods — critical for staffing, inventory, and capacity planning.")

heatmap_data = (
    filtered.groupby(["weekday", "channel"])
    .size()
    .reset_index(name="transactions")
)
weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
heatmap_pivot = heatmap_data.pivot(index="channel", columns="weekday", values="transactions")
heatmap_pivot = heatmap_pivot.reindex(columns=weekday_order)

fig4 = px.imshow(
    heatmap_pivot,
    color_continuous_scale="Blues",
    aspect="auto",
    labels=dict(color="Transactions"),
    text_auto=".0f",
)
fig4.update_layout(height=300, xaxis_title="", yaxis_title="")
st.plotly_chart(fig4, use_container_width=True)

# ==================== CHART 5: TOP DEVIATIONS TABLE ====================
st.markdown("### ⚠️ Top Forecast Deviations")
st.caption("Days with the largest gap between forecast and actual — these are the cases ops teams should investigate first.")

deviations = daily_data.copy()
deviations["deviation"] = deviations["actual"] - deviations["forecast"]
deviations["deviation_pct"] = (deviations["deviation"] / deviations["forecast"] * 100).round(1)
deviations["abs_deviation_pct"] = deviations["deviation_pct"].abs()
top_dev = deviations.nlargest(10, "abs_deviation_pct")[
    ["date", "forecast", "actual", "deviation", "deviation_pct"]
].copy()
top_dev.columns = ["Date", "Forecast", "Actual", "Deviation", "Deviation %"]
top_dev["Date"] = top_dev["Date"].dt.strftime("%Y-%m-%d")

st.dataframe(
    top_dev.style.format({
        "Forecast": "{:,.0f}",
        "Actual": "{:,.0f}",
        "Deviation": "{:+,.0f}",
        "Deviation %": "{:+.1f}%",
    }),
    use_container_width=True,
    hide_index=True,
)

# ==================== FOOTER ====================
st.markdown("---")
st.markdown(
    """
    #### 🛠️ How this was built
    - **Data:** 450K+ synthetic transactions across 4 regions, 5 categories, 4 channels, 12 months.
      Designed to mirror real operational patterns: seasonality, Q4 holiday peaks, weekend behavior, channel-specific fulfillment.
    - **Stack:** Python · Pandas · Plotly · Streamlit · deployed on Streamlit Community Cloud
    - **Design choices:** Forecast accuracy and deviation tracking modeled after KPIs I used in Workforce Management roles,
      where surfacing volume vs. forecast gaps enabled real operational improvements (e.g., raising occupancy from 20% to 65%
      at IntouchCX by rebalancing staffing against actual demand).
    """
)
