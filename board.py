import os
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scipy import stats
from scipy.fft import rfft, rfftfreq

try:
    from scipy.io import loadmat
except Exception:
    loadmat = None

plt.rcParams["axes.unicode_minus"] = False
np.random.seed(42)

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import os

# Install a Korean font for matplotlib
!apt-get update -qq
!apt-get install fonts-nanum -qq > /dev/null

fontpath = '/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf'

# Add the font to matplotlib's font manager
fm.fontManager.addfont(fontpath)

font_name = fm.FontProperties(fname=fontpath, size=10).get_name()

plt.rc('font', family=font_name)
plt.rcParams['axes.unicode_minus'] = False

print(f"Font '{font_name}' installed and configured for matplotlib.")

DATASET_NAME = "CWRU Bearing Dataset"
DATASET_URL = "https://engineering.case.edu/bearingdatacenter/download-data-file"
NORMAL_FILE = "/content/Time_Normal_1_098.mat"
FAULT_FILE = "/content/B007_1_123.mat"
FS = 12000  # CWRU 12k Hz data

print("데이터셋:", DATASET_NAME)
print("출처:", DATASET_URL)
print("샘플링 주파수:", FS, "Hz")

# 방법 A: Colab 파일 업로드
# 실행하면 파일 선택 창이 뜹니다.

RUN_UPLOAD = False

if RUN_UPLOAD:
    from google.colab import files
    uploaded = files.upload()
    print("업로드 파일:", list(uploaded.keys()))
else:
    print("파일 업로드를 사용하려면 RUN_UPLOAD = True로 바꾸세요.")

# 방법 B: CSV 파일 불러오기
# TODO: CSV URL 또는 업로드한 파일 경로로 바꾸세요.

RUN_CSV_LOAD = False
CSV_PATH_OR_URL = "TODO.csv"

if RUN_CSV_LOAD:
    df = pd.read_csv(CSV_PATH_OR_URL)
    display(df.head())
    print(df.info())
else:
    print("CSV 로딩을 사용하려면 RUN_CSV_LOAD = True로 바꾸세요.")

# 방법 C: MAT 파일 구조 확인
# CWRU 계열 데이터는 .mat 형식인 경우가 많습니다.

RUN_MAT_INSPECT = False
MAT_PATH = "TODO.mat"

if RUN_MAT_INSPECT:
    if loadmat is None:
        raise RuntimeError("scipy.io.loadmat을 사용할 수 없습니다.")
    mat = loadmat(MAT_PATH)
    keys = [k for k in mat.keys() if not k.startswith("__")]
    print("MAT 변수 목록:")
    for k in keys:
        arr = np.asarray(mat[k])
        print(k, arr.shape, arr.dtype)
else:
    print("MAT 구조 확인을 사용하려면 RUN_MAT_INSPECT = True로 바꾸세요.")

# Load normal signal
normal_mat = loadmat(NORMAL_FILE)
# Find the relevant signal variable, typically 'X###_DE_time' or similar
normal_key = [k for k in normal_mat.keys() if ('DE_time' in k or 'FE_time' in k or 'time' in k) and not k.startswith("__")]
if not normal_key:
    raise ValueError(f"Could not find a suitable time series signal in {NORMAL_FILE}. Please inspect the .mat file manually (e.g., by running the MAT_INSPECT cell).")
normal_signal = normal_mat[normal_key[0]].ravel()

# Load fault signal
fault_mat = loadmat(FAULT_FILE)
# Find the relevant signal variable
fault_key = [k for k in fault_mat.keys() if ('DE_time' in k or 'FE_time' in k or 'time' in k) and not k.startswith("__")]
if not fault_key:
    raise ValueError(f"Could not find a suitable time series signal in {FAULT_FILE}. Please inspect the .mat file manually (e.g., by running the MAT_INSPECT cell).")
fault_signal = fault_mat[fault_key[0]].ravel()

print("normal_signal:", normal_signal.shape)
print("fault_signal:", fault_signal.shape)

def plot_time_waveform(signal, fs, title, seconds=0.2):
    n = min(len(signal), int(fs * seconds))
    x = np.arange(n) / fs
    plt.figure(figsize=(12, 3))
    plt.plot(x, signal[:n])
    plt.title(title)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.grid(alpha=0.3)
    plt.show()

plot_time_waveform(normal_signal, FS, "정상 진동 신호")
plot_time_waveform(fault_signal, FS, "이상 진동 신호")

def calculate_features(signal):
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

