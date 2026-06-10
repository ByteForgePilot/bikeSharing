"""
共享单车健康快速检测系统 — 核心算法实现 (v3.0)

根据设计文档 v3 的三级检测架构：
  F1 — 轮胎偏摆检测：IMU Z轴 → FFT → 轮频 f 与 2f 幅值 → P=A1+0.5*A2
  F2 — 链条异响检测：8kHz 音频 → 2~4kHz带通 → 包络谱 → 四特征融合 → 分段评分
  F3 — 车头不正检测：IMU偏航角 vs GPS航向角偏差 Δθ → 线性插值评分

综合评分（木桶效应）：
  H = 1 / (0.4/F1 + 0.3/F2 + 0.3/F3)    — 加权调和平均
  penalty = min(F1, F2, F3) / 100        — 最小值惩罚
  S = H × penalty                        — 最终评分 (0~100)

输入：传感器数据.txt / 音频.pcm / 音频_时间戳.csv
输出：综合健康评分 S ∈ [0,100]，以及对应的骑行建议。
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass

import numpy as np
from scipy import signal
from scipy.fft import dct, fft, fftfreq

# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

WHEEL_RADIUS = 0.35  # 共享单车轮胎半径 (m)


@dataclass
class AccelSample:
    timestamp_ns: int
    ax: float
    ay: float
    az: float


@dataclass
class GyroSample:
    timestamp_ns: int
    gx: float
    gy: float
    gz: float


@dataclass
class AudioChunk:
    timestamp_ns: int
    cumulative_samples: int


# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

import os as _os

_BASE_DIR = _os.path.dirname(_os.path.abspath(__file__))

SENSOR_FILE = _os.path.join(_BASE_DIR, "传感器数据.txt")
PCM_FILE = _os.path.join(_BASE_DIR, "音频.pcm")
AUDIO_TS_FILE = _os.path.join(_BASE_DIR, "音频_时间戳.csv")


def load_sensor_data(path: str) -> tuple[list[AccelSample], list[GyroSample]]:
    accel: list[AccelSample] = []
    gyro: list[GyroSample] = []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 12:
            continue
        ts = int(parts[0])
        stype = parts[1].strip()
        if stype == "加速度计":
            accel.append(AccelSample(ts, float(parts[2]), float(parts[3]), float(parts[4])))
        elif stype == "陀螺仪":
            gyro.append(GyroSample(ts, float(parts[9]), float(parts[10]), float(parts[11])))
    return accel, gyro


def load_audio(path: str) -> np.ndarray:
    with open(path, "rb") as f:
        raw = f.read()
    n = len(raw) // 2
    return np.array(struct.unpack(f"<{n}h", raw), dtype=np.float32) / 32768.0


def load_audio_timestamps(path: str) -> list[AudioChunk]:
    chunks: list[AudioChunk] = []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 2:
            continue
        chunks.append(AudioChunk(int(parts[0]), int(parts[1])))
    return chunks


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def safe_div(a: float, b: float, fallback: float = 0.0) -> float:
    return a / b if b != 0 else fallback


def resample_irregular(
    times: np.ndarray, values: np.ndarray, target_fs: float
) -> tuple[np.ndarray, np.ndarray]:
    dt = 1.0 / target_fs
    t_new = np.arange(times[0], times[-1], dt)
    return t_new, np.interp(t_new, times, values)


def sliding_variance(data: np.ndarray, window: int, step: int) -> np.ndarray:
    """滑动窗口方差 (向量化)"""
    from numpy.lib.stride_tricks import sliding_window_view
    return sliding_window_view(data, window)[::step].var(axis=1)


def bandpass_filter(
    data: np.ndarray, fs: float, lowcut: float, highcut: float, order: int = 4
) -> np.ndarray:
    """Butterworth 带通滤波 (安全截断版)"""
    nyq = 0.5 * fs
    lo = max(lowcut / nyq, 0.001)
    hi = min(highcut / nyq, 0.999)
    if lo >= hi:
        return data
    b, a = signal.butter(order, [lo, hi], btype="band")
    return signal.filtfilt(b, a, data)


def estimate_wheel_frequency(
    accel_z: np.ndarray, fs: float, speed_ms: float | None = None
) -> float:
    """
    估算车轮旋转频率 f (Hz).

    f = v/(2πr), r≈0.35m. 共享单车 6~30 km/h → 1.5~8 Hz.

    当提供 GPS 车速时，以其计算期望频率为中心 ±2Hz 搜索，比全范围扫描更鲁棒。
    """
    n = len(accel_z)
    mag = np.abs(fft(accel_z))[: n // 2]
    freqs = fftfreq(n, 1.0 / fs)[: n // 2]

    if speed_ms is not None and speed_ms > 0.5:
        # GPS 先验：缩小搜索范围到期望频率 ±2Hz
        f_expected = speed_ms / (2.0 * np.pi * WHEEL_RADIUS)
        lo = max(f_expected - 2.0, 1.0)
        hi = min(f_expected + 2.0, 10.0)
    else:
        lo, hi = 1.5, 8.0

    mask = (freqs >= lo) & (freqs <= hi)
    if mask.any():
        return float(freqs[mask][np.argmax(mag[mask])])
    return 3.0


# ===================================================================
# 大数据文件自适应窗口选取
#
# 策略：
#   1. 传感器时长 ≤ 30s 且音频 ≤ 30s → 全量分析
#   2. 超过阈值 → 从传感器数据中选取骑行质量最高的 15s 窗口
#   3. 窗口评分 = 路面平整度 + 直行稳定性（方差越低越好）
#   4. 按时间戳对应裁剪音频数据
# ===================================================================

# 阈值常量
MAX_DURATION_S = 30.0      # 超过此值触发窗口选取
WINDOW_DURATION_S = 15.0   # 选取窗口长度

# 运行时配置（可通过环境变量覆盖）
MAX_DURATION_S = float(_os.environ.get("BIKE_MAX_DURATION_S", "30"))
WINDOW_DURATION_S = float(_os.environ.get("BIKE_WINDOW_DURATION_S", "15"))


def select_analysis_window(
    accel: list[AccelSample],
    gyro: list[GyroSample],
    audio: np.ndarray,
    audio_ts: list[AudioChunk],
) -> dict:
    """
    当输入数据时长超过阈值时，自动选取骑行质量最高的时间段。

    返回值：
      {
        "used_window": True/False,
        "window_start_ns": ...,
        "window_end_ns": ...,
        "accel_slice": [...],
        "gyro_slice": [...],
        "audio_slice": np.ndarray,
        "audio_ts_slice": [...],
      }

    调用方使用返回的 sliced 数据替代原始数据进行后续检测。
    """
    result = {
        "used_window": False,
        "accel_slice": accel,
        "gyro_slice": gyro,
        "audio_slice": audio,
        "audio_ts_slice": audio_ts,
    }

    if len(accel) < 64:
        return result

    # ---- 计算传感器时间范围 ----
    all_timestamps = sorted(
        [a.timestamp_ns for a in accel] + [g.timestamp_ns for g in gyro]
    )
    t_min_ns = all_timestamps[0]
    t_max_ns = all_timestamps[-1]
    duration_s = (t_max_ns - t_min_ns) * 1e-9

    # 计算音频时长
    if len(audio_ts) >= 2:
        audio_duration_s = (
            abs(audio_ts[-1].timestamp_ns - audio_ts[0].timestamp_ns) * 1e-9
        )
    else:
        audio_duration_s = 0.0

    # 判断是否需要窗口选取
    need_window = duration_s > MAX_DURATION_S or audio_duration_s > MAX_DURATION_S
    if not need_window:
        return result

    # ---- 滑动窗口扫描传感器数据 ----
    window_ns = int(WINDOW_DURATION_S * 1e9)
    step_ns = window_ns // 4

    # 将传感器数据重采样到统一网格，向量化评估所有候选窗口
    t0 = accel[0].timestamp_ns if accel else t_min_ns
    times_a = np.array([(a.timestamp_ns - t0) * 1e-9 for a in accel], dtype=np.float64)
    az = np.array([a.az for a in accel], dtype=np.float64)
    az -= np.mean(az)

    # 统一重采样到 50Hz（评分不需要高精度）
    score_fs = 50.0
    t_uniform, az_uniform = resample_irregular(times_a, az, score_fs)

    window_samples = int(WINDOW_DURATION_S * score_fs)
    step_samples = max(window_samples // 4, 1)

    from numpy.lib.stride_tricks import sliding_window_view

    if len(az_uniform) < window_samples:
        return result

    windows = sliding_window_view(az_uniform, window_samples)[::step_samples]
    az_vars = windows.var(axis=1)  # 向量化：所有窗口的方差一次性计算

    if gyro:
        gz_t = np.array([(g.timestamp_ns - t0) * 1e-9 for g in gyro], dtype=np.float64)
        gz = np.array([g.gz for g in gyro], dtype=np.float64)
        _, gz_uniform = resample_irregular(gz_t, gz, score_fs)
        if len(gz_uniform) >= window_samples:
            gz_windows = sliding_window_view(gz_uniform, window_samples)[::step_samples]
            gz_vars = gz_windows.var(axis=1)
        else:
            gz_vars = np.zeros_like(az_vars)
    else:
        gz_vars = np.zeros_like(az_vars)

    # 综合评分：路面越平(az方差低) + 骑得越直(gz方差低) → 分越低 → 越好
    scores_vec = az_vars * 1.0 + gz_vars * 10.0

    # 找到最佳窗口对应的起始时间
    best_idx = int(np.argmin(scores_vec))
    best_start_ns = t_min_ns + int(best_idx * step_samples / score_fs * 1e9)
    best_end_ns = best_start_ns + window_ns

    # ---- 裁剪传感器数据 ----
    accel_slice = [
        a for a in accel if best_start_ns <= a.timestamp_ns < best_end_ns
    ]
    gyro_slice = [
        g for g in gyro if best_start_ns <= g.timestamp_ns < best_end_ns
    ]

    # ---- 裁剪音频数据 ----
    # 音频时间戳映射到采样索引
    if len(audio_ts) >= 2 and len(audio) > 0:
        # 找到最接近窗口起止时间的音频块
        start_idx = 0
        end_idx = len(audio_ts) - 1
        for i, chunk in enumerate(audio_ts):
            if chunk.timestamp_ns < best_start_ns:
                start_idx = i
            if chunk.timestamp_ns <= best_end_ns:
                end_idx = i

        sample_start = audio_ts[max(start_idx - 1, 0)].cumulative_samples
        sample_end = audio_ts[min(end_idx + 1, len(audio_ts) - 1)].cumulative_samples
        sample_start = max(sample_start, 0)
        sample_end = min(sample_end, len(audio))

        audio_slice = audio[sample_start:sample_end].copy()

        # 调整音频时间戳（重新对齐到窗口起点）
        audio_ts_slice = [
            AudioChunk(timestamp_ns=c.timestamp_ns, cumulative_samples=c.cumulative_samples - sample_start)
            for c in audio_ts
            if sample_start <= c.cumulative_samples <= sample_end
        ]
    else:
        audio_slice = audio
        audio_ts_slice = audio_ts

    return {
        "used_window": True,
        "window_start_ns": best_start_ns,
        "window_end_ns": best_end_ns,
        "duration_original_s": round(duration_s, 1),
        "duration_window_s": round(window_ns * 1e-9, 1),
        "accel_slice": accel_slice,
        "gyro_slice": gyro_slice,
        "audio_slice": audio_slice,
        "audio_ts_slice": audio_ts_slice,
    }


# ===================================================================
# F1 — 轮胎偏摆检测
#
# 设计文档算法：
#   1. IMU Z 轴加速度 → 平整路面判定 (方差 < 0.5)
#   2. 读取 GPS 车速 → f = v / (2πr)
#   3. FFT → 提取 f 与 2f 频率幅值 A1, A2
#   4. 偏摆特征值 P = A1 + 0.5×A2
#   5. P ≤ P_healthy → F1=100 | P ≥ P_severe → F1=0 | 线性插值
#
# 适配说明：无 GPS 数据时，使用陀螺仪/加速度计估算车轮转频 f。
# ===================================================================


def detect_tire_wobble(
    accel: list[AccelSample],
    gyro: list[GyroSample] | None = None,
    speed_ms: float | None = None,
) -> dict:
    if len(accel) < 64:
        return {"score": 100.0, "wheel_freq_hz": 0.0, "amplitude_f": 0.0,
                "amplitude_2f": 0.0, "P_value": 0.0, "flat_fraction": 0.0}

    t0 = accel[0].timestamp_ns
    times = np.array([(a.timestamp_ns - t0) * 1e-9 for a in accel], dtype=np.float64)
    az = np.array([a.az for a in accel], dtype=np.float64)
    az -= np.mean(az)  # 去重力直流

    # ---- 1. 重采样 + 带通滤波 ----
    target_fs = 100.0
    _, az_uniform = resample_irregular(times, az, target_fs)
    az_filtered = bandpass_filter(az_uniform, target_fs, 2.0, 40.0, order=4)

    # ---- 2. 平整路面判定（滑动窗口方差） ----
    window = int(target_fs * 1.0)  # 1 秒窗口
    step = window // 2
    win_vars = sliding_variance(az_filtered, window, step)
    flat_mask = win_vars < 3.0  # 阈值调高以适配真实骑行数据振动强度
    flat_fraction = float(np.mean(flat_mask)) if len(flat_mask) > 0 else 0.0

    # 优先使用平整路面片段；若不足则使用全部数据
    if flat_fraction >= 0.2:
        # 提取所有平整窗口拼接
        flat_segments = []
        for i, is_flat in enumerate(flat_mask):
            if is_flat:
                start = i * step
                flat_segments.append(az_filtered[start : start + window])
        if flat_segments:
            analysis_data = np.concatenate(flat_segments)
        else:
            analysis_data = az_filtered
    else:
        analysis_data = az_filtered

    # ---- 3. 估计车轮转频 + FFT ----
    f_wheel = estimate_wheel_frequency(analysis_data, target_fs, speed_ms)
    f_2 = 2.0 * f_wheel

    n = len(analysis_data)
    mag = np.abs(fft(analysis_data))[: n // 2] / (n / 2)  # 归一化幅值
    freqs = fftfreq(n, 1.0 / target_fs)[: n // 2]

    def amplitude_at(target_hz: float) -> float:
        """取目标频率 ±0.3Hz 范围内的最大幅值"""
        margin = 0.3
        mask = (freqs >= target_hz - margin) & (freqs <= target_hz + margin)
        if mask.any():
            return float(np.max(mag[mask]))
        idx = np.argmin(np.abs(freqs - target_hz))
        return float(mag[idx])

    A1 = amplitude_at(f_wheel)
    A2 = amplitude_at(f_2)

    # ---- 4. 偏摆特征值 P = A1 + 0.5×A2 ----
    P = A1 + 0.5 * A2

    # ---- 5. 线性插值评分 ----
    # 阈值基于归一化 FFT 幅值的经验标定
    # P 阈值: 正常轮胎底盘振动线 P ≤ 0.35, 严重偏摆 P ≥ 1.50
    #   注意: 真实骑行数据在颠簸路面 A1/A2 可达 0.3~0.8，阈值已放宽
    #   P ≤ 0.35 → 100（正常轮胎，包含骑行小幅振动）
    #   P > 0.35 → 线性衰减到 P=1.50 时得 0
    P_normal = 0.35
    P_severe = 1.50

    if P <= P_normal:
        score = 100.0
    elif P >= P_severe:
        score = 0.0
    else:
        score = 100.0 * (1.0 - (P - P_normal) / (P_severe - P_normal))

    # 平整路面惩罚: 仅在极差路况（平整占比 < 20%）时降信度
    if flat_fraction < 0.2:
        score = min(score, 85.0)

    return {
        "score": round(float(score), 2),
        "wheel_freq_hz": round(f_wheel, 2),
        "amplitude_f": round(A1, 4),
        "amplitude_2f": round(A2, 4),
        "P_value": round(P, 4),
        "flat_fraction": round(flat_fraction, 3),
    }


# ===================================================================
# F2 — 链条异响检测 (v3.0 包络谱分析方案)
#
# 核心原理（零训练数据）：
#   链条异响 = 与踏频同步的周期性金属冲击。
#   环境噪音（风噪/车流/人声）无此周期性特征。
#
# 方法：
#   1. 8kHz 重采样
#   2. 带通滤波 2~4kHz（链条冲击共振频带）
#   3. 希尔伯特变换 → 包络信号
#   4. 低通滤波包络 (0.5~10Hz，仅保留踏频范围)
#   5. FFT → 包络谱 → 踏频 SNR + 谐波检测
#   6. 冲击相位一致性分析
#   7. 多特征融合 → 异常得分 → 评分
# ===================================================================




def _lowpass_filter(data: np.ndarray, fs: float, cutoff: float, order: int = 4) -> np.ndarray:
    """Butterworth 低通滤波"""
    nyq = 0.5 * fs
    wn = min(cutoff / nyq, 0.999)
    b, a = signal.butter(order, wn, btype="low")
    return signal.filtfilt(b, a, data)


def _hilbert_envelope(data: np.ndarray) -> np.ndarray:
    """希尔伯特包络"""
    analytic = signal.hilbert(data)
    return np.abs(analytic)


def _envelope_spectrum_snr(
    envelope: np.ndarray, fs: float, target_freq: float, margin: float = 0.3
) -> float:
    """
    计算包络谱中目标频率处的 SNR (dB)。

    返回包络谱中 target_freq 处的峰值与附近基底之比。
    """
    n = len(envelope)
    mag = np.abs(fft(envelope))[: n // 2]
    freqs = fftfreq(n, 1.0 / fs)[: n // 2]

    # 峰值：目标频率 ± margin
    mask_peak = (freqs >= target_freq - margin) & (freqs <= target_freq + margin)
    if not mask_peak.any():
        return 0.0
    peak_val = float(np.max(mag[mask_peak]))

    # 噪声基底：排除目标频率附近的频率区间
    mask_noise = (freqs >= 0.3) & (freqs <= 15.0) & ~mask_peak
    # 同时排除谐波位置
    for h in [2, 3]:
        mask_noise &= ~((freqs >= target_freq * h - margin) & (freqs <= target_freq * h + margin))

    if not mask_noise.any():
        return 0.0
    noise_floor = float(np.median(mag[mask_noise]))
    if noise_floor < 1e-12:
        return 0.0
    snr = 20.0 * np.log10(peak_val / noise_floor)
    return float(max(snr, 0.0))


def _check_harmonics(
    envelope: np.ndarray, fs: float, fundamental: float, n_harmonics: int = 3, margin: float = 0.3
) -> float:
    """
    检测包络谱中是否存在基频的 n 次谐波。
    返回：检测到的谐波比例 (0~1)。
    """
    n = len(envelope)
    mag = np.abs(fft(envelope))[: n // 2]
    freqs = fftfreq(n, 1.0 / fs)[: n // 2]

    # 噪声基底（>15Hz 视为无周期结构）
    noise_mask = freqs >= 15.0
    noise_floor = float(np.median(mag[noise_mask])) if noise_mask.any() else 1e-10
    if noise_floor < 1e-12:
        return 0.0

    detected = 0
    for h in range(2, n_harmonics + 1):
        hf = fundamental * h
        mask = (freqs >= hf - margin) & (freqs <= hf + margin)
        if mask.any():
            h_peak = float(np.max(mag[mask]))
            if h_peak > noise_floor * 2.0:  # > 6dB above floor
                detected += 1
    return detected / n_harmonics


def _phase_consistency(envelope: np.ndarray, fs: float, pedal_freq: float) -> float:
    """
    冲击相位一致性分析。

    原理：链条异响在曲柄固定相位产生冲击 → 包络峰值间隔锁定在踏频周期。
         环境噪音冲击间隔随机 → 相位分散。
    """
    if len(envelope) < 16 or pedal_freq <= 0.0:
        return 0.0

    from scipy.signal import find_peaks

    # 防御：distance 至少为 fs 的 1/100，至多为包络长度的一半
    dist = int(fs / max(pedal_freq, 0.5) * 0.3)
    dist = max(min(dist, len(envelope) // 2), 2)
    height = max(np.std(envelope) * 0.3, 1e-12)

    peaks, _ = find_peaks(envelope, height=height, distance=dist)
    if len(peaks) < 4:
        return 0.0

    # 峰-峰间隔
    intervals = np.diff(peaks) / fs  # 秒

    # 排除异常间隔（<0.3个周期或>3个周期）
    period = 1.0 / pedal_freq
    valid = (intervals > period * 0.3) & (intervals < period * 3.0)
    if np.sum(valid) < 3:
        return 0.0
    intervals = intervals[valid]

    # 将间隔映射到等效曲柄相位：相位 = (间隔 mod 周期) / 周期
    phases = (intervals % period) / period

    # 圆形方差 (circular variance)
    angles = phases * 2.0 * np.pi
    R = np.sqrt(np.mean(np.cos(angles))**2 + np.mean(np.sin(angles))**2)
    # R ∈ [0, 1]，R=1 表示所有间隔对齐到同一相位
    return float(R)


def _cepstrum_score(audio: np.ndarray, fs: float, pedal_freq: float) -> float:
    """
    Cepstrum 周期性冲击检测。

    Cepstrum = |IFFT(log|FFT(x)|)|² 对周期性冲击极为敏感——
    链条异响的规则金属撞击会在 cepstrum 中产生清晰峰值，
    而风噪/人声等非周期信号则无此特征。

    返回：0~1 的周期性得分。>0.6 倾向链条异响，<0.2 倾向环境噪音。
    """
    if len(audio) < 64 or pedal_freq <= 0.0:
        return 0.0

    n = len(audio)
    spectrum = np.abs(fft(audio))
    log_spec = np.log10(spectrum[: n // 2] + 1e-10)
    cepstrum = np.abs(np.fft.ifft(log_spec)) ** 2
    # 只取前半部分 (避免对称)
    cepstrum = cepstrum[: len(cepstrum) // 2]

    # 目标 quefrency = 1 / pedal_freq (秒)
    target_q = 1.0 / pedal_freq
    margin_q = 0.15 * target_q  # ±15%

    t_axis = np.arange(len(cepstrum)) / fs
    mask = (t_axis >= target_q - margin_q) & (t_axis <= target_q + margin_q)
    if not mask.any():
        return 0.0

    peak_val = float(np.max(cepstrum[mask]))

    # 噪声基底：排除目标区域后的中值
    noise_mask = (t_axis >= 0.01) & (t_axis <= 5.0) & ~mask
    noise_floor = float(np.median(cepstrum[noise_mask])) if noise_mask.any() else 1e-10
    if noise_floor < 1e-12:
        return 0.0

    snr = peak_val / noise_floor
    # 将 SNR 映射到 [0, 1]：SNR≥8 → 1(异常), SNR≤2 → 0
    return float(min(max((snr - 2.0) / 6.0, 0.0), 1.0))


def detect_chain_noise(
    audio: np.ndarray,
    audio_chunks: list[AudioChunk],
    pedal_freq_hz: float | None = None,
) -> dict:
    """
    链条异响检测 (v3.0 包络谱方案)。

    参数:
      audio:         PCM 音频数据 (float32 [-1, 1])
      audio_chunks:  时间戳映射表
      pedal_freq_hz: 踏频 (Hz)，None 时自动从包络谱估算
    """
    if len(audio) == 0:
        return {"score": 100.0, "prediction": "良好",
                "pedal_snr_db": 0.0, "harmonic_ratio": 0.0, "phase_consistency": 0.0}

    # ---- 1. 采样率估计 → 重采样到 8kHz ----
    if len(audio_chunks) >= 2:
        dt_ns = abs(audio_chunks[-1].timestamp_ns - audio_chunks[0].timestamp_ns)
        ds = abs(audio_chunks[-1].cumulative_samples - audio_chunks[0].cumulative_samples)
        orig_fs = safe_div(ds, dt_ns * 1e-9, 16000.0)
    else:
        orig_fs = 16000.0
    # 防御：限制采样率在合理范围
    orig_fs = max(min(orig_fs, 96000.0), 1000.0)

    target_fs = 8000.0
    if abs(orig_fs - target_fs) > 100:
        num_samples = max(int(len(audio) * target_fs / orig_fs), 1)
        audio_8k = signal.resample(audio.astype(np.float64), num_samples).astype(np.float64)
    else:
        audio_8k = audio.astype(np.float64)
    # 防御：确保至少有 2 个样本
    if len(audio_8k) < 2:
        return {"score": 100.0, "prediction": "良好",
                "pedal_snr_db": 0.0, "harmonic_ratio": 0.0, "phase_consistency": 0.0}

    # ---- 2. 踏频估计（未提供时自相关法估算） ----
    if pedal_freq_hz is None or pedal_freq_hz <= 0.0:
        # 希尔伯特包络 → 低通 → 自相关找基频（比包络谱峰值扫描更抗噪）
        rough_env = _hilbert_envelope(audio_8k)
        rough_lp = _lowpass_filter(rough_env, target_fs, 10.0, order=2)
        ac = np.correlate(rough_lp, rough_lp, mode="full")
        ac = ac[len(ac) // 2:]  # 取正延迟部分
        ac /= max(ac[0], 1e-10)  # 归一化
        # 搜索范围：0.2~1.0s 延迟 → 对应 1~5Hz 踏频
        lo_idx = max(int(target_fs * 0.2), 1)
        hi_idx = min(int(target_fs * 1.0), len(ac) - 2)
        if hi_idx > lo_idx:
            from scipy.signal import find_peaks
            peaks, props = find_peaks(ac[lo_idx:hi_idx], prominence=0.05)
            if len(peaks) > 0:
                best = peaks[np.argmax(props["prominences"])]
                lag_s = (lo_idx + best) / target_fs
                pedal_freq_hz = 1.0 / lag_s
            else:
                pedal_freq_hz = 2.0
        else:
            pedal_freq_hz = 2.0
    # 防御：限制踏频在合理范围
    pedal_freq_hz = max(min(pedal_freq_hz, 8.0), 0.5)

    # ---- 3. 带通滤波 2~4kHz（链条冲击共振频带） ----
    filtered = bandpass_filter(audio_8k, target_fs, 2000.0, 4000.0, order=4)

    # ---- 4. 希尔伯特包络 + 低通滤波 ----
    envelope = _hilbert_envelope(filtered)
    # 低通保留 0.5~10Hz（踏频及其低次谐波范围）
    envelope_lp = _lowpass_filter(envelope, target_fs, 10.0, order=4)

    # ---- 4.5. 包络调制深度（AM 深度） ----
    # 链条异响的本质是强烈的振幅调制：金属冲击 → 2~4kHz 能量剧增，
    # 间隙 → 能量骤降。正常骑行也有踏频调制，但幅度平缓得多。
    # CV = std/mean，高于 0.3 意味明显调制，高于 0.6 意味强烈调制。
    envelope_mean = float(np.mean(envelope_lp))
    envelope_std = float(np.std(envelope_lp))
    mod_depth = envelope_std / (envelope_mean + 1e-10)

    # ---- 5. 包络谱 SNR @ 踏频 ----
    pedal_snr = _envelope_spectrum_snr(envelope_lp, target_fs, pedal_freq_hz)

    # ---- 6. 谐波检测 ----
    harmonic_ratio = _check_harmonics(envelope_lp, target_fs, pedal_freq_hz, n_harmonics=3)

    # ---- 7. 冲击相位一致性 ----
    phase_cons = _phase_consistency(envelope_lp, target_fs, pedal_freq_hz)

    # ---- 8. Cepstrum 周期性冲击特征 ----
    cepstrum_s = _cepstrum_score(filtered, target_fs, pedal_freq_hz)

    # ---- 9. 辅助特征：高频能量比 (2~4kHz vs 全频带) ----
    n_fft = min(len(audio_8k), 4096)
    seg = audio_8k[:n_fft]
    mag = np.abs(fft(seg))[: n_fft // 2]
    freqs = fftfreq(n_fft, 1.0 / target_fs)[: n_fft // 2]
    mask_hf = (freqs >= 2000) & (freqs <= 4000)
    total_e = np.sum(mag**2)
    hf_ratio = float(np.sum(mag[mask_hf] ** 2) / total_e) if total_e > 0 else 0.0

    # ---- 10. 辅助特征：峰值因子 ----
    rms = float(np.sqrt(np.mean(audio_8k**2))) + 1e-10
    crest_factor = float(np.max(np.abs(audio_8k))) / rms

    # ================================================================
    # 11. 异常得分融合
    #
    # 核心特征（包络谱 + cepstrum）—— 决定"是否为链条特有的周期性冲击"：
    #   pedal_snr:      包络谱在踏频处的 SNR。>8dB 链条, <3dB 噪音
    #   harmonic_ratio: 谐波存在比例。>0.5 链条, <0.2 噪音
    #   phase_cons:     冲击相位一致性。>0.6 链条, <0.3 噪音
    #   cepstrum_s:     Cepstrum 周期性得分。>0.6 链条, <0.2 噪音
    #
    # 辅助特征 —— 提供额外的异常敏感度：
    #   hf_ratio:      高频能量比
    #   crest_factor:  峰值因子
    # ================================================================
    # 11. 异常得分融合（四特征融合）
    #
    # 四个核心特征各自反映链条异响的不同侧面：
    #   pedal_snr:      包络谱在踏频处的 SNR（dB）。>10dB 强周期冲击
    #   harmonic_ratio: 谐波存在比例（0~1）。>0.6 机械冲击特征明显
    #   phase_cons:     冲击相位一致性（0~1）。>0.6 间隔锁定在曲柄相位
    #   cepstrum_s:     Cepstrum 周期性得分（0~1）。>0.6 冲击间隔离散度低
    #
    # 每个特征分别归一化到 [0,1]（阈值放宽以扩展中段区分度），
    # 然后加权融合为 anomaly_score。
    # ================================================================
    # 11b. 正常骑行基线偏移 (Offset Calibration)
    #
    # 核心思想：正常骑行必然产生踏频周期的包络调制。
    #   路面振动 + 踏板运动 + 链条正常运转 → 每个特征都有一个"正常底线"。
    #   只有显著超过底线的值才计入异常分——相当于一个高通滤波器。
    #
    # 各特征偏移说明：
    #   pedal_snr < 10dB → 视为正常骑行调制，不贡献异常分
    #   mod_depth < 0.8 → 包络CV未超过正常范围（纯噪声~0.5, 正常骑行~0.7）
    #   harm_ratio < 0.4 → 偶然谐波不算机械冲击
    #   phase_cons < 0.4 → 偶然相位对齐不意味周期锁定
    #   cepstrum < 0.3 → 倒谱微弱周期不算异常
    # ================================================================

    # 带偏移的特征归一化
    snr_score = min(max(pedal_snr - 10.0, 0.0) / 10.0, 1.0)       # 10~20dB = 0~1
    mod_score = min(max(mod_depth - 0.8, 0.0) / 0.4, 1.0)          # 0.8~1.2 = 0~1
    harm_score = min(max(harmonic_ratio - 0.4, 0.0) / 0.4, 1.0)    # 0.4~0.8 = 0~1
    phase_score = min(max(phase_cons - 0.4, 0.0) / 0.4, 1.0)       # 0.4~0.8 = 0~1
    cep_score = min(max(cepstrum_s - 0.3, 0.0) / 0.5, 1.0)         # 0.3~0.8 = 0~1

    # 加权融合
    anom = (0.35 * snr_score + 0.25 * mod_score +
            0.10 * harm_score + 0.10 * phase_score + 0.20 * cep_score)
    anomaly_score = min(max(anom, 0.0), 1.0)

    # ================================================================
    # 12. 连续评分 + 三级分级（分段映射）
    #
    # 分段映射替代线性一刀切，为"轻微"段留出更宽区间：
    #   异常分 < 0.20 → 100（正常路面噪音，无周期结构）
    #   0.20 ~ 0.45 → 100~70（轻微周期成分 → "良好"下限）
    #   0.45 ~ 0.70 → 70~30（中等周期性 → "轻微"区间）
    #   0.70 ~ 1.00 → 30~0（强周期冲击 → "异响"区间）
    # ================================================================

    if anomaly_score < 0.20:
        score = 100.0
    elif anomaly_score < 0.45:
        score = 100.0 - 30.0 * (anomaly_score - 0.20) / 0.25
    elif anomaly_score < 0.70:
        score = 70.0 - 40.0 * (anomaly_score - 0.45) / 0.25
    else:
        score = max(0.0, 30.0 - 30.0 * (anomaly_score - 0.70) / 0.30)

    if score >= 70:
        level = "良好"
    elif score >= 40:
        level = "轻微"
    else:
        level = "异响"

    return {
        "score": round(float(score), 2),
        "prediction": level,
        "pedal_snr_db": round(float(pedal_snr), 2),
        "harmonic_ratio": round(float(harmonic_ratio), 3),
        "phase_consistency": round(float(phase_cons), 3),
        "modulation_depth": round(float(mod_depth), 4),
        "cepstrum_score": round(float(cepstrum_s), 4),
        "anomaly_score": round(float(anomaly_score), 4),
    }


# ===================================================================
# F3 — 车头不正检测
#
# 设计文档算法：
#   1. 骑行状态判定：车速 ≥ 2 m/s 且 航向变化率 < 3°/s
#   2. 记录 5 秒 Yaw (IMU) 与 Course (GPS) 数据
#   3. 计算最小夹角差 → 平均偏差 Δθ
#   4. Δθ ≤ 5° → F3=100 | Δθ ≥ 15° → F3=0 | 线性插值
#
# 适配说明：无 GPS 航向数据时，使用陀螺仪 Z 轴积分偏航角
#           在"准直行段"（gz 均值接近零的窗口）计算漂移。
# ===================================================================


def detect_handlebar_misalignment(gyro: list[GyroSample]) -> dict:
    """
    车头不正检测 (F3) — 设计文档算法适配版

    原理：车头偏斜 → 骑行时为维持直行需持续施加补偿力矩
         → 陀螺仪 Z 轴出现非零偏置（偏航偏置）。
        通过分析"相对最直"骑行段的 gz 均值和累计偏航角来判断。

    适配说明：无 GPS Course 数据时，
        ① 取 gz 方差最小的 30% 窗口作为"准直行段"
        ② 用 gz 均值估算稳态偏航偏置（等效 Δθ）
        ③ 同时参考累计偏航角作为辅助判断
    """
    if len(gyro) < 32:
        return {"score": 100.0, "delta_theta_deg": 0.0, "yaw_bias_rad_s": 0.0,
                "straight_segments": 0}

    t0 = gyro[0].timestamp_ns
    times = np.array([(g.timestamp_ns - t0) * 1e-9 for g in gyro], dtype=np.float64)
    gz = np.array([g.gz for g in gyro], dtype=np.float64)

    target_fs = 50.0
    _, gz_uniform = resample_irregular(times, gz, target_fs)

    # ---- 1. 寻找"准直行段"（取 gz 方差最低的片段） ----
    window_s = 5.0
    window_n = int(window_s * target_fs)
    step_n = max(window_n // 4, 1)

    segments: list[tuple[float, np.ndarray]] = []  # (std, segment)
    for start in range(0, len(gz_uniform) - window_n, step_n):
        seg = gz_uniform[start : start + window_n]
        segments.append((float(np.std(seg)), seg))

    if not segments:
        return {"score": 100.0, "delta_theta_deg": 0.0, "yaw_bias_rad_s": 0.0,
                "straight_segments": 0}

    segments.sort(key=lambda x: x[0])
    top_n = max(int(len(segments) * 0.3), 1)
    best_segments = segments[:top_n]

    # 绝对质量门槛：最直段的 gz 标准差必须低于此值，否则判定"无有效直行段"
    # 0.3 rad/s ≈ 17°/s — 超过此值说明全程在转弯，车头检测不可靠
    MAX_STRAIGHT_STD = 0.3
    best_std = best_segments[0][0]
    if best_std > MAX_STRAIGHT_STD:
        return {
            "score": 100.0,
            "delta_theta_deg": 0.0,
            "yaw_bias_rad_s": 0.0,
            "straight_segments": 0,
            "warning": f"无有效直行段 (最佳段 gz_std={best_std:.3f} > {MAX_STRAIGHT_STD}), "
                       f"建议在平直路段重新检测",
        }

    # ---- 2. 计算各段的 gz 均值和累计偏航角 ----
    gz_means: list[float] = []
    yaw_deviations: list[float] = []
    dt = 1.0 / target_fs

    for _, seg in best_segments:
        gz_means.append(float(np.mean(seg)))
        yaw = np.cumsum(seg) * dt
        yaw_deviations.append(float(np.mean(yaw)))

    # ---- 3. 综合指标 ----
    yaw_bias = float(np.mean(gz_means))  # 稳态偏航偏置 (rad/s)
    avg_yaw_deviation = float(np.mean([abs(d) for d in yaw_deviations]))  # 累计偏航角 (rad)

    # 将 gz 偏置映射为等效车头偏角 Δθ（°）
    # 关系：Δθ ≈ |gz_bias| × T_observation
    # 其中 T_observation = 2s（骑行者感知漂移的时间尺度）
    T_obs = 2.0
    delta_theta_from_bias = float(np.degrees(abs(yaw_bias) * T_obs))

    # 辅助：累计偏航角也反映偏斜程度
    delta_theta_from_yaw = float(np.degrees(avg_yaw_deviation))

    # 取两者加权作为最终 Δθ
    delta_theta_deg = 0.7 * delta_theta_from_bias + 0.3 * delta_theta_from_yaw

    # ---- 4. 线性插值评分 ----
    theta_ok = 8.0
    theta_bad = 22.0

    if delta_theta_deg <= theta_ok:
        score = 100.0
    elif delta_theta_deg >= theta_bad:
        score = 0.0
    else:
        score = 100.0 * (1.0 - (delta_theta_deg - theta_ok) / (theta_bad - theta_ok))

    return {
        "score": round(float(score), 2),
        "delta_theta_deg": round(delta_theta_deg, 2),
        "yaw_bias_rad_s": round(yaw_bias, 4),
        "straight_segments": top_n,
    }


# ===================================================================
# 综合健康评分（木桶效应）
#
# 设计文档算法：
#   H = 1 / (0.4/F1 + 0.3/F2 + 0.3/F3)    — 加权调和平均
#   penalty = min(F1, F2, F3) / 100        — 最小值惩罚因子
#   S = H × penalty                        — 最终评分 (0~100)
#
# 使用调和平均 + 最小值惩罚体现"木桶效应"：
#   某项严重故障不会被其他高分项掩盖。
# ===================================================================


def compute_health_score(
    f1_result: dict,
    f2_result: dict,
    f3_result: dict,
) -> dict:
    s1, s2, s3 = f1_result["score"], f2_result["score"], f3_result["score"]

    # 防止除零：将 0 分替换为极小值
    eps = 1e-6
    f1_safe = max(s1, eps)
    f2_safe = max(s2, eps)
    f3_safe = max(s3, eps)

    # 加权调和平均
    H = 1.0 / (0.4 / f1_safe + 0.3 / f2_safe + 0.3 / f3_safe)

    # 最小值惩罚（指数 0.6 比 sqrt 温和: 25分 → 0.44, 50分 → 0.66, 75分 → 0.85）
    penalty = (min(s1, s2, s3) / 100.0) ** 0.6

    # 最终评分
    S = H * penalty

    # 分类阈值（文档 Section 6）
    if S >= 70:
        recommendation = "推荐骑行"
        level = "good"
    elif S >= 50:
        recommendation = "谨慎使用"
        level = "caution"
    else:
        recommendation = "建议换车"
        level = "bad"

    return {
        "total_score": round(S, 2),
        "harmonic_mean": round(H, 2),
        "penalty_factor": round(penalty, 4),
        "level": level,
        "recommendation": recommendation,
        "sub_scores": {
            "tire_wobble": round(s1, 2),
            "chain_noise": round(s2, 2),
            "handlebar_misalignment": round(s3, 2),
        },
        "details": {
            "F1_tire_wobble": f1_result,
            "F2_chain_noise": f2_result,
            "F3_handlebar_misalignment": f3_result,
        },
    }


# ===================================================================
# 主流程
# ===================================================================


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("  共享单车健康快速检测系统  v2.0")
    print("  Bike Health Rapid Inspection System")
    print("=" * 60)

    # 加载
    print("\n[1/4] 加载传感器数据 ...")
    accel, gyro = load_sensor_data(SENSOR_FILE)
    print(f"      加速度计: {len(accel)} 条 | 陀螺仪: {len(gyro)} 条")

    print("\n[2/4] 加载音频数据 ...")
    audio = load_audio(PCM_FILE)
    audio_ts = load_audio_timestamps(AUDIO_TS_FILE)
    print(f"      PCM 样本: {len(audio)} | 时间戳块: {len(audio_ts)}")

    # 大数据自适应窗口选取
    window_result = select_analysis_window(accel, gyro, audio, audio_ts)
    if window_result["used_window"]:
        print(f"\n  ⚠ 数据时长 {window_result['duration_original_s']}s 超过阈值，"
              f"自动选取 {window_result['duration_window_s']}s 最优窗口")
    accel = window_result["accel_slice"]
    gyro = window_result["gyro_slice"]
    audio = window_result["audio_slice"]
    audio_ts = window_result["audio_ts_slice"]

    # 检测
    print("\n[3/4] 执行三级故障检测 ...")

    print("  ├─ F1 轮胎偏摆检测 ...")
    f1 = detect_tire_wobble(accel, gyro)
    print(f"  │   车轮转频: {f1['wheel_freq_hz']:.1f} Hz | 平整占比: {f1['flat_fraction']:.1%}")
    print(f"  │   幅值 f/2f: {f1['amplitude_f']:.4f} / {f1['amplitude_2f']:.4f}")
    print(f"  │   P = A1+0.5*A2 = {f1['P_value']:.4f}")
    print(f"  │   评分: {f1['score']:.1f}")

    print("  ├─ F2 链条异响检测 ...")
    pedal_freq = f1["wheel_freq_hz"]
    f2 = detect_chain_noise(audio, audio_ts, pedal_freq_hz=pedal_freq)
    print(f"  │   踏频: {pedal_freq:.1f} Hz | 预测: {f2['prediction']} | 异常分: {f2['anomaly_score']:.3f}")
    print(f"  │   包络谱SNR: {f2['pedal_snr_db']:.1f} dB | 谐波比: {f2['harmonic_ratio']:.2f} | 相位一致性: {f2['phase_consistency']:.2f}")
    print(f"  │   评分: {f2['score']:.1f}")

    print("  └─ F3 车头不正检测 ...")
    f3 = detect_handlebar_misalignment(gyro)
    print(f"      平均偏差 Δθ: {f3['delta_theta_deg']:.2f}° | 直行段数: {f3['straight_segments']}")
    print(f"      评分: {f3['score']:.1f}")

    # 综合
    print("\n[4/4] 综合健康评分（木桶效应）...")
    result = compute_health_score(f1, f2, f3)

    print("\n" + "─" * 60)
    print(f"  加权调和平均 H = {result['harmonic_mean']:.1f}")
    print(f"  最小值惩罚因子  = {result['penalty_factor']:.4f}")
    print(f"  最终评分 S = H × penalty = {result['total_score']:.1f}")
    print(f"  分级: {result['level']} → {result['recommendation']}")
    print("─" * 60)

    print("\n  子项评分明细 (0~100):")
    subs = result["sub_scores"]
    print(f"    F1 轮胎偏摆:  {subs['tire_wobble']:.1f}  (权重 0.40)")
    print(f"    F2 链条异响:  {subs['chain_noise']:.1f}  (权重 0.30)")
    print(f"    F3 车头不正:  {subs['handlebar_misalignment']:.1f}  (权重 0.30)")

    print("\n" + "=" * 60)
    return result


if __name__ == "__main__":
    main()
