import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from scipy.fft import rfft, rfftfreq
from scipy.io import loadmat

# 페이지 기본 설정
st.set_page_config(
    page_title="CWRU 베어링 진동 분석 대시보드",
    page_icon="⚙️",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. 신호 처리 및 특징 추출 함수 (Colab 코드 이식)
# -----------------------------------------------------------------------------
def calculate_features(signal):
    """신호의 주요 통계적 특징값을 추출합니다."""
    signal = np.asarray(signal).ravel()
    rms = np.sqrt(np.mean(signal ** 2))
    peak = np.max(np.abs(signal))
    kurtosis = stats.kurtosis(signal, fisher=False)
    skewness = stats.skew(signal)
    crest_factor = peak / rms if rms > 0 else np.nan
    std = np.std(signal)
    mean_abs = np.mean(np.abs(signal))
    return {
        "mean": np.mean(signal),
        "std": std,
        "rms": rms,
        "peak": peak,
        "kurtosis": kurtosis,
        "skewness": skewness,
        "crest_factor": crest_factor,
        "mean_abs": mean_abs,
    }

def compute_fft(signal, fs):
    """신호의 FFT(고속 푸리에 변환) 주파수 스펙트럼을 계산합니다."""
    signal = np.asarray(signal).ravel()
    signal = signal - np.mean(signal)
    n = len(signal)
    window = np.hanning(n)
    spectrum = np.abs(rfft(signal * window)) / n
    freq = rfftfreq(n, 1 / fs)
    return freq, spectrum

def window_features(signal, fs, window_sec=0.2, step_sec=0.1):
    """일정 구간(윈도우)을 이동하며 시간에 따른 특징값 추세를 계산합니다."""
    signal = np.asarray(signal).ravel()
    window = int(fs * window_sec)
    step = int(fs * step_sec)
    rows = []
    for start in range(0, len(signal) - window + 1, step):
        seg = signal[start:start + window]
        rows.append({
            "time_sec": start / fs,
            **calculate_features(seg),
        })
    return pd.DataFrame(rows)

def generate_demo_signal(fs, duration, state="normal"):
    """업로드된 파일이 없을 때 테스트할 데모 신호를 생성합니다."""
    t = np.arange(int(fs * duration)) / fs
    # 기본 회전 주파수 30Hz 및 노이즈
    signal = np.sin(2 * np.pi * 30 * t) * 0.1 + np.random.randn(len(t)) * 0.05
    if state == "fault":
        # 결함 주파수 성분 및 충격성 노이즈(Kurtosis 증가) 추가
        fault_pulse = np.sin(2 * np.pi * 150 * t) * np.exp(-t * 50)
        fault_signal = np.zeros_like(signal)
        fault_signal[::int(fs/10)] = 2.5 # 주기적 충격 추가
        signal += fault_pulse + fault_signal + np.random.randn(len(t)) * 0.15
    return signal

# -----------------------------------------------------------------------------
# 2. UI 및 사이드바 설정
# -----------------------------------------------------------------------------
st.title("⚙️ CWRU 베어링 진동 데이터 분석 대시보드")
st.caption("Time-domain 통계 특징, FFT 스펙트럼, CBM 진단 로직을 포함한 대시보드입니다.")

st.sidebar.header("📁 데이터 설정")
fs = st.sidebar.number_input("샘플링 주파수 (Hz)", min_value=1000, value=12000, step=1000)

upload_file = st.sidebar.file_uploader(".mat 파일을 업로드하세요 (CWRU 형식)", type=["mat"])

if upload_file is not None:
    # MAT 파일 파싱 로직
    try:
        mat_data = loadmat(upload_file)
        keys = [k for k in mat_data.keys() if ('DE_time' in k or 'FE_time' in k or 'time' in k) and not k.startswith("__")]
        if not keys:
            st.sidebar.error("MAT 파일에서 적절한 시간축 데이터를 찾지 못했습니다.")
            st.stop()
        signal = mat_data[keys[0]].ravel()
        st.sidebar.success(f"파일 로드 완료! (데이터 크기: {len(signal)})")
    except Exception as e:
        st.sidebar.error(f"파일 읽기 오류: {str(e)}")
        st.stop()
else:
    # 데모 데이터 제공
    st.sidebar.info("💡 업로드된 파일이 없어 **데모 데이터**를 사용합니다.")
    demo_type = st.sidebar.radio("데모 신호 종류 선택", ["정상 (Normal)", "결함 (Fault)"])
    state = "normal" if "정상" in demo_type else "fault"
    signal = generate_demo_signal(fs, duration=10.0, state=state)

st.sidebar.markdown("---")
st.sidebar.header("🚨 CBM 진단 임계값")
rms_threshold = st.sidebar.slider("RMS 임계값", min_value=0.01, max_value=0.50, value=0.15, step=0.01)
kurtosis_threshold = st.sidebar.slider("Kurtosis 임계값", min_value=3.0, max_value=10.0, value=5.0, step=0.5)
crest_threshold = st.sidebar.slider("Crest Factor 임계값", min_value=3.0, max_value=10.0, value=4.0, step=0.5)

# -----------------------------------------------------------------------------
# 3. 데이터 분석 처리
# -----------------------------------------------------------------------------
# 1) 전체 특징 추출
overall_features = calculate_features(signal)

# 2) 윈도우 기반 트렌드 추출
with st.spinner('구간별 특징값을 계산 중입니다...'):
    trend_df = window_features(signal, fs, window_sec=0.2, step_sec=0.1)

# 3) 진단 로직 적용
def diagnose(row):
    reasons = []
    if row["rms"] > rms_threshold: reasons.append("RMS 증가")
    if row["kurtosis"] > kurtosis_threshold: reasons.append("충격성 증가")
    if row["crest_factor"] > crest_threshold: reasons.append("Crest Factor 증가")
    
    if len(reasons) >= 2: return "위험 (Danger)", ", ".join(reasons)
    if len(reasons) == 1: return "주의 (Warning)", reasons[0]
    return "정상 (Normal)", "-"

trend_df[["diagnosis", "reason"]] = trend_df.apply(lambda row: pd.Series(diagnose(row)), axis=1)

# -----------------------------------------------------------------------------
# 4. 메인 대시보드 렌더링
# -----------------------------------------------------------------------------
# 상단 KPI 메트릭 요약
col1, col2, col3, col4 = st.columns(4)
col1.metric("전체 RMS", f"{overall_features['rms']:.4f}", 
            delta="임계값 초과!" if overall_features['rms'] > rms_threshold else "정상",
            delta_color="inverse")
col2.metric("전체 Kurtosis", f"{overall_features['kurtosis']:.2f}",
            delta="임계값 초과!" if overall_features['kurtosis'] > kurtosis_threshold else "정상",
            delta_color="inverse")
col3.metric("전체 Crest Factor", f"{overall_features['crest_factor']:.2f}",
            delta="임계값 초과!" if overall_features['crest_factor'] > crest_threshold else "정상",
            delta_color="inverse")
col4.metric("분석 구간 수", f"{len(trend_df)} 구간")

st.markdown("---")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📈 시계열 및 주파수 분석 (Waveform & FFT)", "📉 시간대별 특징 추세 (Trends)", "🚨 진단 결과 요약 (Diagnosis)"])

with tab1:
    st.subheader("Time Waveform (시계열 파형)")
    # 브라우저 성능을 위해 앞 1초 데이터만 플로팅
    plot_len = min(len(signal), fs * 1) 
    t_axis = np.arange(plot_len) / fs
    fig_time = px.line(x=t_axis, y=signal[:plot_len], labels={'x': 'Time (s)', 'y': 'Amplitude'})
    fig_time.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_time, use_container_width=True)

    st.subheader("Frequency Spectrum (FFT)")
    freq, spectrum = compute_fft(signal, fs)
    mask = freq <= 1000 # 최대 1000Hz 까지만 표시
    fig_fft = px.line(x=freq[mask], y=spectrum[mask], labels={'x': 'Frequency (Hz)', 'y': 'Amplitude'})
    fig_fft.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_fft, use_container_width=True)