feature_df = pd.DataFrame([
    {"state": "normal", **calculate_features(normal_signal)},
    {"state": "fault", **calculate_features(fault_signal)},
])

display(feature_df)

plot_cols = ["rms", "peak", "kurtosis", "crest_factor"]
feature_df.set_index("state")[plot_cols].T.plot(kind="bar", figsize=(10, 4))
plt.title("정상/이상 특징값 비교")
plt.ylabel("Feature value")
plt.xticks(rotation=0)
plt.grid(axis="y", alpha=0.3)
plt.show()

def compute_fft(signal, fs):
    signal = np.asarray(signal).ravel()
    signal = signal - np.mean(signal)
    n = len(signal)
    window = np.hanning(n)
    spectrum = np.abs(rfft(signal * window)) / n
    freq = rfftfreq(n, 1 / fs)
    return freq, spectrum

def plot_fft(signal, fs, title, max_freq=1000):
    freq, spectrum = compute_fft(signal, fs)
    mask = freq <= max_freq
    plt.figure(figsize=(12, 4))
    plt.plot(freq[mask], spectrum[mask])
    plt.title(title)
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Amplitude")
    plt.grid(alpha=0.3)
    plt.show()

plot_fft(normal_signal, FS, "정상 신호 FFT")
plot_fft(fault_signal, FS, "이상 신호 FFT")

def window_features(signal, fs, window_sec=0.2, step_sec=0.1):
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

normal_win = window_features(normal_signal, FS)
fault_win = window_features(fault_signal, FS)
normal_win["state"] = "normal"
fault_win["state"] = "fault"
trend_df = pd.concat([normal_win, fault_win], ignore_index=True)

display(trend_df.head())

for col in ["rms", "kurtosis", "crest_factor"]:
    plt.figure(figsize=(12, 3))
    for state, group in trend_df.groupby("state"):
        plt.plot(group["time_sec"], group[col], label=state)
    plt.title(f"구간별 {col} 추세")
    plt.xlabel("Time (s)")
    plt.ylabel(col)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.show()

normal_baseline = normal_win[["rms", "kurtosis", "crest_factor"]].agg(["mean", "std"])

rms_threshold = normal_baseline.loc["mean", "rms"] + 3 * normal_baseline.loc["std", "rms"]
kurtosis_threshold = 5.0
crest_threshold = 4.0

def diagnose(row):
    reasons = []
    if row["rms"] > rms_threshold:
        reasons.append("RMS 증가")
    if row["kurtosis"] > kurtosis_threshold:
        reasons.append("충격성 증가")
    if row["crest_factor"] > crest_threshold:
        reasons.append("Crest Factor 증가")

    if len(reasons) >= 2:
        return "위험", ", ".join(reasons)
    if len(reasons) == 1:
        return "주의", reasons[0]
    return "정상", "-"

diagnosis = fault_win.copy()
diagnosis[["diagnosis", "reason"]] = diagnosis.apply(
    lambda row: pd.Series(diagnose(row)),
    axis=1,
)

display(diagnosis[["time_sec", "rms", "kurtosis", "crest_factor", "diagnosis", "reason"]].head(20))
print(diagnosis["diagnosis"].value_counts())

