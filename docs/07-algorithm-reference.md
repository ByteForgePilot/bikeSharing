# 07 -- 检测算法工程参考

bikeSharing 故障检测系统 (v3.0) 的全面技术参考。面向需要修改或扩展算法的工程师。

---

## 1. 架构与模块映射

### 文件职责

| 文件 | 角色 | 导出的函数 |
|------|------|-----------|
| app/ml/bike_health_detector.py | 核心算法逻辑 | detect_tire_wobble、detect_chain_noise、detect_handlebar_misalignment、compute_health_score、select_analysis_window、数据类 |
| app/services/detection_engine.py | 数据格式适配器 | parse_sensor_csv、parse_pcm、parse_audio_ts、dicts_to_accel、dicts_to_gyro、run_full_detection、run_f1_tire_wobble、run_f2_chain_noise、run_f3_handlebar |
| app/services/detection.py | 编排 + 数据库 | detect_from_files、detect_wheel_wobble (DB)、detect_chain_noise (DB)、detect_handlebar (DB) |
| app/api/detection.py | HTTP 接口 | /upload、/process、/dashboard、/report |
| app/ml/__init__.py | 重新导出 | AccelSample、GyroSample、AudioChunk、所有 detect_* 函数 |

### 调用链

```
POST /api/detection/process
  -> api/detection.py: api_process()
    -> services/detection_engine.py: parse_sensor_csv()
    -> services/detection_engine.py: parse_pcm()
    -> services/detection_engine.py: parse_audio_ts()
    -> services/detection_engine.py: run_full_detection()
      -> ml/bike_health_detector.py: select_analysis_window()
      -> ml/bike_health_detector.py: detect_tire_wobble()
      -> ml/bike_health_detector.py: detect_chain_noise()
      -> ml/bike_health_detector.py: detect_handlebar_misalignment()
      -> ml/bike_health_detector.py: compute_health_score()
```

---

## 2. 数据结构

### AccelSample

```python
@dataclass
AccelSample:
  timestamp_ns: int     # 自纪元以来的纳秒数
  ax: float             # m/s^2
  ay: float             # m/s^2
  az: float             # m/s^2（含重力，静止时约 9.81）
```

### GyroSample

```python
@dataclass
GyroSample:
  timestamp_ns: int     # 自纪元以来的纳秒数
  gx: float             # rad/s
  gy: float             # rad/s
  gz: float             # rad/s
```

### AudioChunk

```python
@dataclass
AudioChunk:
  timestamp_ns: int              # 自纪元以来的纳秒数
  cumulative_samples: int        # 该时间戳处的累积音频样本数
```

---

## 3. 工具函数

### resample_irregular(times, values, target_fs) -> (t_new, v_new)

- 对不规则时间间隔的传感器数据进行线性插值，生成均匀网格
- 三个检测器在频谱分析前均使用此函数
- **核心**：numpy.interp

### bandpass_filter(data, fs, lowcut, highcut, order=4) -> ndarray

- Butterworth 带通滤波器，通过 scipy.signal.filtfilt 应用（零相位）
- 内置限幅：lowcut/highcut 自动裁剪到奈奎斯特频率的 [0.001, 0.999] 范围内
- 若 lowcut >= highcut，直接返回原始数据

### sliding_variance(data, window, step) -> ndarray

- 通过 numpy.lib.stride_tricks.sliding_window_view 实现向量化滑动窗口方差
- **复杂度**：每个窗口 O(n)

### estimate_wheel_frequency(accel_z, fs, speed_ms=None) -> float

- 对 Z 轴加速度做 FFT，在 [1.5, 8.0] Hz 范围内搜索峰值
- 有 GPS 速度时：以 v / (2*pi*0.35) 为中心搜索，±2 Hz 裕量
- 无 GPS 时：全范围峰值搜索

---

## 4. 自适应窗口选择

### select_analysis_window(accel, gyro, audio, audio_ts) -> dict

对于长录音（>30s），选择骑行质量最高的最优 15s 窗口。

**参数**：

