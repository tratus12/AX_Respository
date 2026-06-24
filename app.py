import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os
import datetime

# 1. 페이지 설정
st.set_page_config(
    page_title="Pioneer-1 Robot Advanced Sensor Dashboard",
    page_icon="🤖",
    layout="wide"
)

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

# -----------------------------------------------------------------------------
# 1. 시뮬레이션 데모 데이터 생성기 (원본 파일 누락 시 대체)
# -----------------------------------------------------------------------------
def generate_simulated_robot_data():
    """파일이 존재하지 않을 때 로봇의 주행 특징을 완벽히 모사하는 고품질 데이터셋을 생성합니다."""
    dfs = []
    
    # 1. MOVE.DATA 시뮬레이션
    for trial in range(1, 4):
        n_steps = 100
        time_seq = np.linspace(0, 15, n_steps)
        battery = np.linspace(12.6, 12.4 - trial*0.05, n_steps)
        
        # 점점 장애물에 접근하는 시나리오 (소나 값 감소)
        sonar_base = np.linspace(4000, 300 + (trial*100), n_steps)
        
        # 전진 제어
        trans_vel = np.full(n_steps, 200.0)
        trans_vel[-15:] = 0.0 # 정지
        
        row_dict = {
            "TRIAL-ID": trial,
            "DESCRIPTION": f"Steady Move forward to wall (Simulated Trial {trial})",
            "TIME-SECS": time_seq,
            "BATTERY-LEVEL": battery,
            "HEADING": np.full(n_steps, 90.0), # 북향 고정
            "R-WHEEL-VEL": trans_vel,
            "L-WHEEL-VEL": trans_vel,
            "TRANS-VEL": trans_vel,
            "ROT-VEL": np.zeros(n_steps),
            "R-STALL": np.zeros(n_steps),
            "L-STALL": np.zeros(n_steps),
            "ROBOT-STATUS": np.full(n_steps, 1),
            "GRIP-STATE": np.zeros(n_steps),
            "GRIP-FRONT-BEAM": np.zeros(n_steps),
            "GRIP-REAR-BEAM": np.zeros(n_steps),
            "GRIP-BUMPER": np.zeros(n_steps),
            "MODE": "move"
        }
        
        for s in range(7):
            row_dict[f"SONAR-{s}"] = sonar_base + np.random.randn(n_steps)*50
            
        # 비주얼 데이터 타겟 접근 시그널
        row_dict["VIS-A-DIST"] = np.linspace(5000, 1000, n_steps)
        row_dict["VIS-A-AREA"] = np.linspace(10, 500, n_steps)
        
        for v in ["A", "B", "C"]:
            if f"VIS-{v}-DIST" not in row_dict:
                row_dict[f"VIS-{v}-DIST"] = np.full(n_steps, 10000.0)
                row_dict[f"VIS-{v}-AREA"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-X"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-Y"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-H"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-W"] = np.zeros(n_steps)
            
        dfs.append(pd.DataFrame(row_dict))
        
    # 2. TURN.DATA 시뮬레이션
    for trial in range(4, 7):
        n_steps = 120
        time_seq = np.linspace(0, 18, n_steps)
        battery = np.linspace(12.4, 12.2, n_steps)
        heading = np.linspace(90, 90 + 360, n_steps) % 360  # 360도 제자리 회전
        
        row_dict = {
            "TRIAL-ID": trial,
            "DESCRIPTION": f"Stationary full spin test (Simulated Trial {trial})",
            "TIME-SECS": time_seq,
            "BATTERY-LEVEL": battery,
            "HEADING": heading,
            "R-WHEEL-VEL": np.full(n_steps, 150.0),
            "L-WHEEL-VEL": np.full(n_steps, -150.0),
            "TRANS-VEL": np.zeros(n_steps),
            "ROT-VEL": np.full(n_steps, 30.0),
            "R-STALL": np.zeros(n_steps),
            "L-STALL": np.zeros(n_steps),
            "ROBOT-STATUS": np.full(n_steps, 1),
            "GRIP-STATE": np.zeros(n_steps),
            "GRIP-FRONT-BEAM": np.zeros(n_steps),
            "GRIP-REAR-BEAM": np.zeros(n_steps),
            "GRIP-BUMPER": np.zeros(n_steps),
            "MODE": "turn"
        }
        for s in range(7):
            row_dict[f"SONAR-{s}"] = np.full(n_steps, 2000.0) + np.sin(np.radians(heading))*800
            
        for v in ["A", "B", "C"]:
            row_dict[f"VIS-{v}-DIST"] = np.full(n_steps, 10000.0)
            row_dict[f"VIS-{v}-AREA"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-X"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-Y"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-H"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-W"] = np.zeros(n_steps)
            
        dfs.append(pd.DataFrame(row_dict))
        
    # 3. GRIPPER.DATA 시뮬레이션
    for trial in range(7, 10):
        n_steps = 150
        time_seq = np.linspace(0, 25, n_steps)
        battery = np.linspace(12.3, 12.0, n_steps)
        
        # 그리퍼 미션 특화 시퀀스
        grip_state = np.zeros(n_steps)
        front_beam = np.zeros(n_steps)
        rear_beam = np.zeros(n_steps)
        
        # 후반부에 물체 접근 및 집어 들기
        front_beam[60:80] = 1.0
        rear_beam[75:100] = 1.0
        grip_state[80:] = 2.0  # Gripper Closed
        
        # 스탈 이벤트 강제 주입 (테스트 및 보고서용)
        r_stall = np.zeros(n_steps)
        if trial == 8:
            r_stall[40:45] = 1.0
        
        row_dict = {
            "TRIAL-ID": trial,
            "DESCRIPTION": f"Object capture and lifting (Simulated Trial {trial})",
            "TIME-SECS": time_seq,
            "BATTERY-LEVEL": battery,
            "HEADING": np.full(n_steps, 180.0),
            "R-WHEEL-VEL": np.linspace(100, 0, n_steps),
            "L-WHEEL-VEL": np.linspace(100, 0, n_steps),
            "TRANS-VEL": np.linspace(100, 0, n_steps),
            "ROT-VEL": np.zeros(n_steps),
            "R-STALL": r_stall,
            "L-STALL": np.zeros(n_steps),
            "ROBOT-STATUS": np.full(n_steps, 1),
            "GRIP-STATE": grip_state,
            "GRIP-FRONT-BEAM": front_beam,
            "GRIP-REAR-BEAM": rear_beam,
            "GRIP-BUMPER": np.zeros(n_steps),
            "MODE": "gripper"
        }
        for s in range(7):
            row_dict[f"SONAR-{s}"] = np.linspace(3000, 150, n_steps)
            
        for v in ["A", "B", "C"]:
            row_dict[f"VIS-{v}-DIST"] = np.linspace(4000, 50, n_steps)
            row_dict[f"VIS-{v}-AREA"] = np.linspace(20, 900, n_steps)
            row_dict[f"VIS-{v}-X"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-Y"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-H"] = np.zeros(n_steps)
            row_dict[f"VIS-{v}-W"] = np.zeros(n_steps)
            
        dfs.append(pd.DataFrame(row_dict))
        
    return pd.concat(dfs, ignore_index=True)


