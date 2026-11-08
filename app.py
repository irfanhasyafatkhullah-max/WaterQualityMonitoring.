
import streamlit as st
import paho.mqtt.client as mqtt
import json
import pandas as pd
import threading
import uuid

from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================

st.set_page_config(
    page_title="Water Quality Dashboard",
    page_icon="💧",
    layout="wide"
)


# ==========================================
# 2. KONFIGURASI MQTT
# ==========================================

MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "waterquality/esp32/data"

def mqtt_connection():

    client_id = "streamlit-" + uuid.uuid4().hex[:10]

    client = mqtt.Client(
        client_id=client_id,
        protocol=mqtt.MQTTv311
    )

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    return client


# ==========================================
# 3. CSS DESIGN
# ==========================================

st.markdown("""
<style>

.stApp {
    background-color: #f4f7fb;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

.main-title {
    font-size: 34px;
    font-weight: 800;
    color: #17324d;
}

.subtitle {
    color: #718096;
    font-size: 15px;
    margin-bottom: 25px;
}

.metric-card {
    background: white;
    padding: 22px;
    border-radius: 15px;
    border: 1px solid #e7edf5;
    box-shadow: 0 3px 12px rgba(0,0,0,0.04);
}

.metric-label {
    color: #718096;
    font-size: 14px;
    font-weight: 600;
}

.metric-value {
    color: #17324d;
    font-size: 30px;
    font-weight: 800;
    margin-top: 8px;
}

.metric-unit {
    color: #718096;
    font-size: 13px;
}

.section-title {
    color: #17324d;
    font-size: 22px;
    font-weight: 700;
    margin-top: 15px;
}

.status-online {
    background: #dcfce7;
    color: #15803d;
    padding: 10px 15px;
    border-radius: 10px;
    font-weight: 600;
}

.status-offline {
    background: #fee2e2;
    color: #b91c1c;
    padding: 10px 15px;
    border-radius: 10px;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# 4. MQTT CONNECTION
# ==========================================

@st.cache_resource
def mqtt_connection():

    data_history = deque(maxlen=200)
    lock = threading.Lock()

    status = {
        "connected": False
    }

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            status["connected"] = True
            client.subscribe(MQTT_TOPIC)
            print("MQTT Connected!")
        else:
            status["connected"] = False
            print("MQTT Connection Failed:", rc)

    def on_disconnect(client, userdata, rc):
        status["connected"] = False
        print("MQTT Disconnected:", rc)

    def on_message(client, userdata, msg):

        try:
            payload = json.loads(msg.payload.decode())

            data = {
                "Waktu": datetime.now(ZoneInfo("Asia/Jakarta")),
                "pH": payload.get("ph"),
                "Temperature": payload.get("temperature"),
                "Turbidity": payload.get("turbidity"),
                "TDS": payload.get("tds")
            }

            with lock:
                data_history.append(data)

        except Exception as e:
            print("Error membaca data:", e)

    client = mqtt.Client(
        client_id="streamlit-water-quality-dashboard"
    )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()

    return client, data_history, lock, status


client, data_history, lock, status = mqtt_connection()


# ==========================================
# 5. SIDEBAR
# ==========================================

st.sidebar.title("💧 Water Quality")
st.sidebar.caption("Monitoring Control Panel")

st.sidebar.divider()

st.sidebar.subheader("Dashboard Settings")

max_data = st.sidebar.slider(
    "Jumlah data pada grafik",
    min_value=10,
    max_value=200,
    value=50,
    step=10
)

st.sidebar.divider()

st.sidebar.subheader("MQTT Configuration")

st.sidebar.write("**Broker:**")
st.sidebar.code(MQTT_BROKER)

st.sidebar.write("**Topic:**")
st.sidebar.code(MQTT_TOPIC)

st.sidebar.write("**Port:**", MQTT_PORT)

st.sidebar.divider()

st.sidebar.caption("ESP32 + Wokwi + EMQX + Streamlit")


# ==========================================
# 6. HEADER DASHBOARD
# ==========================================

st.markdown(
    '<div class="main-title">💧 Water Quality Monitoring</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Real-Time IoT Monitoring System | ESP32 & MQTT'
    '</div>',
    unsafe_allow_html=True
)


# ==========================================
# 7. DASHBOARD CONTENT
# ==========================================

@st.fragment(run_every=2)
def dashboard():

    # Mengambil data dengan aman
    with lock:
        data = list(data_history)

    # Status MQTT
    if status["connected"]:
        st.markdown(
            '<div class="status-online">● MQTT Connected</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="status-offline">● MQTT Disconnected / Connecting...</div>',
            unsafe_allow_html=True
        )

    st.write("")

    if len(data) == 0:
        st.info("Menunggu data sensor dari ESP32...")
        return

    df = pd.DataFrame(data)

    # Mengubah data sensor menjadi numerik
    sensor_columns = [
        "pH", "Temperature", "Turbidity", "TDS"
    ]

    for column in sensor_columns:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    latest = df.iloc[-1]

    # ======================================
    # SENSOR METRICS
    # ======================================

    st.markdown(
        '<div class="section-title">Latest Sensor Readings</div>',
        unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)

    metrics = [
        (col1, "🧪 pH", latest["pH"], ""),
        (col2, "🌡️ Temperature", latest["Temperature"], "°C"),
        (col3, "💧 Turbidity", latest["Turbidity"], "NTU"),
        (col4, "⚡ TDS", latest["TDS"], "ppm")
    ]

    for col, label, value, unit in metrics:

        with col:
            if pd.notna(value):
                display_value = f"{value:.2f}"
            else:
                display_value = "N/A"

            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{display_value}</div>
                <div class="metric-unit">{unit}</div>
            </div>
            """, unsafe_allow_html=True)

    # ======================================
    # DATA SUMMARY
    # ======================================

    st.write("")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Data", len(df))
    col2.metric(
        "Last Update",
        df["Waktu"].iloc[-1].strftime("%H:%M:%S")
    )
    col3.metric(
        "Monitoring",
        "Active" if status["connected"] else "Offline"
    )

    # ======================================
    # SENSOR CHART
    # ======================================

    st.markdown(
        '<div class="section-title">Sensor Data Visualization</div>',
        unsafe_allow_html=True
    )

    chart_option = st.selectbox(
        "Pilih parameter sensor",
        ["pH", "Temperature", "Turbidity", "TDS"]
    )

    chart_df = df.tail(max_data)

    chart_data = chart_df.set_index("Waktu")[
        [chart_option]
    ].dropna()

    if not chart_data.empty:
        st.line_chart(
            chart_data,
            height=350,
            use_container_width=True
        )
    else:
        st.info("Belum ada data valid untuk parameter ini.")

    # ======================================
    # ALL SENSOR CHARTS
    # ======================================

    with st.expander("Lihat seluruh grafik sensor"):

        for sensor in sensor_columns:

            st.write(f"**{sensor}**")

            sensor_data = chart_df.set_index("Waktu")[
                [sensor]
            ].dropna()

            if not sensor_data.empty:
                st.line_chart(
                    sensor_data,
                    height=200,
                    use_container_width=True
                )

    # ======================================
    # DATA HISTORY
    # ======================================

    st.markdown(
        '<div class="section-title">Data History</div>',
        unsafe_allow_html=True
    )

    display_df = df.sort_values(
        "Waktu", ascending=False
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # ======================================
    # DOWNLOAD CSV
    # ======================================

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download Data CSV",
        data=csv,
        file_name="water_quality_history.csv",
        mime="text/csv"
    )

    st.caption(
        f"Menampilkan {min(len(df), max_data)} data terakhir pada grafik. "
        f"Buffer menyimpan maksimal 200 data di RAM."
    )


dashboard()
