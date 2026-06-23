import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from scipy.fft import rfft, rfftfreq
from scipy.io import loadmat
import datetime

# 페이지 기본 설정
st.set_page_config(
    page_title="CWRU 베어링 진동 분석 및 종합 진단 시스템",
    page_icon="⚙️",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 1. 신호 처리 및 특징 추출 함수
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
    """업로드된 파일이 없을 때 테스트할 세분화된 데모 신호를 생성합니다."""
    t = np.arange(int(fs * duration)) / fs
    # 기본 모터 회전 주파수 (30Hz)와 백그라운드 화이트 노이즈
    signal = np.sin(2 * np.pi * 30 * t) * 0.08 + np.random.randn(len(t)) * 0.04
    
    if state == "inner":
        # 내륜 결함 시뮬레이션: 고주파 통과 시 회전 주파수로 맥동(진폭 변조)
        carrier = np.sin(2 * np.pi * 350 * t)
        modulator = (1 + np.sin(2 * np.pi * 30 * t)) * 0.5
        impacts = np.zeros_like(t)
        impacts[::int(fs/8.5)] = 1.8  # 내륜 통과 주파수 유사 성분
        signal += (carrier * modulator) * 0.2 + impacts * np.exp(-t%0.12 * 40) + np.random.randn(len(t)) * 0.08
    elif state == "outer":
        # 외륜 결함 시뮬레이션: 외륜 고정점으로 인한 규칙적인 날카로운 충격 신호
        impacts = np.zeros_like(t)
        impacts[::int(fs/5.2)] = 2.2  # 외륜 통과 주파수 유사 성분
        signal += impacts * np.exp(-t%0.19 * 60) + np.random.randn(len(t)) * 0.12
    elif state == "normal":
        pass
    return signal

# -----------------------------------------------------------------------------
# 2. UI 및 사이드바 설정
# -----------------------------------------------------------------------------
st.title("⚙️ CWRU 베어링 상태 기반 정비(CBM) 진단 시스템")
st.caption("진동 시계열 물리 지표 분석, FFT 가속 주파수 분해, 자동 판정 알고리즘 및 종합 보고서 발행 시스템")

st.sidebar.header("📁 데이터 분석 제어")
fs = st.sidebar.number_input("샘플링 주파수 (Hz)", min_value=1000, value=12000, step=1000)

upload_file = st.sidebar.file_uploader(".mat 파일을 업로드하세요 (CWRU 형식)", type=["mat"])

file_name_label = "Demo_Dataset"
if upload_file is not None:
    try:
        mat_data = loadmat(upload_file)
        keys = [k for k in mat_data.keys() if ('DE_time' in k or 'FE_time' in k or 'time' in k) and not k.startswith("__")]
        if not keys:
            st.sidebar.error("MAT 파일에서 적절한 시간축 데이터를 찾지 못했습니다.")
            st.stop()
        signal = mat_data[keys[0]].ravel()
        file_name_label = upload_file.name
        st.sidebar.success(f"파일 로드 완료! ({file_name_label})")
    except Exception as e:
        st.sidebar.error(f"파일 읽기 오류: {str(e)}")
        st.stop()
else:
    st.sidebar.info("💡 업로드된 파일이 없어 **시뮬레이션 데모 데이터**를 사용합니다.")
    demo_type = st.sidebar.radio("데모 신호 상태 선택", ["정상 상태 (Normal)", "내륜 결함 상태 (Inner Ring Fault)", "외륜 결함 상태 (Outer Ring Fault)"])
    if "정상" in demo_type:
        state = "normal"
    elif "내륜" in demo_type:
        state = "inner"
    else:
        state = "outer"
    signal = generate_demo_signal(fs, duration=10.0, state=state)
    file_name_label = f"Demo_{state.upper()}_Signal"

st.sidebar.markdown("---")
st.sidebar.header("🚨 경고 임계값 설정 (Thresholds)")
rms_threshold = st.sidebar.slider("RMS 임계값 (전체 에너지 수준)", min_value=0.01, max_value=0.60, value=0.15, step=0.01)
kurtosis_threshold = st.sidebar.slider("Kurtosis 임계값 (충격성 예리도)", min_value=3.0, max_value=10.0, value=5.0, step=0.5)
crest_threshold = st.sidebar.slider("Crest Factor 임계값 (피크 대비 비율)", min_value=3.0, max_value=10.0, value=4.5, step=0.5)

# -----------------------------------------------------------------------------
# 3. 실시간 통계 연산 및 진단 처리
# -----------------------------------------------------------------------------
overall_features = calculate_features(signal)

with st.spinner('구간 분할 및 시간축 특징 융합 추세를 계산 중입니다...'):
    trend_df = window_features(signal, fs, window_sec=0.2, step_sec=0.1)

# 진단 함수 정의
def diagnose(row):
    reasons = []
    if row["rms"] > rms_threshold: reasons.append("RMS 증가 (구조적 손상)")
    if row["kurtosis"] > kurtosis_threshold: reasons.append("Kurtosis 증가 (충격성 결함 발생)")
    if row["crest_factor"] > crest_threshold: reasons.append("Crest Factor 증가 (초기 박리 우려)")
    
    if len(reasons) >= 2: return "위험 (Danger)", ", ".join(reasons)
    if len(reasons) == 1: return "주의 (Warning)", reasons[0]
    return "정상 (Normal)", "-"

trend_df[["diagnosis", "reason"]] = trend_df.apply(lambda row: pd.Series(diagnose(row)), axis=1)

# 전체 판정 결과 종합 도출
danger_ratio = (trend_df["diagnosis"] == "위험 (Danger)").mean() * 100
warning_ratio = (trend_df["diagnosis"] == "주의 (Warning)").mean() * 100

if danger_ratio > 15:
    final_status = "위험 (Danger)"
    status_color = "red"
elif (danger_ratio + warning_ratio) > 20:
    final_status = "주의 (Warning)"
    status_color = "orange"
else:
    final_status = "정상 (Normal)"
    status_color = "green"

# -----------------------------------------------------------------------------
# 4. 메인 대시보드 UI 및 시각화 구성
# -----------------------------------------------------------------------------
# 종합 판정 결과 헤더 배너
st.markdown(f"""
<div style="background-color:rgba({255 if status_color=='red' else (251 if status_color=='orange' else 220)}, 
             {230 if status_color=='red' else (241 if status_color=='orange' else 245)}, 
             {230 if status_color=='red' else (219 if status_color=='orange' else 220)}, 0.3);
            border-left: 8px solid {status_color}; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
    <h3 style="margin: 0; color: {status_color};">🛡️ 종합 진단 결과: {final_status}</h3>
    <p style="margin: 5px 0 0 0; font-size: 0.95rem; color: #333;">
        전체 신호 대비 경고 구간 점유율: 위험 구간 {danger_ratio:.1f}%, 주의 구간 {warning_ratio:.1f}%. 정기 모니터링을 통한 추세 관찰이 요구됩니다.
    </p>
</div>
""", unsafe_allow_html=True)

# KPI 대시보드 카드 배치
col1, col2, col3, col4 = st.columns(4)
col1.metric("종합 실효값 (RMS)", f"{overall_features['rms']:.4f} G", 
            delta="기준치 초과" if overall_features['rms'] > rms_threshold else "안정 상태",
            delta_color="inverse" if overall_features['rms'] > rms_threshold else "normal")
col2.metric("최대 첨도 (Kurtosis)", f"{overall_features['kurtosis']:.2f}",
            delta="급격한 충격 감지" if overall_features['kurtosis'] > kurtosis_threshold else "정상 분포",
            delta_color="inverse" if overall_features['kurtosis'] > kurtosis_threshold else "normal")
col3.metric("크레스트 팩터", f"{overall_features['crest_factor']:.2f}",
            delta="박리 의심" if overall_features['crest_factor'] > crest_threshold else "안정 분포",
            delta_color="inverse" if overall_features['crest_factor'] > crest_threshold else "normal")
col4.metric("시계열 최대 지크값 (Peak)", f"{overall_features['peak']:.3f} G")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 파형 및 고속 스펙트럼 (Signal & FFT)", 
    "📉 시간 흐름별 지표 추세 (Feature Trends)", 
    "🚨 통계 판정 분포 (Diagnosis)",
    "📋 CBM 예산 연계 진단 보고서 (CBM Report)"
])