with tab2:
    st.subheader("구간별 RMS 추세")
    fig_rms = px.line(trend_df, x='time_sec', y='rms', labels={'time_sec': 'Time (s)', 'rms': 'RMS'})
    fig_rms.add_hline(y=rms_threshold, line_dash="dash", line_color="red", annotation_text="Threshold")
    st.plotly_chart(fig_rms, use_container_width=True)

    col_k, col_c = st.columns(2)
    with col_k:
        st.subheader("Kurtosis 추세")
        fig_kurt = px.line(trend_df, x='time_sec', y='kurtosis', labels={'time_sec': 'Time (s)'})
        fig_kurt.add_hline(y=kurtosis_threshold, line_dash="dash", line_color="red")
        st.plotly_chart(fig_kurt, use_container_width=True)
    with col_c:
        st.subheader("Crest Factor 추세")
        fig_crest = px.line(trend_df, x='time_sec', y='crest_factor', labels={'time_sec': 'Time (s)'})
        fig_crest.add_hline(y=crest_threshold, line_dash="dash", line_color="red")
        st.plotly_chart(fig_crest, use_container_width=True)

with tab3:
    st.subheader("진단 상태 분포")
    diag_counts = trend_df['diagnosis'].value_counts().reset_index()
    diag_counts.columns = ['진단 상태', '구간 수']
    
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        fig_pie = px.pie(diag_counts, values='구간 수', names='진단 상태', 
                         color='진단 상태', 
                         color_discrete_map={"정상 (Normal)": "green", "주의 (Warning)": "orange", "위험 (Danger)": "red"})
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_d2:
        st.write("상세 진단 내역 (처음 20개 구간)")
        st.dataframe(trend_df[["time_sec", "rms", "kurtosis", "crest_factor", "diagnosis", "reason"]].head(20), use_container_width=True)
        
    st.info("""
    **CBM(상태기반정비) 해석 가이드**
    - **RMS**: 전체적인 진동 에너지 증가를 나타내며, 주로 베어링의 전반적인 마모를 의미합니다.
    - **Kurtosis & Crest Factor**: 베어링 초기 결함(예: 국부적인 스크래치)으로 인해 발생하는 '충격성' 신호를 감지하는 데 유리합니다.
    - 임계값을 초과하는 상태가 지속되면 설비 점검을 지시해야 합니다.
    """)