summary = f'''
# 공개 진동 데이터 분석 결과 요약

## 사용 데이터
- 데이터셋: {DATASET_NAME}
- 출처: {DATASET_URL}
- 샘플링 주파수: {FS} Hz

## 특징값 비교
- 정상 RMS: {feature_df.loc[feature_df['state']=='normal', 'rms'].iloc[0]:.4f}
- 이상 RMS: {feature_df.loc[feature_df['state']=='fault', 'rms'].iloc[0]:.4f}
- 정상 Kurtosis: {feature_df.loc[feature_df['state']=='normal', 'kurtosis'].iloc[0]:.4f}
- 이상 Kurtosis: {feature_df.loc[feature_df['state']=='fault', 'kurtosis'].iloc[0]:.4f}
- 정상 Crest Factor: {feature_df.loc[feature_df['state']=='normal', 'crest_factor'].iloc[0]:.4f}
- 이상 Crest Factor: {feature_df.loc[feature_df['state']=='fault', 'crest_factor'].iloc[0]:.4f}

## 진단 기준 예시
- RMS 주의 기준: 정상 RMS 평균 + 3σ = {rms_threshold:.4f}
- Kurtosis 주의 기준: {kurtosis_threshold}
- Crest Factor 주의 기준: {crest_threshold}

## CBM 해석
- **가장 잘 설명한 특징값**: 현재 분석된 CWRU 데이터에서는 RMS(제곱평균제곱근)가 이상 상태를 가장 명확하게 설명했습니다. 모든 '주의' 경고는 RMS 증가에 의해 유발되었으며, Kurtosis와 Crest Factor는 상승했으나 설정된 임계값을 초과하지 않았습니다. 이는 전체적인 진동 에너지 증가가 주요 이상 징후임을 나타냅니다.
- **점검 또는 정비 지시 기준**: RMS 값이 정상 기준(정상 RMS 평균 + 3 표준편차)을 지속적으로 초과하는 경우, 또는 경고 상태가 일정 시간 이상 유지되는 경우 점검을 지시할 수 있습니다. 예를 들어, '주의' 상태가 3회 연속 감지되거나, RMS가 특정 '위험' 임계값(예: 5 표준편차 초과 또는 공장 허용치)을 넘어서면 즉각적인 정비를 고려할 수 있습니다.
- **실제 현장 적용 시 필요한 추가 데이터**: 실제 현장 적용을 위해서는 다음과 같은 추가 데이터가 필요합니다. 1) 다양한 운전 조건(부하, 속도 등)에서의 정상 데이터, 2) 실제 고장 이력 데이터 및 고장 종류별 진동 데이터, 3) 유사 설비의 운전 데이터 및 유지보수 기록. 이러한 데이터는 임계값의 신뢰도를 높이고, 오경보를 줄이며, 고장 유형 분류 및 잔여 수명 예측 모델 구축에 기여할 수 있습니다.
'''

print(summary)

import seaborn as sns

# Count the occurrences of each diagnosis status
alert_counts = diagnosis['diagnosis'].value_counts()

# Create a bar plot
plt.figure(figsize=(8, 5))
sns.barplot(x=alert_counts.index, y=alert_counts.values, palette='viridis', hue=alert_counts.index, legend=False)
plt.title('진단 상태 분포')
plt.xlabel('진단 상태')
plt.ylabel('데이터 포인트 수')
plt.grid(axis='y', alpha=0.3)
plt.show()
kurtosis_alerts = diagnosis[diagnosis['kurtosis'] > kurtosis_threshold]
display(kurtosis_alerts[['time_sec', 'kurtosis', 'diagnosis', 'reason']])
if kurtosis_alerts.empty:
    print('No data points found where Kurtosis exceeds the alert threshold.')

# RMS 추세와 임계값 시각화
plt.figure(figsize=(12, 4))
plt.plot(fault_win['time_sec'], fault_win['rms'], label='Fault RMS')
plt.axhline(y=rms_threshold, color='r', linestyle='--', label=f'RMS 임계값: {rms_threshold:.4f}')
plt.title('RMS 추세 및 경고 임계값')
plt.xlabel('Time (s)')
plt.ylabel('RMS')
plt.legend()
plt.grid(alpha=0.3)
plt.show()

# Kurtosis 추세와 임계값 시각화
plt.figure(figsize=(12, 4))
plt.plot(fault_win['time_sec'], fault_win['kurtosis'], label='Fault Kurtosis')
plt.axhline(y=kurtosis_threshold, color='r', linestyle='--', label=f'Kurtosis 임계값: {kurtosis_threshold:.1f}')
plt.title('Kurtosis 추세 및 경고 임계값')
plt.xlabel('Time (s)')
plt.ylabel('Kurtosis')
plt.legend()
plt.grid(alpha=0.3)
plt.show()

# Crest Factor 추세와 임계값 시각화
plt.figure(figsize=(12, 4))
plt.plot(fault_win['time_sec'], fault_win['crest_factor'], label='Fault Crest Factor')
plt.axhline(y=crest_threshold, color='r', linestyle='--', label=f'Crest Factor 임계값: {crest_threshold:.1f}')
plt.title('Crest Factor 추세 및 경고 임계값')
plt.xlabel('Time (s)')
plt.ylabel('Crest Factor')
plt.legend()
plt.grid(alpha=0.3)
plt.show()

# Get all selected .mat files from the context
selected_mat_files = [
    '/content/B007_1_123.mat',
    '/content/B021_1_227.mat',
    '/content/B014_1_190.mat',
    '/content/IR007_1_110.mat',
    '/content/IR021_1_214.mat',
    '/content/OR007_6_1_136.mat',
    '/content/OR014_6_1_202.mat',
    '/content/OR021_6_1_239.mat',
    '/content/Time_Normal_1_098.mat'
]

# Filter out the already analyzed normal and fault files
other_mat_files = [f for f in selected_mat_files if f not in [NORMAL_FILE, FAULT_FILE]]

