import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

st.set_page_config(page_title="Pioneer-1 Robot Dashboard", layout="wide", page_icon="🤖")

COLUMNS = [
    "TRIAL-ID", "DESCRIPTION", "TIME-SECS", "BATTERY-LEVEL",
    "SONAR-0", "SONAR-1", "SONAR-2", "SONAR-3", "SONAR-4", "SONAR-5", "SONAR-6",
    "HEADING", "R-WHEEL-VEL", "L-WHEEL-VEL", "TRANS-VEL", "ROT-VEL",
    "R-STALL", "L-STALL", "ROBOT-STATUS",
    "GRIP-STATE", "GRIP-FRONT-BEAM", "GRIP-REAR-BEAM", "GRIP-BUMPER",
    "VIS-A-AREA", "VIS-A-X", "VIS-A-Y", "VIS-A-H", "VIS-A-W", "VIS-A-DIST",
    "VIS-B-AREA", "VIS-B-X", "VIS-B-Y", "VIS-B-H", "VIS-B-W", "VIS-B-DIST",
    "VIS-C-AREA", "VIS-C-X", "VIS-C-Y", "VIS-C-H", "VIS-C-W", "VIS-C-DIST",
]

BASE = os.path.dirname(__file__)

@st.cache_data
def load_data():
    dfs = []
    files = {
        "move": os.path.join(BASE, "move.data", "MOVE.DATA"),
        "turn": os.path.join(BASE, "turn.data", "TURN.DATA"),
        "gripper": os.path.join(BASE, "gripper.data", "GRIPPER.DATA"),
    }
    for mode, path in files.items():
        if os.path.exists(path):
            df = pd.read_csv(path, header=None, names=COLUMNS, quotechar='"')
            df["MODE"] = mode
            dfs.append(df)
    combined = pd.concat(dfs, ignore_index=True)
    for col in COLUMNS[2:]:
        combined[col] = pd.to_numeric(combined[col], errors="coerce")
    return combined

data = load_data()

# ── Sidebar ─────────────────────────────────────────────────────────────────
st.sidebar.title("🤖 Pioneer-1 Robot")
st.sidebar.markdown("---")

mode_options = ["All"] + sorted(data["MODE"].unique().tolist())
selected_mode = st.sidebar.selectbox("Activity Type", mode_options)

filtered = data if selected_mode == "All" else data[data["MODE"] == selected_mode]
trial_ids = sorted(filtered["TRIAL-ID"].unique().tolist())
selected_trial = st.sidebar.selectbox("Trial ID", trial_ids)

trial_data = filtered[filtered["TRIAL-ID"] == selected_trial].copy()
description = trial_data["DESCRIPTION"].iloc[0] if len(trial_data) else "—"

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Description:**  \n`{description}`")
st.sidebar.markdown(f"**Observations:** {len(trial_data)}")
st.sidebar.markdown(f"**Duration:** {trial_data['TIME-SECS'].max() - trial_data['TIME-SECS'].min():.1f} s")

# ── Header ──────────────────────────────────────────────────────────────────
st.title("Pioneer-1 Mobile Robot Sensor Dashboard")

# ── Top KPI strip ───────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Battery (V)", f"{trial_data['BATTERY-LEVEL'].mean():.2f}")
k2.metric("Avg Trans Vel (mm/s)", f"{trial_data['TRANS-VEL'].mean():.1f}")
k3.metric("Avg Rot Vel (°/s)", f"{trial_data['ROT-VEL'].mean():.1f}")
k4.metric("R-Stall events", int(trial_data["R-STALL"].sum()))
k5.metric("L-Stall events", int(trial_data["L-STALL"].sum()))

st.markdown("---")

# ── Row 1: Sonar radar + Velocity ───────────────────────────────────────────
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Sonar Snapshot (mean, mm)")
    sonar_cols = [f"SONAR-{i}" for i in range(7)]
    angles = [90, 15, 7.5, 0, -7.5, -15, -90]
    sonar_labels = [f"S{i} ({a}°)" for i, a in enumerate(angles)]
    sonar_vals = [trial_data[c].mean() for c in sonar_cols]
    # Close the radar
    sonar_vals_closed = sonar_vals + [sonar_vals[0]]
    sonar_labels_closed = sonar_labels + [sonar_labels[0]]

    fig_radar = go.Figure(go.Scatterpolar(
        r=sonar_vals_closed,
        theta=sonar_labels_closed,
        fill="toself",
        line_color="#00b4d8",
        fillcolor="rgba(0,180,216,0.25)",
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5300])),
        margin=dict(l=20, r=20, t=20, b=20),
        height=320,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