# --- TAB 1: 신호 및 주파수 상세 분석 ---
with tab1:
    st.subheader("Time Waveform (원시 진동 신호 1.0초 구간)")
    plot_len = min(len(signal), fs * 1) 
    t_axis = np.arange(plot_len) / fs
    fig_time = px.line(x=t_axis, y=signal[:plot_len], labels={'x': 'Time (s)', 'y': 'Acceleration Amplitude (G)'})
    fig_time.update_layout(height=300, margin=dict(l=20, r=20, t=10, b=10))
    st.plotly_chart(fig_time, use_container_width=True)

    col_fft_ctrl, col_fft_plot = st.columns([1, 3])
    with col_fft_ctrl:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.write("🎯 **주파수 분석 정밀 필터**")
        max_freq_limit = st.slider("최대 시각화 주파수 범위 (Hz)", min_value=100, max_value=int(fs/2), value=1500, step=100)
        st.info("💡 **주파수 도메인 진단 가이드**:\n- 0~200Hz: 축 정렬 불량 및 언밸런스 지점\n- 200~1000Hz: 베어링 국부적 표면 고장 지점")
    with col_fft_plot:
        st.subheader("Frequency Spectrum (FFT 결과)")
        freq, spectrum = compute_fft(signal, fs)
        mask = freq <= max_freq_limit
        fig_fft = px.line(x=freq[mask], y=spectrum[mask], labels={'x': 'Frequency (Hz)', 'y': 'Amplitude Spectral Density'})
        fig_fft.update_layout(height=300, margin=dict(l=20, r=20, t=10, b=10))
        st.plotly_chart(fig_fft, use_container_width=True)