print("Analyzing other MAT files:")
for mat_file_path in other_mat_files:
    print(f"  - {mat_file_path}")

for mat_file_path in other_mat_files:
    file_name = os.path.basename(mat_file_path)
    print(f"\n--- Processing file: {file_name} ---")

    # Load signal from the current .mat file
    current_mat = loadmat(mat_file_path)
    # Find the relevant signal variable
    current_key = [k for k in current_mat.keys() if ('DE_time' in k or 'FE_time' in k or 'time' in k) and not k.startswith("__")]
    if not current_key:
        print(f"  WARNING: Could not find a suitable time series signal in {file_name}. Skipping.")
        continue
    current_signal = current_mat[current_key[0]].ravel()

    # Calculate windowed features
    current_win = window_features(current_signal, FS)

    # Plot trends with thresholds
    for col in ["rms", "kurtosis", "crest_factor"]:
        plt.figure(figsize=(12, 3))
        plt.plot(current_win["time_sec"], current_win[col], label=f'{file_name} {col}')

        if col == "rms":
            plt.axhline(y=rms_threshold, color='r', linestyle='--', label=f'RMS 임계값: {rms_threshold:.4f}')
        elif col == "kurtosis":
            plt.axhline(y=kurtosis_threshold, color='r', linestyle='--', label=f'Kurtosis 임계값: {kurtosis_threshold:.1f}')
        elif col == "crest_factor":
            plt.axhline(y=crest_threshold, color='r', linestyle='--', label=f'Crest Factor 임계값: {crest_threshold:.1f}')

        plt.title(f'{file_name} 구간별 {col} 추세')
        plt.xlabel("Time (s)")
        plt.ylabel(col)
        plt.legend()
        plt.grid(alpha=0.3)
        plt.show()

all_other_features_list = []

for mat_file_path in other_mat_files:
    file_name = os.path.basename(mat_file_path)

    # Load signal from the current .mat file
    current_mat = loadmat(mat_file_path)
    current_key = [k for k in current_mat.keys() if ('DE_time' in k or 'FE_time' in k or 'time' in k) and not k.startswith("__")]
    if not current_key:
        print(f"  WARNING: Could not find a suitable time series signal in {file_name}. Skipping for correlation analysis.")
        continue
    current_signal = current_mat[current_key[0]].ravel()

    # Calculate windowed features
    current_win = window_features(current_signal, FS)
    current_win['file'] = file_name
    all_other_features_list.append(current_win)

if all_other_features_list:
    all_other_features_df = pd.concat(all_other_features_list, ignore_index=True)
    print("Combined features from other files:")
    display(all_other_features_df.head())

    # Select features for correlation analysis
    features_for_correlation = ['rms', 'kurtosis', 'crest_factor', 'std', 'peak']
    correlation_matrix = all_other_features_df[features_for_correlation].corr()

    plt.figure(figsize=(8, 6))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=.5)
    plt.title('다른 .mat 파일들의 특징값 간 상관관계')
    plt.show()
else:
    print("No other .mat files were processed for correlation analysis.")

print("원인별 '주의' 경고 발생 횟수:")
display(diagnosis['reason'].value_counts())
descriptive_stats = trend_df.groupby('state')[['rms', 'kurtosis', 'crest_factor']].describe()
display(descriptive_stats)

specific_files_to_analyze = [
    '/content/B007_1_123.mat',
    '/content/IR007_1_110.mat',
    '/content/OR007_6_1_136.mat'
]