@st.cache_data
def load_data():
    dfs = []
    files = {
        "move": os.path.join(BASE, "move.data", "MOVE.DATA"),
        "turn": os.path.join(BASE, "turn.data", "TURN.DATA"),
        "gripper": os.path.join(BASE, "gripper.data", "GRIPPER.DATA"),
    }
    
    file_found = False
    for mode, path in files.items():
        if os.path.exists(path):
            file_found = True
            df = pd.read_csv(path, header=None, names=COLUMNS, quotechar='"')
            df["MODE"] = mode
            dfs.append(df)
            
    if file_found:
        combined = pd.concat(dfs, ignore_index=True)
        for col in COLUMNS[2:]:
            combined[col] = pd.to_numeric(combined[col], errors="coerce")
        return combined, "실제 하드웨어 파일 로드 완료"
    else:
        # 가상 데이터 생성 제공
        return generate_simulated_robot_data(), "로봇 주행 가상 시뮬레이터 구동 중"

data, data_source_message = load_data()

# -----------------------------------------------------------------------------
# 2. 로봇 헤딩 및 전진 속도를 활용한 궤적 산출 (Odometry Integration)
# -----------------------------------------------------------------------------
def compute_trajectory(trial_df):
    """로봇 전진 속도와 방향각 각도를 시계열 적분하여 2D 실시간 도면 경로를 계산합니다."""
    t = trial_df["TIME-SECS"].values
    trans_vel = trial_df["TRANS-VEL"].values # mm/s
    heading = np.radians(trial_df["HEADING"].values) # Convert to radians
    
    x, y = [0.0], [0.0]
    for i in range(1, len(t)):
        dt = t[i] - t[i-1]
        # 중간 속도 기반 주행 델타 계산
        distance = trans_vel[i-1] * dt
        dx = distance * np.cos(heading[i-1])
        dy = distance * np.sin(heading[i-1])
        x.append(x[-1] + dx)
        y.append(y[-1] + dy)
        
    trial_df["Odom-X"] = x
    trial_df["Odom-Y"] = y
    return trial_df