# --- TAB 2: 통계적 특징 추세 차트 ---
with tab2:
    st.subheader("구간 단위 물리적 지표 추적 (Trend Analytics)")
    st.write("200ms 단위로 계산된 이동식 물리 파라미터들이 진단 기준선(임계값)을 초과하는 패턴을 추적합니다.")
    
    fig_rms = px.line(trend_df, x='time_sec', y='rms', title='RMS (전체적인 진동 에너지 규모)', labels={'time_sec': '시간 (s)', 'rms': 'RMS (G)'})
    fig_rms.add_hline(y=rms_threshold, line_dash="dash", line_color="red", annotation_text=f"경고 한계선: {rms_threshold:.2f}")
    st.plotly_chart(fig_rms, use_container_width=True)

    col_k, col_c = st.columns(2)
    with col_k:
        fig_kurt = px.line(trend_df, x='time_sec', y='kurtosis', title='Kurtosis (돌발 격파 예리도)', labels={'time_sec': '시간 (s)'})
        fig_kurt.add_hline(y=kurtosis_threshold, line_dash="dash", line_color="red", annotation_text=f"첨도 한계선: {kurtosis_threshold:.1f}")
        st.plotly_chart(fig_kurt, use_container_width=True)
    with col_c:
        fig_crest = px.line(trend_df, x='time_sec', y='crest_factor', title='Crest Factor (피크/평균 대비값)', labels={'time_sec': '시간 (s)'})
        fig_crest.add_hline(y=crest_threshold, line_dash="dash", line_color="red", annotation_text=f"크레스트 한계선: {crest_threshold:.1f}")
        st.plotly_chart(fig_crest, use_container_width=True)

# --- TAB 3: 판정 분포 및 내역 테이블 ---
with tab3:
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        st.subheader("지표 점유율 분포")
        diag_counts = trend_df['diagnosis'].value_counts().reset_index()
        diag_counts.columns = ['진단 상태', '구간 수']
        fig_pie = px.pie(diag_counts, values='구간 수', names='진단 상태', 
                         color='진단 상태', 
                         color_discrete_map={"정상 (Normal)": "#10b981", "주의 (Warning)": "#f59e0b", "위험 (Danger)": "#ef4444"})
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_d2:
        st.subheader("이동 진단 원시 데이터 그리드")
        st.dataframe(trend_df[["time_sec", "rms", "kurtosis", "crest_factor", "diagnosis", "reason"]], use_container_width=True)