for mat_file_path in specific_files_to_analyze:
    file_name = os.path.basename(mat_file_path)
    print(f"\n--- 파일 분석 시작: {file_name} ---")

    # 1. Load signal
    current_mat = loadmat(mat_file_path)
    current_key = [k for k in current_mat.keys() if ('DE_time' in k or 'FE_time' in k or 'time' in k) and not k.startswith("__")]
    if not current_key:
        print(f"  WARNING: {file_name}에서 적절한 시계열 신호를 찾을 수 없습니다. 건너뜁니다.")
        continue
    current_signal = current_mat[current_key[0]].ravel()

    # 2. Calculate and display overall features
    overall_features = calculate_features(current_signal)
    print(f"\n{file_name} 전체 특징값:")
    display(pd.DataFrame([overall_features], index=[file_name]))

    # 3. Calculate windowed features
    current_win = window_features(current_signal, FS)
    current_win['file'] = file_name

    # 4. Plot feature trends with thresholds
    for col in ["rms", "kurtosis", "crest_factor"]:
        plt.figure(figsize=(12, 3))
        plt.plot(current_win["time_sec"], current_win[col], label=f'{file_name} {col}')

        if col == "rms":
            plt.axhline(y=rms_threshold, color='r', linestyle='--', label=f'RMS 임계값: {rms_threshold:.4f}')
            exceeded_count = (current_win[col] > rms_threshold).sum()
            print(f"  - {col}: {exceeded_count}/{len(current_win)} 구간이 RMS 임계값 초과")
        elif col == "kurtosis":
            plt.axhline(y=kurtosis_threshold, color='r', linestyle='--', label=f'Kurtosis 임계값: {kurtosis_threshold:.1f}')
            exceeded_count = (current_win[col] > kurtosis_threshold).sum()
            print(f"  - {col}: {exceeded_count}/{len(current_win)} 구간이 Kurtosis 임계값 초과")
        elif col == "crest_factor":
            plt.axhline(y=crest_threshold, color='r', linestyle='--', label=f'Crest Factor 임계값: {crest_threshold:.1f}')
            exceeded_count = (current_win[col] > crest_threshold).sum()
            print(f"  - {col}: {exceeded_count}/{len(current_win)} 구간이 Crest Factor 임계값 초과")

        plt.title(f'{file_name} 구간별 {col} 추세')
        plt.xlabel("Time (s)")
        plt.ylabel(col)
        plt.legend()
        plt.grid(alpha=0.3)
        plt.show()

specific_files_to_compare = [
    '/content/B007_1_123.mat',
    '/content/IR007_1_110.mat',
    '/content/OR007_6_1_136.mat'
]

comparison_features = []

for mat_file_path in specific_files_to_compare:
    file_name = os.path.basename(mat_file_path)

    # Load signal
    current_mat = loadmat(mat_file_path)
    current_key = [k for k in current_mat.keys() if ('DE_time' in k or 'FE_time' in k or 'time' in k) and not k.startswith("__")]
    if not current_key:
        print(f"  WARNING: {file_name}에서 적절한 시계열 신호를 찾을 수 없습니다. 건너뜁니다.")
        continue
    current_signal = current_mat[current_key[0]].ravel()

    # Calculate overall features
    overall_features = calculate_features(current_signal)
    comparison_features.append({
        'file': file_name,
        'rms': overall_features['rms'],
        'kurtosis': overall_features['kurtosis'],
        'crest_factor': overall_features['crest_factor'],
        'peak': overall_features['peak'],
        'std': overall_features['std']
    })

# Create DataFrame for comparison
comparison_df = pd.DataFrame(comparison_features)
comparison_df = comparison_df.set_index('file')

print("세 파일의 주요 특징값 비교:")
display(comparison_df)

# Visualize comparison with a bar chart
comparison_df.plot(kind='bar', figsize=(12, 6))
plt.title('B007, IR007, OR007 파일 특징값 비교')
plt.ylabel('Feature Value')
plt.xticks(rotation=45)
plt.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.show()

# Summarize findings based on comparison and thresholds
print("\n--- 분석 요약 ---")
print(f"RMS 임계값: {rms_threshold:.4f}")
print(f"Kurtosis 임계값: {kurtosis_threshold:.1f}")
print(f"Crest Factor 임계값: {crest_threshold:.1f}")

for index, row in comparison_df.iterrows():
    print(f"\n파일: {index}")
    if row['rms'] > rms_threshold:
        print(f"  - RMS ({row['rms']:.4f})는 임계값 ({rms_threshold:.4f})을 초과하여 높은 진동 에너지를 나타냅니다.")
    else:
        print(f"  - RMS ({row['rms']:.4f})는 임계값 ({rms_threshold:.4f})보다 낮습니다.")

    if row['kurtosis'] > kurtosis_threshold:
        print(f"  - Kurtosis ({row['kurtosis']:.4f})는 임계값 ({kurtosis_threshold:.1f})을 초과하여 강한 충격성을 나타냅니다.")
    else:
        print(f"  - Kurtosis ({row['kurtosis']:.4f})는 임계값 ({kurtosis_threshold:.1f})보다 낮습니다.")

    if row['crest_factor'] > crest_threshold:
        print(f"  - Crest Factor ({row['crest_factor']:.4f})는 임계값 ({crest_threshold:.1f})을 초과하여 높은 피크-RMS 비율을 나타냅니다.")
    else:
        print(f"  - Crest Factor ({row['crest_factor']:.4f})는 임계값 ({crest_threshold:.1f})보다 낮습니다.")

from google.colab import drive
drive.mount('/content/drive')