| 变量 | 默认值 | 环境变量覆盖 | 说明 |
|------|--------|-------------|------|
| MAX_DURATION_S | 30.0 | BIKE_MAX_DURATION_S | 触发窗口选择的阈值 |
| WINDOW_DURATION_S | 15.0 | BIKE_WINDOW_DURATION_S | 选择的窗口长度 |
| score_fs | 50 | （硬编码） | 评分网格的重采样率 |

**算法**：
1. 计算传感器和音频时长
2. 若任一超过 MAX_DURATION_S，进入窗口选择
3. 将 Z 轴加速度重采样到均匀的 50Hz 网格
4. 滑动重叠窗口（步长 = 窗口长度/4）
5. 给每个窗口评分：az_variance + 10 * gz_variance（越低越好）
6. 选择评分最低的窗口 → 最高骑行质量
7. 裁剪传感器数据和音频，匹配所选时间范围

**边界情况**：
- 若传感器数据 < 64 样本，直接返回原始数据
- 若重采样后长度 < 窗口样本数 (15*50=750)，返回原始数据
- 音频时间戳映射裁剪到最近的块边界，±1 保护块

---

## 5. F1 -- 轮胎偏摆检测

### detect_tire_wobble(accel, gyro=None, speed_ms=None) -> dict

**信号链**：

```
加速度计 Z 轴（不规则 100Hz）
  -> [去直流] 减去均值
  -> [重采样] 均匀 100Hz 网格
  -> [带通滤波] Butterworth 4 阶，2-40 Hz
  -> [平坦路面选择] 滑动方差 < 0.5，1s 窗口
  -> [FFT] 归一化幅值 |A|/N*2
  -> [峰值提取] A1 @ 车轮频率，A2 @ 2*车轮频率
  -> [评分] P = A1 + 0.5*A2，线性插值
```

**关键参数**：

| 参数 | 值 | 说明 |
|------|-----|------|
| WHEEL_RADIUS | 0.35 m | 共享单车车轮半径 |
| target_fs | 100.0 Hz | 加速度计重采样率 |
| bandpass low/high | 2.0 / 40.0 Hz | 去除低频漂移和高频噪声 |
| flat_window_s | 1.0 s | 路面质量检查窗口 |
| flat_threshold | 0.5 (m/s^2)^2 | 低于此值 = 平坦路面 |
| flat_min_fraction | 0.2 (20%) | 使用平坦路面数据的最小比例 |
| P_healthy | 0.15 | 低于此值 → 得分=100 |
| P_severe | 0.60 | 高于此值 → 得分=0 |
| flat_confidence_threshold | 0.3 (30%) | 若平坦比例 < 30%，得分上限为 75 |
| fft_margin_hz | 0.3 Hz | amplitude_at() 的频率搜索窗口 |

**得分映射**：
```
score = 100                          if P <= 0.15
        100 * (1 - (P-0.15)/0.45)    if 0.15 < P < 0.60
        0                             if P >= 0.60
```

**输出字典**：
```python
{
    "score": float,          # 0-100
    "wheel_freq_hz": float,  # 估计的车轮旋转频率
    "amplitude_f": float,    # 车轮频率处的 FFT 幅值
    "amplitude_2f": float,   # 2 倍车轮频率处的 FFT 幅值
    "P_value": float,        # A1 + 0.5*A2
    "flat_fraction": float,  # 被分类为平坦路面的窗口比例
}
```

**修改指南**：
- 调整灵敏度：修改 P_healthy / P_severe 阈值
- 调整频率范围：修改 bandpass_filter 参数或 estimate_wheel_frequency 搜索范围
- 添加 GPS 集成：从骑行 GPS 数据传入 speed_ms
- 可通过将 flat_threshold 设为较大值来禁用车厢路面选择

---

## 6. F2 -- 链条异响检测

### detect_chain_noise(audio, audio_chunks, pedal_freq_hz=None) -> dict

**信号链**：

