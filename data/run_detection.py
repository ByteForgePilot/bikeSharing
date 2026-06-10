"""
快速检测脚本 --- 对 data/ 目录下的真实传感器数据运行三级故障检测。

使用方式（项目根目录下执行）：
    cd E:/Project/personal/bikrsharing
    python data/run_detection.py

依赖：pip install -r backend/requirements.txt
"""

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.detection_engine import (
    parse_sensor_csv,
    parse_pcm,
    parse_audio_ts,
    run_full_detection,
)

DATA_DIR = Path(__file__).resolve().parent

sensor_files = list(DATA_DIR.glob("*传感器*数据*")) + list(DATA_DIR.glob("*.txt"))
pcm_files = list(DATA_DIR.glob("*.pcm"))
ts_files = list(DATA_DIR.glob("*时间戳*")) + list(DATA_DIR.glob("*timestamp*"))

if not sensor_files or not pcm_files or not ts_files:
    print("错误：在 data/ 目录中找不到传感器数据文件。")
    print(f"  期望: 传感器数据.txt / 音频.pcm / 音频_时间戳.csv")
    print(f"  找到的 txt: {[f.name for f in sensor_files]}")
    print(f"  找到的 pcm: {[f.name for f in pcm_files]}")
    print(f"  找到的 csv: {[f.name for f in ts_files]}")
    sys.exit(1)


def main():
    sensor_path = sensor_files[0]
    pcm_path = pcm_files[0]
    ts_path = ts_files[0]

    print("=" * 60)
    print("  单车健康快速检测 - 真实数据测试")
    print("=" * 60)

    print(f"\n[1/4] 读取传感器数据 ...")
    sensor_text = sensor_path.read_text(encoding="utf-8")
    print(f"      文件: {sensor_path.name} ({sensor_path.stat().st_size / 1024:.0f} KB)")

    print(f"\n[2/4] 读取音频数据 ...")
    pcm_bytes = pcm_path.read_bytes()
    ts_text = ts_path.read_text(encoding="utf-8")
    print(f"      PCM: {pcm_path.name} ({pcm_path.stat().st_size / 1024:.0f} KB)")
    print(f"      时间戳: {ts_path.name} ({ts_path.stat().st_size / 1024:.0f} KB)")

    print(f"\n[3/4] 解析数据 ...")
    accel, gyro = parse_sensor_csv(sensor_text)
    audio = parse_pcm(pcm_bytes)
    audio_ts_list = parse_audio_ts(ts_text)
    print(f"      加速度: {len(accel)} 条 | 陀螺仪: {len(gyro)} 条")
    print(f"      音频: {len(audio)} 采样 | 时间戳块: {len(audio_ts_list)}")

    print(f"\n[4/4] 执行三级故障检测 ...")
    result = run_full_detection(accel, gyro, audio, audio_ts_list)

    health = result["health"]
    f1 = result["f1"]
    f2 = result["f2"]
    f3 = result["f3"]
    summary = result["data_summary"]
    used_window = result["window_used"]

    print(f"\n{'─' * 60}")
    print(f"  数据概览: {summary['accel_count']} accel / {summary['gyro_count']} gyro / "
          f"{summary['audio_samples']} audio")
    if used_window:
        print(f"  自动选取了最优时间段 (原始数据较长)")
    print()

    print(f"  F1 轮胎偏摆:")
    print(f"      车轮转频: {f1['wheel_freq_hz']:.1f} Hz")
    print(f"      平整占比: {f1['flat_fraction']:.1%}")
    print(f"      P = A1+0.5*A2 = {f1['P_value']:.4f}")
    print(f"      评分: {f1['score']:.1f}")
    print()

    print(f"  F2 链条异响:")
    print(f"      预测: {f2['prediction']} (置信度: {f2['confidence']:.3f})")
    print(f"      包络谱 SNR: {f2['pedal_snr_db']:.1f} dB")
    print(f"      谐波比: {f2['harmonic_ratio']:.3f}")
    print(f"      相位一致性: {f2['phase_consistency']:.3f}")
    print(f"      评分: {f2['score']:.1f}")
    print()

    print(f"  F3 车头不正:")
    print(f"      delta_theta: {f3['delta_theta_deg']:.2f} deg")
    print(f"      yaw bias: {f3['yaw_bias_rad_s']:.4f} rad/s")
    print(f"      直行段: {f3['straight_segments']}")
    print(f"      评分: {f3['score']:.1f}")
    print()

    print(f"{'─' * 60}")
    print(f"  综合健康评分:")
    print(f"      加权调和平均 H = {health['harmonic_mean']:.1f}")
    print(f"      最小值惩罚因子 = {health['penalty_factor']:.4f}")
    print(f"      最终评分 S = {health['total_score']:.1f} / 100")
    print(f"      等级: {health['level']} -> {health['recommendation']}")
    print(f"{'─' * 60}")

    out_path = DATA_DIR / "detection_result.json"
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n详细结果已保存到: {out_path}")

    return result


if __name__ == "__main__":
    main()