# -----------------------------------------------------------------------------
# 5. TAB 4: 종합 진단 보고서 생성 및 내보내기 (CBM Report) - 신규 개발 파트
# -----------------------------------------------------------------------------
with tab4:
    st.subheader("📋 설비 정밀 상태 평가 진단서 (CBM Report)")
    st.write("부장님 보고 및 예산 승인에 활용할 수 있는 정식 보고서 양식입니다. 내용을 수정하여 다운로드할 수 있습니다.")
    
    # 보고서 메타데이터 입력창
    st.markdown("#### 1. 정비 요약 메타정보")
    rep_col1, rep_col2, rep_col3 = st.columns(3)
    with rep_col1:
        eval_date = st.date_input("진단 및 점검 평가일", datetime.date.today())
    with rep_col2:
        inspector_name = st.text_input("점검 엔지니어", value="예산운영팀 홍길동")
    with rep_col3:
        equipment_id = st.text_input("설비/모터 식별 번호", value="MTR-CWRU-12K-01")

    # 예산 관리 연계를 위한 의견 작성 및 자동 점검비 권고
    st.markdown("#### 2. 진단 소견 및 권장 조치사항")
    
    # 상태에 따른 정비 처방전 자동 생성
    if final_status == "위험 (Danger)":
        default_comment = "해당 모터에서 높은 빈도의 고주파 격파 및 진동 에너지 증폭이 확인되었습니다. 즉시 정비 조치(오버홀 및 베어링 전면 교체)를 취해야 하며, 설비 예비비(개량공사비 또는 수선유지비) 투입을 권고합니다."
        suggested_action = "수리/부품 긴급 교체(개량공사 예산 배정)"
        recommended_budget = "수선유지비 및 개량공사비 2,500,000원 긴급 책정 필요"
    elif final_status == "주의 (Warning)":
        default_comment = "일부 이상 피크 증가 추세가 관측됩니다. 설비 성능 저하가 의심되므로 윤활유 공급 및 간이 정밀 점검을 진행해야 합니다. 차기 월별 예산 내 비품/소모품 비로 윤활 그리스 정비 예산을 배정하십시오."
        suggested_action = "윤활 주입 및 정밀 관측 주기 단축 (정기 수선 유지)"
        recommended_budget = "수선유지비 350,000원 배정 권고"
    else:
        default_comment = "전체적인 진동 통계 지표가 임계값 아래에서 안정적인 분포를 나타내고 있습니다. 추가 조치는 필요 없으며, 정기 예찰 주기를 현행대로 유지합니다."
        suggested_action = "상태 모니터링 유지 및 정기 진동 측정 유지"
        recommended_budget = "추가 정비 비용 없음 (0원)"

    custom_opinion = st.text_area("종합 정비 엔지니어 소견", value=default_comment, height=120)
    
    rep_col4, rep_col5 = st.columns(2)
    with rep_col4:
        action_plan = st.text_input("필요 정비 조치", value=suggested_action)
    with rep_col5:
        budget_plan = st.text_input("권장 소요 정비비용", value=recommended_budget)

    # 마크다운 형태의 보고서 전문 빌드
    report_content = f"""# 📊 설비 정밀 상태 진단 및 CBM 종합 보고서

- **발행 일자**: {eval_date}
- **설비 식별 번호**: {equipment_id}
- **점검 담당자**: {inspector_name}
- **대상 소스 데이터**: {file_name_label}

---

## 1. 설비 건전성 진단 요약
- **종합 건전성 상태**: {final_status}
- **샘플링 속도**: {fs:,} Hz
- **총 분석 구간**: {len(trend_df)} 구간
- **위험 한도 초과율**: {danger_ratio:.1f}% (정상 범위: < 5%)

---

## 2. 주요 진동 특징 지표
- **실효 진동 폭 (RMS)**: {overall_features['rms']:.4f} G (허용 임계치: {rms_threshold:.2f} G)
- **충격 유발 첨도 (Kurtosis)**: {overall_features['kurtosis']:.2f} (허용 임계치: {kurtosis_threshold:.1f})
- **안정 분포 비 (Crest Factor)**: {overall_features['crest_factor']:.2f} (허용 임계치: {crest_threshold:.1f})

---

## 3. 현장 진단 및 정비 종합 소견
- **엔지니어 판단 의견**:
  "{custom_opinion}"

- **조치 요구 수준**: {action_plan}
- **정비 소요 예산안**: {budget_plan}

--------------------------------------------------
이 보고서는 CWRU 베어링 정밀 상태 대시보드 자동 진단 연동에 의해 실시간 출력되었습니다.
"""

    st.markdown("---")
    st.markdown("#### 3. 보고서 미리보기 (Preview)")
    st.markdown(report_content)

    # 텍스트 형태 다운로드 기능 탑재
    st.download_button(
        label="📥 진단 보고서 텍스트(.txt) 내보내기",
        data=report_content,
        file_name=f"CBM_Bearing_Report_{equipment_id}_{eval_date}.txt",
        mime="text/plain"
    )
