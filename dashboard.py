
import json
from datetime import timedelta

import boto3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from boto3.dynamodb.conditions import Key

# =========================================================
# PAGE CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="AWS IoT Sensor Time-Series Data Analysis",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Automatically rerun the dashboard every 30 seconds to fetch fresh DynamoDB data.
st_autorefresh(interval=30_000, limit=None, key="iot_sensor_auto_refresh")

AWS_PROFILE = "IoTAnalysisUser"
AWS_REGION = "ap-southeast-2"
TABLE_NAME = "IoTSensorData"
DEFAULT_DEVICE = "sensor01"
DEFAULT_THRESHOLD = 30.0

# =========================================================
# STYLING
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;800&family=Space+Grotesk:wght@600;700&display=swap');

.stApp {
  background: radial-gradient(ellipse at 10% 0%, #14394b, transparent 38%),
              radial-gradient(ellipse at 95% 0%, #30204c, transparent 35%),
              linear-gradient(135deg,#071321,#0c1b2b 60%,#15152e);
  color:#f4f8ff;
  font-family:'DM Sans',sans-serif;
}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"] {
  background:linear-gradient(180deg,#11283d,#19172f);
  border-right:1px solid #31516a;
}
h1,h2,h3,h4 {color:#fff !important;font-family:'Space Grotesk',sans-serif;}
p,label {color:#e0eaf6;}
.hero {
  padding:30px;border-radius:22px;margin-bottom:25px;
  background:linear-gradient(115deg,#164d60,#087f88,#483277);
  border:1px solid #58c6c7;
  box-shadow:0 14px 40px #0005;
}
.hero-kicker {color:#9dfff0;font-weight:800;letter-spacing:2px;font-size:12px;}
.hero-title {color:white;font-size:clamp(25px,3vw,40px);font-weight:800;margin:10px 0;}
.hero-subtitle {color:#f0fbff;font-size:15px;}
.card {
  padding:20px;border-radius:18px;min-height:145px;
  border:1px solid #ffffff35;box-shadow:0 9px 25px #0003;
}
.coral {background:linear-gradient(135deg,#b73557,#f36b42);}
.cyan {background:linear-gradient(135deg,#087b91,#2469cb);}
.violet {background:linear-gradient(135deg,#6940bc,#b02ac8);}
.green {background:linear-gradient(135deg,#07866d,#55ad31);}
.card-label {font-size:12px;font-weight:800;letter-spacing:1px;color:white;}
.card-value {font-size:30px;font-weight:800;color:white;margin:12px 0;}
.card-note {font-size:12px;color:#f1f7ff;}
.section-kicker {font-size:11px;font-weight:800;letter-spacing:2px;color:#8ffff0;}
div.stButton > button,div.stDownloadButton > button {
  background:linear-gradient(100deg,#087f88,#236dc1);
  color:white !important;border:1px solid #61d7d1;border-radius:10px;font-weight:700;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input,
[data-baseweb="input"] input {
  background:white !important;color:#17263a !important;
  -webkit-text-fill-color:#17263a !important;caret-color:#087f88 !important;
}
[data-testid="stTextInput"] input::placeholder {
  color:#64748b !important;-webkit-text-fill-color:#64748b !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
  background:white !important;color:#17263a !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] * {
  color:#17263a !important;
}
[data-testid="stNumberInput"] button {background:#eaf1f8 !important;color:#17263a !important;}
[data-testid="stMetric"] {
  background:#132b40;border:1px solid #31516a;border-radius:13px;padding:12px;
}
[data-testid="stMetric"] label,
[data-testid="stMetric"] [data-testid="stMetricValue"] {color:white !important;}
hr {border-color:#31516a;}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DYNAMODB DATA RETRIEVAL
# No cache: every rerun queries DynamoDB again.
# =========================================================
@st.cache_resource
def get_table():
    session = boto3.Session(
        profile_name=AWS_PROFILE,
        region_name=AWS_REGION,
    )
    return session.resource("dynamodb").Table(TABLE_NAME)


def load_sensor_data(device_id):
    table = get_table()
    items = []

    response = table.query(
        KeyConditionExpression=Key("device_id").eq(device_id),
        ScanIndexForward=True,
    )
    items.extend(response.get("Items", []))

    while response.get("LastEvaluatedKey"):
        response = table.query(
            KeyConditionExpression=Key("device_id").eq(device_id),
            ExclusiveStartKey=response["LastEvaluatedKey"],
            ScanIndexForward=True,
        )
        items.extend(response.get("Items", []))

    rows = []

    for item in items:
        sensor = item.get("sensor_data", {})

        if isinstance(sensor, str):
            try:
                sensor = json.loads(sensor)
            except (ValueError, TypeError):
                sensor = {}

        if not isinstance(sensor, dict):
            sensor = {}

        def number(*names):
            for source in (sensor, item):
                for name in names:
                    value = source.get(name)
                    if value is not None:
                        try:
                            return float(value)
                        except (ValueError, TypeError):
                            pass
            return None

        raw_ts = item.get("timestamp", sensor.get("timestamp"))
        ts = pd.NaT

        try:
            raw_ts = float(raw_ts)
            ts = pd.to_datetime(
                raw_ts,
                unit="ms" if raw_ts > 10**11 else "s",
                utc=True,
            )
        except (ValueError, TypeError, OverflowError):
            pass

        rows.append({
            "Device": str(item.get("device_id", device_id)),
            "Timestamp": ts,
            "Temperature (°C)": number("temperature", "temp", "Temperature"),
            "Humidity (%)": number("humidity", "Humidity"),
            "Pressure (hPa)": number("pressure", "Pressure"),
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["Timestamp"] = pd.to_datetime(
            df["Timestamp"], utc=True, errors="coerce"
        )
        df = df.dropna(subset=["Timestamp"])
        df = df.sort_values("Timestamp")
        df = df.drop_duplicates(
            subset=["Device", "Timestamp"], keep="last"
        )

    return df


# =========================================================
# ANOMALY DETECTION
# =========================================================
def detect_anomalies(df, threshold):
    result = df.copy()
    result["Alert"] = "Normal"
    result["Alert reason"] = ""

    temperature = result["Temperature (°C)"]
    high = temperature > threshold

    result.loc[high, "Alert"] = "HIGH TEMPERATURE"
    result.loc[high, "Alert reason"] = (
        f"Temperature exceeds {threshold:.1f} °C"
    )

    # Rolling outlier detection; sort first so order is correct.
    if temperature.notna().sum() >= 10:
        rolling_mean = temperature.rolling(
            10, min_periods=5
        ).mean()
        rolling_std = temperature.rolling(
            10, min_periods=5
        ).std()

        unusual = (
            (temperature - rolling_mean).abs() > 2.5 * rolling_std
        ) & rolling_std.gt(0)

        unusual = unusual & ~high & temperature.notna()
        result.loc[unusual, "Alert"] = "UNUSUAL TREND"
        result.loc[unusual, "Alert reason"] = (
            "Unusual relative to recent temperature readings"
        )

    return result


# =========================================================
# HEADER
# =========================================================
st.markdown("""
<div class="hero">
  <div class="hero-kicker">CLOUD COMPUTING · IOT · DATA ANALYTICS</div>
  <div class="hero-title">🌐 AWS IoT SENSOR ANALYTICS</div>
  <div class="hero-subtitle">
    Time-Series Monitoring · Interactive Graphs · Anomaly Detection
  </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR + MANUAL REFRESH
# =========================================================
st.sidebar.title("🎛️ Dashboard Controls")

device_id = st.sidebar.text_input(
    "DynamoDB device ID",
    value=DEFAULT_DEVICE,
    help="Must match the device_id stored in DynamoDB.",
).strip()

threshold = st.sidebar.number_input(
    "Temperature alert threshold (°C)",
    min_value=-50.0,
    max_value=150.0,
    value=DEFAULT_THRESHOLD,
    step=1.0,
)

window = st.sidebar.selectbox(
    "Graph and summary time window",
    ["Last 1 hour", "Last 24 hours", "Last 7 days", "All history"],
    index=1,
)

refresh = st.sidebar.button("🔄 Fetch latest data", use_container_width=True)

# Refresh is implemented by a full rerun. Data isn't cached.
if refresh:
    st.rerun()

st.sidebar.caption("AWS Region: " + AWS_REGION)
st.sidebar.caption("DynamoDB: " + TABLE_NAME)
st.sidebar.caption("Manual refresh: enabled")

# =========================================================
# LOAD + FILTER
# =========================================================
if not device_id:
    st.warning("Enter a device ID in the sidebar.")
    st.stop()

try:
    with st.spinner("Fetching latest records from DynamoDB..."):
        raw = load_sensor_data(device_id)
except Exception as exc:
    st.error("Could not read DynamoDB data.")
    st.code(str(exc))
    st.info(
        "Check the AWS CLI profile, DynamoDB permissions, region, "
        "table name, and device ID."
    )
    st.stop()

if raw.empty:
    st.warning(f"No readings found for device '{device_id}'.")
    st.info(
        "Start sensor.py and verify the IoT Rule writes the device ID "
        "and timestamp to DynamoDB. You can enter sensor01 to view old data."
    )
    st.stop()

# Select window relative to the latest actual reading.
latest_timestamp = raw["Timestamp"].max()

if window == "Last 1 hour":
    cutoff = latest_timestamp - pd.Timedelta(hours=1)
    filtered = raw[raw["Timestamp"] >= cutoff].copy()
elif window == "Last 24 hours":
    cutoff = latest_timestamp - pd.Timedelta(hours=24)
    filtered = raw[raw["Timestamp"] >= cutoff].copy()
elif window == "Last 7 days":
    cutoff = latest_timestamp - pd.Timedelta(days=7)
    filtered = raw[raw["Timestamp"] >= cutoff].copy()
else:
    filtered = raw.copy()

if filtered.empty:
    st.warning("No readings found in the selected time window.")
    st.stop()

# Summary and alerts are recalculated only from the filtered readings.
result = detect_anomalies(filtered, threshold)
latest = result.iloc[-1]

# =========================================================
# SENSOR OVERVIEW
# =========================================================
st.markdown('<div class="section-kicker">SENSOR OVERVIEW</div>',
            unsafe_allow_html=True)
st.header("✨ Sensor Command Center")

metrics = [
    ("🌡️", "TEMPERATURE", latest["Temperature (°C)"], "°C", "coral"),
    ("💧", "HUMIDITY", latest["Humidity (%)"], "%", "cyan"),
    ("🌀", "PRESSURE", latest["Pressure (hPa)"], "hPa", "violet"),
    ("📡", "READINGS IN WINDOW", len(result), "records", "green"),
]

cols = st.columns(4)

for col, (icon, label, value, unit, color) in zip(cols, metrics):
    shown = "N/A" if pd.isna(value) else (
        f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
    )
    col.markdown(f"""
    <div class="card {color}">
      <div style="font-size:26px">{icon}</div>
      <div class="card-label">{label}</div>
      <div class="card-value">{shown} <span style="font-size:13px">{unit}</span></div>
      <div class="card-note">Current selected window</div>
    </div>
    """, unsafe_allow_html=True)

st.caption(
    f"Latest stored reading: {latest_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')} "
    f"| Total records for device: {len(raw):,} "
    f"| Records in selected window: {len(result):,}"
)

# =========================================================
# SUMMARY + ALERTS
# =========================================================
st.header("🚦 Monitoring and Data Quality")

alerts = result[result["Alert"] != "Normal"]
missing = int(
    result[["Temperature (°C)", "Humidity (%)", "Pressure (hPa)"]]
    .isna().sum().sum()
)

a, b, c = st.columns(3)
a.metric("Readings analyzed", f"{len(result):,}")
b.metric("Readings flagged", f"{len(alerts):,}")
c.metric("Missing measurements", f"{missing:,}")

if len(alerts):
    st.error(
        f"🚨 {len(alerts)} reading(s) flagged in the selected time window. "
        "Review the anomaly table below."
    )
else:
    st.success("No anomalies detected in this selected time window.")

st.header("📊 Statistical Summary")

measures = [
    "Temperature (°C)",
    "Humidity (%)",
    "Pressure (hPa)",
]
summary = result[measures].agg(["mean", "min", "max"]).T
summary.columns = ["Average", "Minimum", "Maximum"]

st.caption(
    f"Readings analyzed: {len(result):,} | "
    f"Latest reading: {latest_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
)
st.dataframe(summary.round(2), use_container_width=True)
st.caption("Statistics are recalculated from the latest loaded data and selected time window.")

# =========================================================
# PLOTLY CHARTS
# =========================================================
st.header("📈 Interactive Time-Series Graphs")
st.caption(
    "Graphs use only the selected time window. Hover for values; "
    "use the toolbar to zoom or download a chart."
)


def draw_chart(column, title, color, unit):
    data = result.dropna(subset=[column]).sort_values("Timestamp")

    if data.empty:
        st.info(f"No valid readings for {title}.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["Timestamp"],
        y=data[column],
        mode="lines+markers",
        name=column,
        line=dict(color=color, width=2.5),
        marker=dict(size=5),
        connectgaps=False,
        hovertemplate="%{x}<br>%{y:.2f} " + unit + "<extra></extra>",
    ))

    if column == "Temperature (°C)":
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="#ff8297",
            annotation_text=f"Alert threshold: {threshold:g}°C",
            annotation_font_color="#ffb4c0",
        )

        flagged = data[data["Alert"] != "Normal"]
        if not flagged.empty:
            fig.add_trace(go.Scatter(
                x=flagged["Timestamp"],
                y=flagged[column],
                mode="markers",
                name="Detected anomaly",
                marker=dict(color="#ff637d", size=11, symbol="diamond"),
                hovertemplate="⚠️ Alert<br>%{x}<br>%{y:.2f} °C<extra></extra>",
            ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=21, color="white")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,22,37,0.85)",
        font=dict(color="#eaf4ff"),
        height=370,
        margin=dict(l=15, r=15, t=65, b=20),
        hovermode="x unified",
        xaxis_title="Timestamp (UTC)",
        yaxis_title=unit,
    )
    fig.update_xaxes(gridcolor="rgba(160,190,220,.15)")
    fig.update_yaxes(gridcolor="rgba(160,190,220,.15)")
    st.plotly_chart(fig, use_container_width=True)


draw_chart("Temperature (°C)", "🌡️ Temperature Trend", "#FF8297", "°C")
draw_chart("Humidity (%)", "💧 Humidity Trend", "#54E6E1", "%")
draw_chart("Pressure (hPa)", "🌀 Pressure Trend", "#B9A1FF", "hPa")

# =========================================================
# ANOMALY TABLE
# =========================================================
st.header("🚨 Anomaly Detection Center")

if alerts.empty:
    st.success("No flagged readings in the selected time window.")
else:
    st.dataframe(
        alerts[
            [
                "Timestamp", "Device", "Temperature (°C)",
                "Humidity (%)", "Pressure (hPa)", "Alert", "Alert reason",
            ]
        ].sort_values("Timestamp", ascending=False),
        use_container_width=True,
    )

    st.download_button(
        "📥 Download anomaly report",
        data=alerts.to_csv(index=False).encode("utf-8"),
        file_name="iot_anomaly_report.csv",
        mime="text/csv",
    )

# =========================================================
# DATA EXPLORER + DOWNLOAD
# =========================================================
st.header("🗂️ Sensor Data Explorer")

filter_choice = st.selectbox(
    "Show records",
    ["All readings", "Only anomalies", "Normal readings"],
)

if filter_choice == "Only anomalies":
    view = result[result["Alert"] != "Normal"]
elif filter_choice == "Normal readings":
    view = result[result["Alert"] == "Normal"]
else:
    view = result

view = view.sort_values("Timestamp", ascending=False)
st.dataframe(view, use_container_width=True, height=350)

st.download_button(
    "⬇️ Download selected data as CSV",
    data=view.to_csv(index=False).encode("utf-8"),
    file_name="aws_iot_sensor_analysis.csv",
    mime="text/csv",
)

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#b4c8dc'>"
    "AWS IoT Sensor Time-Series Data Analysis · "
    "AWS IoT Core · DynamoDB · Python · Pandas · Plotly"
    "</div>",
    unsafe_allow_html=True,
)