```
音频 PCM（可变采样率）
  -> [重采样] 8kHz 均匀
  -> [踏板频率估计] 自相关（若未提供）
  -> [带通] Butterworth 4 阶，2000-4000 Hz（链条共振频段）
  -> [希尔伯特包络] 解析信号幅值
  -> [低通] 4 阶，10 Hz（仅保留踏板频率包络）
  -> [特征提取]：
     |- 包络频谱 SNR @ 踏板频率（±0.3 Hz 裕量）
     |- 谐波检测（2f, 3f）
     |- 相位一致性（峰值间隔的循环方差）
     |- 倒谱周期性评分（1/踏板频率处的倒频率 SNR）
  -> [辅助特征]：
     |- 高频能量比（2000-4000 Hz / 全频段）
     |- 波峰因子（峰值 / RMS）
  -> [融合] 加权异常评分 -> 置信度 -> 最终得分
```

**关键参数**：

| 参数 | 值 | 说明 |
|------|-----|------|
| target_fs | 8000.0 Hz | 音频重采样率 |
| bandpass low/high | 2000 / 4000 Hz | 链条共振频段 |
| envelope_lp_cutoff | 10.0 Hz | 保留踏板频段包络 |
| snr_margin | 0.3 Hz | 踏板频率周围的频谱搜索窗口 |
| n_harmonics | 3 | 检查的谐波数量（2f, 3f, 4f） |
| harmonics_noise_factor | 2.0 | 峰值必须 > 2 倍噪声基底才能计数 |
| phase_consistency_min_peaks | 4 | 相位分析所需的最小峰值数 |
| cepstrum_snr_healthy_range | ≤2 | 倒谱 SNR：低于 2 → 0（正常） |
| cepstrum_snr_bad_range | ≥8 | 倒谱 SNR：高于 8 → 1（链条问题） |

**特征融合权重**：
```
envelope_score = 0.35*snr_score + 0.25*harm_score + 0.20*phase_score + 0.20*cepstrum_score
auxiliary_score = 0.55*hf_ratio_score + 0.45*crest_factor_score
anomaly_score = 0.60*envelope_score + 0.40*auxiliary_score
```

**得分映射**：
```
anomaly < 0.25 => prediction="正常", confidence=0.8 + (0.25-anomaly)*0.8
anomaly > 0.55 => prediction="异响", confidence=0.8 + (anomaly-0.55)*0.5
0.25-0.40      => prediction="正常", confidence=0.5 + (0.40-anomaly)*2.0
0.40-0.55      => prediction="异响", confidence=0.5 + (anomaly-0.40)*2.0
```

**踏板频率估计**：
- 仅当 F1 未提供 pedal_freq_hz 时使用
- 方法：希尔伯特包络 -> 低通 -> 自相关，搜索 0.2-1.0s 延迟（1-5 Hz）
- 后备方案：若估计失败，使用 3.0 Hz

**输出字典**：
```python
{
    "score": float,             # 0-100
    "prediction": str,          # "正常" 或 "异响"
    "confidence": float,        # 0.5-1.0
    "pedal_snr_db": float,      # 踏板频率处的包络频谱 SNR
    "harmonic_ratio": float,    # 检测到的谐波比例（0-1）
    "phase_consistency": float, # 循环方差 R（0-1，1=完美）
    "cepstrum_score": float,    # 倒谱周期性（0-1）
    "hf_energy_ratio": float,   # 2-4kHz / 全频段能量比
    "anomaly_score": float,     # 综合异常评分（0-1）
}
```

**修改指南**：
- **误报太多**：提高 anomaly_score 阈值（0.25 -> 0.35，0.55 -> 0.65）
- **漏报太多**：降低阈值
- **链条共振频段**：2000-4000 Hz 为经验选择。用真实链条异响录音验证和调整
- **添加新特征**：扩展第 11 节的融合公式，分配权重
- **踏板频率关联**：run_full_detection 中复用了 F1 的 wheel_freq_hz 作为 pedal_freq —— 若速度不同，需解耦

---

## 7. F3 -- 车头不正检测

### detect_handlebar_misalignment(gyro) -> dict

**信号链**：