# -----------------------------------------------------------------------------
# 3. 사이드바 및 필터 컨트롤러
# -----------------------------------------------------------------------------
st.sidebar.title("🤖 Pioneer-1 Robot Remote Control")
st.sidebar.caption(data_source_message)
st.sidebar.markdown("---")

mode_options = ["All"] + sorted(data["MODE"].unique().tolist())
selected_mode = st.sidebar.selectbox("Activity Type (로봇 미션 분류)", mode_options)

filtered = data if selected_mode == "All" else data[data["MODE"] == selected_mode]
trial_ids = sorted(filtered["TRIAL-ID"].unique().tolist())
selected_trial = st.sidebar.selectbox("Trial ID (주행 시도 선택)", trial_ids)

# 선택된 트라이얼 데이터 확보
trial_data = filtered[filtered["TRIAL-ID"] == selected_trial].copy()
trial_data = compute_trajectory(trial_data) # 2D 궤적 주입

description = trial_data["DESCRIPTION"].iloc[0] if len(trial_data) else "—"

st.sidebar.markdown("---")
st.sidebar.markdown(f"**실행 미션 설명:** \n`{description}`")
st.sidebar.markdown(f"**원시 수집 패킷 수:** {len(trial_data)} rows")

# 주행 지속 시간 구하기
duration = 0.0
if len(trial_data) > 0:
    duration = trial_data['TIME-SECS'].max() - trial_data['TIME-SECS'].min()
st.sidebar.markdown(f"**총 기동 지속 시간:** {duration:.1f} s")

# -----------------------------------------------------------------------------
# 4. 실시간 상태 기반 미션 정량 평가 로직 (CBM / Evaluation Rule)
# -----------------------------------------------------------------------------
# 1) 누적 이동거리 (m 단위)
dt_seq = trial_data['TIME-SECS'].diff().fillna(0)
integrated_dist = (trial_data['TRANS-VEL'] * dt_seq).sum() / 1000.0 # mm -> m

# 2) 배터리 전력 소모율 (V/s)
v_start = trial_data['BATTERY-LEVEL'].iloc[0] if len(trial_data) else 0.0
v_end = trial_data['BATTERY-LEVEL'].iloc[-1] if len(trial_data) else 0.0
battery_drain = (v_start - v_end)

# 3) 회전 및 구동 장애 진단
r_stalls = int(trial_data["R-STALL"].sum())
l_stalls = int(trial_data["L-STALL"].sum())
total_stalls = r_stalls + l_stalls

# 4) 그리퍼 조작 성공 여부 판별
gripper_success = "미작동(N/A)"
if (trial_data["GRIP-STATE"] == 2).any():
    gripper_success = "성공 (Captured)"
elif selected_mode == "gripper":
    gripper_success = "실패 (Grip Timeout)"

# 5) 종합 미션 스코어 계산 (100점 만점 페널티 방식)
mission_score = 100
reason_penalty = []
if total_stalls > 0:
    penalty = min(total_stalls * 10, 40)
    mission_score -= penalty
    reason_penalty.append(f"구동부 스탈 장애 페널티 (-{penalty}점)")
if battery_drain > 0.8:
    mission_score -= 15
    reason_penalty.append("전력 방전율 임계값 초과 페널티 (-15점)")
if selected_mode == "gripper" and gripper_success == "실패 (Grip Timeout)":
    mission_score -= 30
    reason_penalty.append("목표물 포획 실패 페널티 (-30점)")

# -----------------------------------------------------------------------------
# 5. 대시보드 메인 UI 구성
# -----------------------------------------------------------------------------
st.title("🤖 Pioneer-1 Mobile Robot Sensor Dashboard")
st.caption("고성능 소나 스캔 레이더, 오도메트리 주행 궤적 역설계, 미션 자동 점수화 및 리포팅 시스템")

# 상단 핵심 지표 스케일러 카드
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("배터리 전압 상태", f"{trial_data['BATTERY-LEVEL'].mean():.2f} V", f"-{battery_drain:.2f}V 소모")
k2.metric("누적 주행 거리", f"{integrated_dist:.2f} m", "오도메트리 추정")
k3.metric("평균 전진 속도", f"{trial_data['TRANS-VEL'].mean():.1f} mm/s")
k4.metric("좌/우 바퀴 스탈 장애", f"{total_stalls} 건", f"R: {r_stalls} / L: {l_stalls} 회")
k5.metric("종합 미션 달성도", f"{mission_score} 점", f"{'우수(Excellent)' if mission_score >= 80 else '점검필요(Needs Check)'}")

