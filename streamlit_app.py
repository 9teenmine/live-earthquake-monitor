############################
# IMPORT LIBRARIES
############################
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

############################
# PAGE CONFIGURATION
############################
st.set_page_config(
    page_title="Live Earthquake Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

############################
# GLOBAL STYLES (CSS)
############################
st.markdown("""
<style>
[data-testid="block-container"] {
    padding: 1rem 2rem 0rem 2rem;
    margin-bottom: -7rem;
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

############################
# DATA LOADING (CACHED)
############################
@st.cache_data(ttl=600)
def load_earthquake_data():
    """Fetch live earthquake data from USGS API"""
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

############################
# SIDEBAR CONTROLS
############################
with st.sidebar:
    st.title("📡 Live Earthquake Monitor")

    region = st.radio(
        "Geographic Scope",
        ["Myanmar", "Global"],
        horizontal=True
    )

    view_mode = st.radio(
        "Visualization Type",
        ["Epicenter Map", "Activity Timeline"]
    )

    min_mag = st.slider(
        "Minimum Earthquake Magnitude",
        0.0, 8.0, 4.5
    )

    color_theme = st.selectbox(
        "Map Color Scale",
        ['inferno', 'plasma', 'magma', 'viridis', 'cividis']
    )
    st.markdown(
        """
        <div style="font-size:0.8rem; color:gray;">
            Developer: Htut Myat Oo <br> 
            Version: 1.0.0 <br>
            Last Updated: 02 Feb 2026
        </div>
        """,
        unsafe_allow_html=True
    )

############################
# DATA FILTERING
############################
if region == "Myanmar":
    df_filtered = df[
        df["latitude"].between(5, 35) &
        df["longitude"].between(85, 110)
    ]
else:
    df_filtered = df.copy()

df_filtered = df_filtered[df_filtered["magnitude"] >= min_mag]

############################
# HELPER FUNCTIONS
############################
def time_ago(ts):
    """Convert timestamp to human-readable relative time"""
    delta = pd.Timestamp.now() - ts
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "Just now"
    elif seconds < 3600:
        return f"{seconds // 60} min ago"
    elif seconds < 86400:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h} h {m} min ago"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days > 1 else ''} ago"


def simplify_table(df):
    """Prepare compact table for UI"""
    table = df.copy()
    table["Time"] = table["time"].dt.strftime("%d %b %H:%M")
    table["Location"] = table["place"].str.split(",").str[0]
    table["Magnitude"] = table["magnitude"].round(1)
    table["Depth (km)"] = table["depth"].round(0)

    return table[["Time", "Location", "Magnitude", "Depth (km)"]]


def last_quake_status(ts):
    """Return Streamlit status + label based on recency"""
    hours = (pd.Timestamp.now() - ts).total_seconds() / 3600
    label = time_ago(ts)

    if hours < 1:
        return "error", label
    elif hours < 6:
        return "warning", label
    else:
        return "success", label


def get_most_active_region(df):
    """Most frequent location in last 24 hours"""
    recent = df[df["time"] >= pd.Timestamp.now() - pd.Timedelta(hours=24)]
    if recent.empty:
        return "No recent activity"

    return (
        recent["place"]
        .str.split(",")
        .str[0]
        .value_counts()
        .idxmax()
    )

def get_trend_arrow(df):
    """Compare quake count: today vs yesterday"""
    now = pd.Timestamp.now()

    today = df[df["time"] >= now - pd.Timedelta(hours=24)]
    yesterday = df[
        (df["time"] < now - pd.Timedelta(hours=24)) &
        (df["time"] >= now - pd.Timedelta(hours=48))
    ]

    if yesterday.empty:
        return "→", "No comparison data"

    if len(today) > len(yesterday):
        return "↑", "Increasing activity"
    elif len(today) < len(yesterday):
        return "↓", "Decreasing activity"
    else:
        return "→", "Stable activity"

############################
# TIME SERIES DATA
############################
df_ts = df_filtered.copy()
df_ts["date"] = df_ts["time"].dt.date

df_daily = (
    df_ts.groupby("date")
    .agg(
        quake_count=("magnitude", "count"),
        avg_magnitude=("magnitude", "mean")
    )
    .reset_index()
)

def make_time_series(df):
    fig = px.line(
        df,
        x="date",
        y="quake_count",
        markers=True,
        labels={
            "date": "Date",
            "quake_count": "Number of Earthquakes"
        },
        template="plotly_dark"
    )
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
    return fig

############################
# DASHBOARD LAYOUT
############################
col_left, col_center, col_right = st.columns((1.5, 4.5, 2), gap="medium")

############################
# LEFT COLUMN — METRICS
############################
with col_left:
    st.markdown("#### Real-Time Summary")

    if not df_filtered.empty:
        latest = df_filtered.sort_values("time", ascending=False).iloc[0]
        status, label = last_quake_status(latest["time"])
    else:
        status, label = "success", "No data"

    st.metric("Total Earthquakes", len(df_filtered))
    st.metric("Maximum Magnitude", df_filtered["magnitude"].max() if not df_filtered.empty else 0)
    st.metric("Average Depth (km)", round(df_filtered["depth"].mean(), 1) if not df_filtered.empty else 0)

    st.markdown("**Last Earthquake**")
    getattr(st, status)(f"⏱️ {label}")

    if st.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

############################
# CENTER COLUMN — MAP / TIMELINE + TABLE
############################
with col_center:
    title_region = "Myanmar 🇲🇲" if region == "Myanmar" else "Global 🌍"

    if view_mode == "Epicenter Map":
        st.markdown(f"#### Earthquake Epicenter Distribution ({title_region})")

        fig_map = px.scatter_geo(
            df_filtered,
            lat="latitude",
            lon="longitude",
            color="magnitude",
            size="magnitude",
            hover_name="place",
            hover_data=["depth", "time"],
            color_continuous_scale=color_theme,
            projection="natural earth",
            template="plotly_dark"
        )

        fig_map.update_layout(height=450, margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

    else:
        st.markdown(f"#### Daily Earthquake Activity ({title_region})")
        st.plotly_chart(make_time_series(df_daily), use_container_width=True)

    st.markdown("#### Recent Seismic Events")
    st.dataframe(
        simplify_table(df_filtered.sort_values("time", ascending=False).head(12)),
        hide_index=True,
        use_container_width=True
    )

############################
# RIGHT COLUMN — INSIGHTS
############################
with col_right:
    st.markdown("#### Key Insights")

    st.markdown("📍 **Highest Seismic Activity (Last 24 Hours)**")
    st.info(get_most_active_region(df_filtered))

    arrow, text = get_trend_arrow(df_filtered)
    st.markdown("📉 **Seismic Activity Trend**")
    st.metric("Last 24 Hrs vs Previous 24 Hrs", arrow, text)

    st.caption(f"Based on earthquakes in the last 48 hours • Region: {region}")

    with st.expander("About", expanded=True):
        st.write("""
        - Data Source: [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/)
        - **Epicenter Map**: geographic distribution of earthquake locations by magnitude
        - **Activity Timeline**: daily frequency of recorded seismic events
        - **Regional Filter**: focused analysis for Myanmar or global comparison
        - Data updates automatically every 10 minutes
        """)