```
陀螺仪 Z 轴（不规则 50Hz）
  -> [重采样] 均匀 50Hz
  -> [窗口扫描] 5s 滑动窗口，步长=1.25s
  -> [选择最佳 30%] 最低 gz 方差
  -> [质量门限] 最佳 gz_std < 0.3 rad/s
  -> [计算偏置] 最佳窗口的 gz 均值
  -> [计算偏航] gz * dt 的累积和
  -> [Delta theta] 0.7*|bias|*2s + 0.3*|yaw_deviation|
  -> [评分] 线性插值 5°/15°
```

**关键参数**：

| 参数 | 值 | 说明 |
|------|-----|------|
| target_fs | 50.0 Hz | 陀螺仪重采样率 |
| window_s | 5.0 s | 直行段分析的窗口长度 |
| best_fraction | 0.3 (30%) | 保留的窗口比例 |
| MAX_STRAIGHT_STD | 0.3 rad/s | 质量门限：最佳窗口 gz_std > 0.3 则拒绝 |
| T_obs | 2.0 s | 观测时间尺度：将 gz 偏置映射为角度 |
| theta_ok | 5.0 度 | 低于此值 -> 得分=100 |
| theta_bad | 15.0 度 | 高于此值 -> 得分=0 |
| yaw_weight | 0.7 | 偏置导出角度的融合权重 |
| yaw_deviation_weight | 0.3 | 累积偏航偏差的权重 |

**得分映射**：
```
score = 100                    if delta_theta <= 5°
        100 * (1 - (t-5)/10)  if 5° < delta_theta < 15°
        0                       if delta_theta >= 15°
```

**输出字典**：
```python
{
    "score": float,             # 0-100
    "delta_theta_deg": float,  # 等效转向偏角（度）
    "yaw_bias_rad_s": float,   # 稳态陀螺仪 Z 偏置
    "straight_segments": int,  # 合格的直行段数量
    "warning": str,            # 未找到有效直行段时出现
}
```

**边界情况**：
- gyro < 32 样本：返回 score=100（"无数据，假设正常"）
- 最佳段 gz_std > 0.3 rad/s：返回警告，score=100（"无法测量"）
- 未找到直行段（所有数据均为转弯）：返回警告

**修改指南**：
- **灵敏度**：降低 theta_bad 以检测更小的偏角
- **直行段检测**：降低 MAX_STRAIGHT_STD 以要求更直的骑行
- **观测时间**：增大 T_obs 以放大微小偏置（风险：噪声放大）
- **转弯过滤**：若单车持续在弯道上骑行，增大 window_s 以补偿

---

## 8. 综合健康评分

### compute_health_score(f1, f2, f3) -> dict

**公式**：
```
H = 1 / (0.4/F1 + 0.3/F2 + 0.3/F3)     # 加权调和平均
penalty = min(F1, F2, F3) / 100          # 最小值惩罚因子
S = H * penalty                          # 最终得分 0-100
```

**权重说明**：

| 分量 | 权重 | 理由 |
|------|------|------|
| F1（轮胎） | 0.40 | 安全关键，故障率最高 |
| F2（链条） | 0.30 | 重要但极少灾难性 |
| F3（车头） | 0.30 | 重要但逐渐退化 |

**分类**：

| S 范围 | 等级 | 建议 | 颜色 |
|--------|------|------|------|
| >= 70 | good | 推荐骑行 | 绿色 |
| 50-69 | caution | 谨慎使用 | 黄/橙色 |
| < 50 | bad | 建议换车 | 红色 |

**输出字典**：
```python
{
    "total_score": float,        # S = H * penalty
    "harmonic_mean": float,      # H 值
    "penalty_factor": float,     # penalty = min / 100
    "level": str,                # "good" | "caution" | "bad"
    "recommendation": str,       # 中文建议文本
    "sub_scores": {
        "tire_wobble": float,     # F1 得分
        "chain_noise": float,     # F2 得分
        "handlebar_misalignment": float,  # F3 得分
    },
    "details": {
        "F1_tire_wobble": dict,   # 完整 F1 输出
        "F2_chain_noise": dict,   # 完整 F2 输出
        "F3_handlebar_misalignment": dict,  # 完整 F3 输出
    },
}
```

