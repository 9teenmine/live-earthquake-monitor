#######################
# Import libraries
import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import requests

#######################
# Page configuration
st.set_page_config(
    page_title="Myanmar Earthquake Dashboard",
    page_icon="🌏",
    layout="wide",
    initial_sidebar_state="expanded"
)

alt.themes.enable("dark")

#######################
# CSS styling (SAME STYLE)
st.markdown("""
<style>
[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}
[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}
[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}
[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
""", unsafe_allow_html=True)

#######################
# LOAD LIVE DATA
@st.cache_data(ttl=600)
def load_earthquake_data():
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"
    data = requests.get(url).json()

    rows = []
    for eq in data["features"]:
        prop = eq["properties"]
        geo = eq["geometry"]

        rows.append({
            "place": prop["place"],
            "time": pd.to_datetime(prop["time"], unit="ms"),
            "magnitude": prop["mag"],
            "depth": geo["coordinates"][2],
            "longitude": geo["coordinates"][0],
            "latitude": geo["coordinates"][1]
        })

    return pd.DataFrame(rows)

df = load_earthquake_data()

#######################
# FILTER MYANMAR REGION
df_mm = df[
    (df["latitude"].between(5, 35)) &
    (df["longitude"].between(85, 110))
]

#######################
# SIDEBAR
with st.sidebar:
    st.title("🌏 Myanmar Earthquake Dashboard")

    min_mag = st.slider("Minimum Magnitude", 0.0, 8.0, 4.5)

    color_theme_list = ['inferno', 'plasma', 'magma', 'viridis', 'cividis']
    selected_color_theme = st.selectbox("Color Theme", color_theme_list)

    if st.button("🔄 Refresh Live Data"):
        st.cache_data.clear()
        st.rerun()

df_mm = df_mm[df_mm["magnitude"] >= min_mag]

#######################
# HEATMAP FUNCTION
def make_heatmap(input_df, input_color_theme):
    df_heat = input_df.copy()
    df_heat["date"] = df_heat["time"].dt.date
    heatmap = alt.Chart(df_heat).mark_rect().encode(
        y=alt.Y('date:O', title="Date"),
        x=alt.X('magnitude:Q', bin=True, title="Magnitude"),
        color=alt.Color('count():Q', scale=alt.Scale(scheme=input_color_theme))
    ).properties(height=300)
    return heatmap

#######################
# DASHBOARD LAYOUT
col = st.columns((1.5, 4.5, 2), gap='medium')

#######################
# LEFT COLUMN — METRICS
with col[0]:
    st.markdown("#### Live Stats")

    total_quakes = len(df_mm)
    strongest = df_mm["magnitude"].max() if not df_mm.empty else 0
    avg_depth = round(df_mm["depth"].mean(), 1) if not df_mm.empty else 0

    st.metric("Total Quakes", total_quakes)
    st.metric("Strongest", strongest)
    st.metric("Avg Depth (km)", avg_depth)

#######################
# CENTER — MAP + HEATMAP
with col[1]:
    st.markdown("#### Live Epicenter Map")

    fig_map = px.scatter_geo(
        df_mm,
        lat="latitude",
        lon="longitude",
        color="magnitude",
        size="magnitude",
        hover_name="place",
        hover_data=["depth", "time"],
        color_continuous_scale=selected_color_theme,
        projection="natural earth"
    )

    fig_map.update_layout(template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0), height=400)
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown("#### Activity Heatmap")
    st.altair_chart(make_heatmap(df_mm, selected_color_theme), use_container_width=True)

#######################
# RIGHT COLUMN — TABLE
with col[2]:
    st.markdown("#### Recent Earthquakes")

    df_table = df_mm.sort_values("time", ascending=False)

    st.dataframe(
        df_table,
        column_order=("time", "place", "magnitude", "depth"),
        hide_index=True,
        use_container_width=True
    )

    with st.expander("About", expanded=True):
        st.write("""
        - Live Data Source: USGS Earthquake API  
        - Updates every 10 minutes  
        - Filtered for Myanmar region  
        """)
