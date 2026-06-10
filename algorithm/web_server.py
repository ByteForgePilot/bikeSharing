"""
共享单车健康快速检测系统 — Web 可视化服务 v2.0
支持用户上传数据文件，在线处理并展示结果。
启动后访问 http://127.0.0.1:5000
"""

from __future__ import annotations

import io
import os
import struct
import sys

import numpy as np
from flask import Flask, jsonify, render_template, request
from scipy import signal
from scipy.fft import fft, fftfreq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bike_health_detector import (  # type: ignore
    bandpass_filter,
    compute_health_score,
    detect_chain_noise,
    detect_handlebar_misalignment,
    detect_tire_wobble,
    resample_irregular,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB 上限


# =====================================================================
# 核心：接收用户上传的三个文件，运行检测，返回全部结果
# =====================================================================


@app.route("/api/process", methods=["POST"])
def api_process():
    """接收上传文件，执行三级检测，返回健康评分 + 全部图表数据。"""
    # 校验文件存在
    for key in ["sensor", "audio_pcm", "audio_ts"]:
        if key not in request.files:
            return jsonify({"error": f"缺少文件: {key}"}), 400

    try:
        # ---- 1. 解析传感器数据 ----
        sensor_raw = request.files["sensor"].read().decode("utf-8")
        accel, gyro, gps = _parse_sensor(sensor_raw)

        # ---- 2. 解析音频 PCM ----
        pcm_raw = request.files["audio_pcm"].read()
        audio = _parse_pcm(pcm_raw)

        # ---- 3. 解析音频时间戳 ----
        ts_raw = request.files["audio_ts"].read().decode("utf-8")
        audio_ts = _parse_audio_ts(ts_raw)

        # ---- 4. 大数据自适应窗口选取 (GPS 辅助) ----
        from bike_health_detector import select_analysis_window

        window_result = select_analysis_window(accel, gyro, audio, audio_ts, gps if gps else None)
        accel_s = window_result["accel_slice"]
        gyro_s = window_result["gyro_slice"]
        audio_s = window_result["audio_slice"]
        audio_ts_s = window_result["audio_ts_slice"]

        # GPS 裁剪到窗口
        gps_s = gps
        if gps and window_result.get("used_window"):
            ws_ns = window_result.get("window_start_ns", 0)
            we_ns = window_result.get("window_end_ns", float("inf"))
            gps_s = [g for g in gps if ws_ns <= g.timestamp_ns < we_ns]

        # GPS 平均车速 (F1 先验)
        gps_speeds = [g.speed_ms for g in gps_s if g.speed_ms > 0.5] if gps_s else []
        avg_speed_ms = sum(gps_speeds) / len(gps_speeds) if gps_speeds else None

        # ---- 5. 执行检测 ----
        f1 = detect_tire_wobble(accel_s, gyro_s, speed_ms=avg_speed_ms)
        f2 = detect_chain_noise(audio_s, audio_ts_s, pedal_freq_hz=f1["wheel_freq_hz"])
        f3 = detect_handlebar_misalignment(gyro_s, gps_s if gps_s else None)
        health = compute_health_score(f1, f2, f3)

        # ---- 6. 构建图表数据 ----
        f1_charts = _build_f1_charts(accel_s)
        f2_charts = _build_f2_charts(audio_s, audio_ts_s)
        f3_charts = _build_f3_charts(gyro_s)

        return jsonify({
            "health": health,
            "f1_charts": f1_charts,
            "f2_charts": f2_charts,
            "f3_charts": f3_charts,
            "data_summary": {
                "accel_count": len(accel_s),
                "gyro_count": len(gyro_s),
                "gps_count": len(gps_s),
                "audio_samples": int(len(audio_s)),
                "audio_ts_blocks": len(audio_ts_s),
                "used_window": window_result["used_window"],
                "original_duration_s": window_result.get("duration_original_s", 0),
            },
        })

    except Exception as e:
        return jsonify({"error": f"处理失败: {str(e)}"}), 500


# =====================================================================
# 文件解析（内存版本，无磁盘依赖）
# =====================================================================


def _parse_sensor(text: str) -> tuple[list, list, list]:
    accel, gyro, gps = [], [], []
    for line in text.strip().split("\n")[1:]:  # skip header
        parts = line.strip().split(",")
        if len(parts) < 12:
            continue
        ts = int(parts[0])
        stype = parts[1].strip()
        if stype == "加速度计":
            accel.append((ts, float(parts[2]), float(parts[3]), float(parts[4])))
        elif stype == "陀螺仪":
            gyro.append((ts, float(parts[9]), float(parts[10]), float(parts[11])))
        elif stype == "GPS":
            lat = float(parts[5]) if parts[5].strip() else 0.0
            lon = float(parts[6]) if parts[6].strip() else 0.0
            speed = float(parts[7]) if parts[7].strip() else 0.0
            course = float(parts[8]) if parts[8].strip() else 0.0
            gps.append((ts, lat, lon, speed, course))
    # 转成 bike_health_detector 需要的 dataclass 格式
    from bike_health_detector import AccelSample, GyroSample, GpsSample
    return (
        [AccelSample(ts, ax, ay, az) for ts, ax, ay, az in accel],
        [GyroSample(ts, gx, gy, gz) for ts, gx, gy, gz in gyro],
        [GpsSample(ts, lat, lon, spd, crs) for ts, lat, lon, spd, crs in gps],
    )


def _parse_pcm(raw: bytes) -> np.ndarray:
    n = len(raw) // 2
    samples = struct.unpack(f"<{n}h", raw)
    return np.array(samples, dtype=np.float32) / 32768.0


def _parse_audio_ts(text: str) -> list:
    chunks = []
    for line in text.strip().split("\n")[1:]:
        parts = line.strip().split(",")
        if len(parts) >= 2:
            from bike_health_detector import AudioChunk
            chunks.append(AudioChunk(int(parts[0]), int(parts[1])))
    return chunks


# =====================================================================
# 图表数据构建
# =====================================================================


def _build_f1_charts(accel) -> dict:
    if len(accel) < 64:
        return {}

    t0 = accel[0].timestamp_ns
    times = np.array([(a.timestamp_ns - t0) * 1e-9 for a in accel], dtype=np.float64)
    az = np.array([a.az for a in accel], dtype=np.float64)
    az -= np.mean(az)

    target_fs = 100.0
    _, az_u = resample_irregular(times, az, target_fs)
    filtered = bandpass_filter(az_u, target_fs, 2.0, 40.0, order=4)

    step = max(len(filtered) // 500, 1)
    t_disp = np.arange(len(filtered))[::step] / target_fs

    n = len(filtered)
    mag = np.abs(fft(filtered))[: n // 2] / (n / 2)
    freqs = fftfreq(n, 1.0 / target_fs)[: n // 2]
    mask = freqs <= 60

    return {
        "waveform": {"times": t_disp.tolist(), "az_filtered": filtered[::step].tolist()},
        "fft": {"freqs": freqs[mask].tolist(), "magnitude": mag[mask].tolist()},
    }


def _build_f2_charts(audio: np.ndarray, audio_ts: list) -> dict:
    if len(audio) == 0:
        return {}

    if len(audio_ts) >= 2:
        dt_ns = audio_ts[-1].timestamp_ns - audio_ts[0].timestamp_ns
        ds = audio_ts[-1].cumulative_samples - audio_ts[0].cumulative_samples
        orig_fs = ds / (dt_ns * 1e-9) if dt_ns > 0 else 16000.0
    else:
        orig_fs = 16000.0

    target_fs = 8000.0
    if abs(orig_fs - target_fs) > 100:
        num = int(len(audio) * target_fs / orig_fs)
        audio_8k = signal.resample(audio.astype(np.float64), num)
    else:
        audio_8k = audio.astype(np.float64)

    step = max(len(audio_8k) // 4000, 1)
    idx = np.arange(len(audio_8k))[::step]
    t_disp = (idx / target_fs).tolist()
    amp_disp = audio_8k[::step].tolist()

    n_fft = min(len(audio_8k), 4096)
    seg = audio_8k[:n_fft]
    mag = np.abs(fft(seg))[: n_fft // 2]
    freqs = fftfreq(n_fft, 1.0 / target_fs)[: n_fft // 2]
    mask = freqs <= 4000

    frame_len = int(target_fs * 0.01)
    n_frames = len(audio_8k) // frame_len
    energy = np.array([float(np.mean(audio_8k[i*frame_len:(i+1)*frame_len]**2))
                       for i in range(n_frames)])
    e_times = (np.arange(n_frames) * frame_len / target_fs).tolist()

    return {
        "waveform": {"times": t_disp, "amplitude": amp_disp},
        "fft": {"freqs": freqs[mask].tolist(), "magnitude": mag[mask].tolist()},
        "energy_envelope": {"times": e_times, "energy": energy.tolist()},
    }


def _build_f3_charts(gyro) -> dict:
    if len(gyro) < 32:
        return {}

    t0 = gyro[0].timestamp_ns
    times = [(g.timestamp_ns - t0) * 1e-9 for g in gyro]
    gx = [g.gx for g in gyro]
    gy = [g.gy for g in gyro]
    gz = [g.gz for g in gyro]

    yaw_angle = [0.0]
    for i in range(1, len(times)):
        yaw_angle.append(yaw_angle[-1] + gz[i] * (times[i] - times[i - 1]))

    return {
        "gyro": {"times": times, "gx": gx, "gy": gy, "gz": gz},
        "yaw_angle": {"times": times, "angle_deg": [float(np.degrees(a)) for a in yaw_angle]},
    }


# =====================================================================
# 前端页面
# =====================================================================


@app.route("/")
def index():
    return render_template("index.html")


def main() -> None:
    print("=" * 55)
    print("  共享单车健康快速检测系统 v2.0")
    print("  上传传感器数据 / 音频文件 → 在线检测")
    print(f"  访问: http://127.0.0.1:5000")
    print("=" * 55)
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