**修改指南**：
- **调整权重**：编辑 0.4、0.3、0.3 比例
- **移除木桶效应**：设置 penalty = 1.0（S = H 直接）
- **更严格惩罚**：使用 min(F1,F2,F3)/50 使惩罚更严厉
- **更改分类阈值**：调整 S >= 70 / S >= 50 的边界

---

## 9. 测试与验证

### 单元测试

```
tests/test_detection_engine.py  # 使用合成数据测试所有 detect_* 函数
```

**测试数据辅助函数**（在 conftest.py 中）：
- _make_accel(n, freq=0)：生成合成加速度数据，可选车轮频率振动
- _make_gyro(n, bias=0)：生成合成陀螺仪数据，可选偏航偏置
- _make_audio(n, pedal_freq=0)：生成合成音频，可选链条冲击模式

**测试覆盖清单**：
- F1：干净数据（期望 100）、严重偏摆（期望 0）、混合路面
- F2：干净链条（期望 normal）、链条异响（期望 异响）、环境噪声（期望 normal）
- F3：车头正常（期望 100）、车头不正（期望 <100）、纯转弯数据（期望 warning）
- 评分：使用已知 F1/F2/F3 值验证综合得分
- 窗口选择：验证超过 30s 的数据和短数据边界情况

### 真实数据测试

```bash
cd bikrsharing
python data/run_detection.py
```

从 data/ 目录读取真实传感器数据，将完整结果保存到 data/detection_result.json。

---

## 10. 修改清单

修改检测算法时，请验证：

- [ ] 代码中所有 ## ---- 节标题已更新
- [ ] 参数值已在本参考中记录
- [ ] 默认值和环境变量覆盖保持同步
- [ ] 为新的边界情况重新生成测试数据
- [ ] detection_engine.py 适配器保持不变（除非 API 格式变更）
- [ ] 评分保持 0-100 范围以保证兼容性
- [ ] data/run_detection.py 输出格式不变以保证仪表板兼容

---

## 11. 参数速查

所有可调参数一览表：

| 符号 | 位置 | 默认值 | 单位 | 效果 |
|------|------|--------|------|------|
| WHEEL_RADIUS | 全局 | 0.35 | 米 | 通过 GPS 速度计算车轮频率 |
| MAX_DURATION_S | select_analysis_window | 30（环境变量：BIKE_MAX_DURATION_S） | 秒 | 窗口选择触发器 |
| WINDOW_DURATION_S | select_analysis_window | 15（环境变量：BIKE_WINDOW_DURATION_S） | 秒 | 选中窗口时长 |
| flat_threshold | detect_tire_wobble | 0.5 | (m/s^2)^2 | 平坦路面方差门限 |
| P_healthy | detect_tire_wobble | 0.15 | - | 低于此值 = 满分 |
| P_severe | detect_tire_wobble | 0.60 | - | 高于此值 = 零分 |
| chain_bp_lo | detect_chain_noise | 2000 | Hz | 链条共振低截止 |
| chain_bp_hi | detect_chain_noise | 4000 | Hz | 链条共振高截止 |
| envelope_lp | detect_chain_noise | 10 | Hz | 包络跟踪速度 |
| MAX_STRAIGHT_STD | detect_handlebar_misalignment | 0.3 | rad/s | 直行段质量门限 |
| T_obs | detect_handlebar_misalignment | 2.0 | 秒 | 偏置到角度映射 |
| theta_ok | detect_handlebar_misalignment | 5.0 | 度 | 低于此值 = 满分 |
| theta_bad | detect_handlebar_misalignment | 15.0 | 度 | 高于此值 = 零分 |
| F1_weight | compute_health_score | 0.40 | - | 轮胎偏摆权重 |
| F2_weight | compute_health_score | 0.30 | - | 链条异响权重 |
| F3_weight | compute_health_score | 0.30 | - | 车头不正权重 |