with col2:
    st.subheader("Wheel Velocities Over Time")
    fig_vel = go.Figure()
    fig_vel.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["R-WHEEL-VEL"],
                                 name="Right Wheel", line=dict(color="#e63946")))
    fig_vel.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["L-WHEEL-VEL"],
                                 name="Left Wheel", line=dict(color="#457b9d")))
    fig_vel.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["TRANS-VEL"],
                                 name="Trans Vel", line=dict(color="#2a9d8f", dash="dot")))
    fig_vel.update_layout(xaxis_title="Time (s)", yaxis_title="Velocity (mm/s)",
                          legend=dict(orientation="h"), margin=dict(l=0, r=0, t=10, b=0), height=320)
    st.plotly_chart(fig_vel, use_container_width=True)

# ── Row 2: Heading + Sonar time-series ──────────────────────────────────────
col3, col4 = st.columns([1, 2])

with col3:
    st.subheader("Heading Over Time")
    fig_hdg = px.line(trial_data, x="TIME-SECS", y="HEADING",
                      labels={"TIME-SECS": "Time (s)", "HEADING": "Heading (°)"},
                      color_discrete_sequence=["#f4a261"])
    fig_hdg.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
    st.plotly_chart(fig_hdg, use_container_width=True)

with col4:
    st.subheader("Sonar Readings Over Time")
    fig_sonar = go.Figure()
    colors = px.colors.qualitative.Plotly
    for i, col in enumerate(sonar_cols):
        # Clip max-range readings so they don't dominate
        vals = trial_data[col].clip(upper=5000)
        fig_sonar.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=vals,
                                       name=sonar_labels[i], line=dict(color=colors[i % len(colors)])))
    fig_sonar.update_layout(xaxis_title="Time (s)", yaxis_title="Distance (mm)",
                            legend=dict(orientation="h", font=dict(size=10)),
                            margin=dict(l=0, r=0, t=10, b=0), height=280)
    st.plotly_chart(fig_sonar, use_container_width=True)

# ── Row 3: Visual channels + Gripper/Status ──────────────────────────────────
st.markdown("---")
col5, col6 = st.columns([2, 1])

with col5:
    st.subheader("Visual Channel A — Object Distance & Area")
    fig_vis = make_subplots(specs=[[{"secondary_y": True}]])
    vis_dist = trial_data["VIS-A-DIST"].clip(upper=5000)
    fig_vis.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=vis_dist,
                                 name="VIS-A Distance (mm)", line=dict(color="#e63946")), secondary_y=False)
    fig_vis.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["VIS-A-AREA"],
                                 name="VIS-A Area (px)", line=dict(color="#2a9d8f", dash="dash")), secondary_y=True)
    fig_vis.update_yaxes(title_text="Distance (mm)", secondary_y=False)
    fig_vis.update_yaxes(title_text="Area (px)", secondary_y=True)
    fig_vis.update_xaxes(title_text="Time (s)")
    fig_vis.update_layout(legend=dict(orientation="h"), margin=dict(l=0, r=0, t=10, b=0), height=280)
    st.plotly_chart(fig_vis, use_container_width=True)

with col6:
    st.subheader("Robot Status & Gripper")
    fig_status = make_subplots(rows=3, cols=1, shared_xaxes=True,
                               subplot_titles=["Robot Status", "Grip State", "Grip Beams"],
                               row_heights=[0.33, 0.33, 0.34])
    fig_status.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["ROBOT-STATUS"],
                                    name="Status", line=dict(color="#e63946"), showlegend=False), row=1, col=1)
    fig_status.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["GRIP-STATE"],
                                    name="Grip State", line=dict(color="#457b9d"), showlegend=False), row=2, col=1)
    fig_status.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["GRIP-FRONT-BEAM"],
                                    name="Front Beam", line=dict(color="#f4a261"), showlegend=False), row=3, col=1)
    fig_status.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["GRIP-REAR-BEAM"],
                                    name="Rear Beam", line=dict(color="#2a9d8f"), showlegend=False), row=3, col=1)
    fig_status.update_xaxes(title_text="Time (s)", row=3, col=1)
    fig_status.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=280)
    st.plotly_chart(fig_status, use_container_width=True)

# ── Row 4: Summary table ─────────────────────────────────────────────────────
with st.expander("Raw Trial Data (first 200 rows)"):
    display_cols = ["TIME-SECS", "BATTERY-LEVEL"] + sonar_cols + ["HEADING", "R-WHEEL-VEL", "L-WHEEL-VEL", "TRANS-VEL", "ROT-VEL", "ROBOT-STATUS"]
    st.dataframe(trial_data[display_cols].head(200).reset_index(drop=True), use_container_width=True)

# ── Dataset summary in sidebar ───────────────────────────────────────────────
with st.sidebar.expander("Dataset Summary"):
    st.markdown(f"**Total rows:** {len(data):,}")
    for m in ["move", "turn", "gripper"]:
        n_trials = data[data["MODE"] == m]["TRIAL-ID"].nunique()
        st.markdown(f"- **{m}:** {n_trials} trials")