st.markdown("---")

tab1, tab2, tab3 = st.tabs([
    "🎯 실시간 주행 궤적 및 센서 분석 (Radar & Odometry)", 
    "📈 센서 시계열 정밀 추세 (Sensor Time-Series)", 
    "📋 로봇 미션 평가 및 종합 상태 보고서 (Robot CBM Report)"
])

# --- TAB 1: 주행 궤적 및 소나 맵핑 ---
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📍 Odometry 기반 로봇 주행 궤적 복원 (2D Map)")
        st.write("로봇의 헤딩 방향과 속도를 시간축으로 삼각함수 적분하여 실시간으로 복원한 상대 이동 경로입니다.")
        fig_traj = px.line(trial_data, x="Odom-X", y="Odom-Y", text="TIME-SECS",
                           labels={"Odom-X": "X Position (mm)", "Odom-Y": "Y Position (mm)"})
        fig_traj.update_traces(textposition="top right", mode="lines+markers", marker=dict(size=4))
        fig_traj.update_layout(height=360, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig_traj, use_container_width=True)
        
    with col2:
        st.subheader("📡 고성능 소나 레이더 스캔 범위 (Sonar Radar)")
        st.write("소나 센서 각도별 반사 거리를 폴라(Polar) 극좌표계에 가시화한 최근 진입 장벽 패턴입니다.")
        sonar_cols = [f"SONAR-{i}" for i in range(7)]
        angles = [90, 15, 7.5, 0, -7.5, -15, -90]
        sonar_labels = [f"S{i} ({a}°)" for i, a in enumerate(angles)]
        sonar_vals = [trial_data[c].mean() for c in sonar_cols]
        # 루프 닫기 처리
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
            height=360,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

# --- TAB 2: 센서 시계열 정밀 추세 ---
with tab2:
    st.subheader("📊 다차원 로봇 상태 피드백 시계열")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.write("⚙️ **바퀴 모터별 회전 속도 추적**")
        fig_vel = go.Figure()
        fig_vel.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["R-WHEEL-VEL"],
                                     name="Right Wheel", line=dict(color="#e63946")))
        fig_vel.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["L-WHEEL-VEL"],
                                     name="Left Wheel", line=dict(color="#457b9d")))
        fig_vel.add_trace(go.Scatter(x=trial_data["TIME-SECS"], y=trial_data["TRANS-VEL"],
                                     name="Trans Vel", line=dict(color="#2a9d8f", dash="dot")))
        fig_vel.update_layout(xaxis_title="Time (s)", yaxis_title="Velocity (mm/s)",
                              legend=dict(orientation="h"), margin=dict(l=0, r=0, t=10, b=0), height=280)
        st.plotly_chart(fig_vel, use_container_width=True)
    
    with col_t2:
        st.write("🧭 **로봇 헤딩 각도 변화량 추적**")
        fig_hdg = px.line(trial_data, x="TIME-SECS", y="HEADING",
                          labels={"TIME-SECS": "Time (s)", "HEADING": "Heading (°)"},
                          color_discrete_sequence=["#f4a261"])
        fig_hdg.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=280)
        st.plotly_chart(fig_hdg, use_container_width=True)

    st.markdown("---")
    
    col_t3, col_t4 = st.columns([2, 1])
    with col_t3:
        st.write("👁️ **비주얼 트래킹 타깃 거리 및 검출 면적 변동**")
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
        
    with col_t4:
        st.write("🦾 **그리퍼 광센서 및 상태 흐름**")
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

# --- TAB 3: 로봇 미션 및 상태 분석서 (CBM Report) ---
with tab3:
    st.subheader("📋 Pioneer-1 모바일 로봇 주행 평가 기술서")
    st.write("로봇의 센서 계측 및 모터 주행 피드백 결과를 취합하여 부서 공유용 보고서를 다운로드할 수 있는 영역입니다.")
    
    st.markdown("#### 1. 미션 기본 정보 입력")
    rep_col1, rep_col2, rep_col3 = st.columns(3)
    with rep_col1:
        test_date = st.date_input("미션 주행 테스트 수행일", datetime.date.today())
    with rep_col2:
        operator_name = st.text_input("담당 오퍼레이터 엔지니어", value="스마트로봇연구소 김개발 선임연구원")
    with rep_col3:
        target_mission_goal = st.text_input("설정 미션 목표", value=f"Pioneer-1 {selected_mode.upper()} 주행 알고리즘 검증")
        
    st.markdown("#### 2. 진단 및 세부 검토 의견 입력")
    
    # 미션 달성 점수에 따른 종합 소견 기본 세팅
    if mission_score >= 80:
        default_opinion = "모터의 토크 배출 및 오도메트리 전력 소모의 효율성이 높으며 우수한 주행 안정성을 지니고 있습니다. 별도의 정비나 파라미터 튜닝 없이 상위 자율주행 모듈과의 연동 테스트를 진행해도 무방합니다."
        rec_status = "이상 없음 (Pass)"
    elif mission_score >= 60:
        default_opinion = "바퀴 스탈(Stall) 한계 부근 마찰 손실 또는 배터리 전압의 다소 급격한 소모가 발견됩니다. 주행 패턴을 최적화하고 속도 제어 가속 구간의 파라미터를 보정할 것을 권고합니다."
        rec_status = "가속 파라미터 튜닝 필요 (Warning)"
    else:
        default_opinion = "스탈 장애가 과도하게 누적되었거나 그리퍼 미션을 안전 범위 시간 내에 마무리하지 못했습니다. 제어 모듈 하드웨어 하네스 연결 접촉 상태 점검 및 배터리 전지 노후화 테스트가 시급히 요구됩니다."
        rec_status = "긴급 하드웨어 점검 요망 (Action Needed)"
        
    engineer_opinion = st.text_area("시스템 분석 종합 코멘트 (수정 가능)", value=default_opinion, height=100)
    
    rep_col4, rep_col5 = st.columns(2)
    with rep_col4:
        next_action = st.text_input("권장 차기 조치 계획", value=rec_status)
    with rep_col5:
        score_rating_slider = st.slider("미션 수행 평점 (1.0 ~ 5.0 만점)", min_value=1.0, max_value=5.0, value=float(max(1.0, min(5.0, (mission_score/20.0)))), step=0.5)

    # 마크다운 기반 보고서 전문 조립
    reason_lines = "\n".join([f"- {r}" for r in reason_penalty]) if reason_penalty else "- 해당 없음 (무감점 합격)"
    
    report_content = f"""# 🤖 Pioneer-1 Mobile Robot Mission Analysis Report

- **미션 테스트 일자**: {test_date}
- **미션 고유 ID**: Trial {selected_trial} ({selected_mode.upper()})
- **담당 수석 엔지니어**: {operator_name}
- **실험 알고리즘**: {target_mission_goal}

---

## 1. 텔레메트리 핵심 분석 지표 (Summary)
- **주행 미션 달성 점수**: {mission_score} / 100점 (수행 평점: {score_rating_slider:.1f} / 5.0)
- **가장 긴 주행 지속시간**: {duration:.1f} 초
- **오도메트리 누적 거리**: {integrated_dist:.2f} m
- **배터리 종단 방전 상태**: {v_start:.2f}V -> {v_end:.2f}V (방전 델타: {battery_drain:.3f}V)

---

## 2. 모터 및 센서 안전 한도 검토
- **휠 스탈 장애 검출**: {total_stalls} 회 발생 (오도메트리 마찰 경고)
- **그리퍼 상태 검증**: {gripper_success}
- **점수 감점 요인 상세**:
{reason_lines}

---

## 3. 엔지니어 종합 시스템 평가 의견
- **상태 분석 코멘트**:
  "{engineer_opinion}"

- **차기 유지보수 및 파라미터 계획**: {next_action}

--------------------------------------------------
본 보고서는 Pioneer-1 로봇 센서 데이터 정밀 분석기를 통해 실시간 추출되었습니다.
"""

    st.markdown("---")
    st.markdown("#### 3. 발행 보고서 최종 프리뷰 (Report Preview)")
    st.markdown(report_content)

    # 마크다운 형태 다운로드 버튼 생성
    st.download_button(
        label="📥 로봇 분석 보고서(.txt) 다운로드",
        data=report_content,
        file_name=f"Pioneer1_Trial_Report_{selected_trial}_{test_date}.txt",
        mime="text/plain"
    )

# 원시 데이터 하단 엑스팬더
st.markdown("---")
with st.expander("Raw Trial Data Grid (실시간 원시 레코드 데이터 뷰어)"):
    display_cols = ["TIME-SECS", "BATTERY-LEVEL", "HEADING", "R-WHEEL-VEL", "L-WHEEL-VEL", "TRANS-VEL", "ROT-VEL", "ROBOT-STATUS"] + sonar_cols
    st.dataframe(trial_data[display_cols].reset_index(drop=True), use_container_width=True)
