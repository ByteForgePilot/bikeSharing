# 04 — 故障检测算法详解

## 概述

三种故障检测算法位于 `backend/app/services/`，每个算法输出统一格式：

```json
{
  "detected": "normal" | "suspect" | "fault" | "unknown",
  "confidence": 0.0 ~ 1.0,
  "detail": "人类可读的诊断信息"
}
```

**分类层级：**
- **normal** — 指标在正常范围内
- **suspect** — 指标异常，建议关注
- **fault** — 指标显著异常，极可能存在故障
- **unknown** — 数据不足，无法判断

当前实现使用简化阈值法（RMS/统计），为后续频谱分析和 ML 模型预留升级空间。

---

## 1. 轮胎偏摆检测 (Wheel Wobble)

**文件：** `backend/app/services/sensor_analysis.py`
**函数：** `analyze_wheel_wobble(accelerometer_data, sample_rate, wobble_threshold)`

### 物理原理

```
轮胎偏摆 → 轮毂不圆 → 每转一圈产生一次径向冲击
→ 通过车架传到车把 → 手机加速度计检测到周期性振动

骑行速度 10-20 km/h, 26" 车轮:
  转速 ≈ 2-4 rev/s (Hz)
  对应振动基频 ≈ 2-4 Hz
```

### 当前算法：组合 RMS 能量检测

```
1. 数据校验
   if 数据点数 < sample_rate * 2:
       return "unknown"   # 至少需要 2 秒数据

2. 提取加速度分量
   x_vals = [d["x"] for d in accelerometer_data]   # 横向（主要敏感轴）
   z_vals = [d["z"] for d in accelerometer_data]   # 竖向（辅助）

3. 计算组合 RMS
   x_rms = sqrt(Σ(x²) / N)
   z_rms = sqrt(Σ(z²) / N)
   combined_rms = sqrt(x_rms² + z_rms²)

4. 阈值分类
   threshold = wobble_threshold (默认 0.3 m/s²)

   combined_rms < 0.5 * threshold → normal,   confidence = 1.0 - (rms / (0.5*t))
   0.5*t ≤ rms < threshold       → suspect,   confidence = rms / t
   rms ≥ threshold               → fault,     confidence = min(rms / (2*t), 1.0)
```

**confidence 曲线示意：**
```
confidence
  1.0 ┤          ╭────────
      │         ╱
  0.5 ┤        ╱
      │       ╱
  0.0 ┤──────╯
      └──────┼────────┼──────────► RMS
          0.5*t      t         2*t
         (0.15)    (0.3)      (0.6)
```

### 阈值调优指南

| 场景 | `wobble_threshold` | 说明 |
|------|-------------------|------|
| 高灵敏度（少漏报） | 0.2 | 轻微振动即报警，误报率较高 |
| 默认 | 0.3 | 平衡灵敏度与特异度 |
| 低灵敏度（少误报） | 0.5 | 仅严重偏摆报警，可能漏报 |

### 算法升级方向

**阶段 2：FFT 频谱分析**
```
当前缺陷: RMS 无法区分"3Hz 偏摆振动"和"路面颠簸宽带噪声"
升级方案:
  1. 对 x 轴信号做 FFT → 频谱
  2. 在 1-5 Hz 频带内寻找最大峰值
  3. 计算"带内能量 / 带外能量"比值
  4. 比值 > 阈值 → fault
优势: 频域分析天然滤除路面随机噪声
```

**阶段 3：ML 分类器**
```
特征向量: [FFT峰值频率, 带内能量比, RMS, 骑行速度估计, ...]
分类器:   RandomForest / SVM
训练数据: 标注的正常/偏摆骑行数据（ml/data/）
```

---

## 2. 链条异响检测 (Chain Noise)

**文件：** `backend/app/services/audio_analysis.py`
**函数：** `analyze_chain_noise(audio_features, noise_threshold)`

### 物理原理

```
正常链条: 平滑的金属摩擦声，频谱能量分布均匀
异常链条:
  - 干涩/生锈 → 高频吱吱声 (2-8 kHz)
  - 松链/卡链 → 低频咔咔声 (与踏频同步，约 1-2 Hz)
```

### 当前算法：统计异常检测

```
1. 数据校验
   if audio_features 为空:
       return "unknown"

2. 计算统计量
   mean = Σ(features) / N
   variance = Σ((f - mean)²) / N
   std_dev = sqrt(variance)

3. 异常分数
   anomaly_score = (mean + std_dev) / (noise_threshold * 2 + 1e-6)

4. 分类
   anomaly_score < 0.5  → normal,    confidence = 1.0 - score
   0.5 ≤ score < 1.0    → suspect,   confidence = score
   score ≥ 1.0          → fault,     confidence = min(score / 2, 1.0)
```

**说明：** `audio_features` 预期为预计算的特征向量（如 MFCC 各系数的均值），
由移动端或前置处理步骤提取。当前测试直接传入标量列表。

### 阈值调优

| 场景 | `noise_threshold` | 说明 |
|------|------------------|------|
| 安静环境 | 0.3 | 背景噪声低，敏感度高 |
| 默认 | 0.5 | 城市骑行环境 |
| 嘈杂环境 | 0.8 | 交通噪声大，需更高阈值 |

### 算法升级方向

**阶段 2：MFCC + 频谱分析**
```
当前缺陷: 简单的均值/标准差无法区分"链条异响"和"风噪/语音"
升级方案:
  1. 音频分帧 (25ms, 10ms hop)
  2. 每帧提取 MFCC (13维) + 频谱质心 + 过零率
  3. 使用 librosa.feature.mfcc() 批量计算
  4. 对 MFCC 矩阵做时序统计 (mean, std, delta, delta-delta)
```

**阶段 3：音频事件分类**
```
模型: CNN / LSTM 对 MFCC 序列分类
类别: {正常, 干涩异响, 松链咔咔, 风噪, 语音}
输出: 各类别概率 + 最终判定
```

---

## 3. 车头不正检测 (Handlebar Misalignment)

**文件：** `backend/app/services/fault_classifier.py`
**函数：** `classify_handlebar(gyroscope_data, sample_rate, offset_threshold_deg)`

### 物理原理

```
正常车头: 车把居中时前轮对准车架中线 → 骑行直线时陀螺仪偏航角 ≈ 0
车头不正: 车把居中但前轮偏转 → 为保持直线，车手必须将车把偏转一个补偿角
        → 陀螺仪偏航角存在系统性非零偏移
```

### 当前算法：均值偏移 + 离群值剔除

```
1. 数据校验
   if 数据点数 < sample_rate * 3:
       return "unknown"   # 至少需要 3 秒数据

2. 提取偏航角 (z 轴)
   yaw_vals = [d["z"] for d in gyroscope_data]

3. 离群值剔除 (10% 截尾)
   sorted_yaw = sorted(yaw_vals)
   trim = N // 10
   trimmed = sorted_yaw[trim : -trim]

4. 均值偏移
   mean_yaw = mean(trimmed)
   ratio = abs(mean_yaw) / offset_threshold_deg

5. 分类
   ratio < 0.5   → normal,    confidence = 1.0 - ratio
   0.5 ≤ r < 1.0 → suspect,   confidence = ratio
   r ≥ 1.0       → fault,     confidence = min(ratio / 2, 1.0)
```

### 为什么需要截尾？

```
骑行中偶发的瞬时偏转（避障、转弯）会产生极大的偏航角尖峰。
截尾 10% 可以剔除这些不属于"系统性偏移"的离群值，
避免它们拉偏均值导致误报。

注意：此方法假设用户在数据采集期间是"直线骑行"的。
如果用户在全程转弯，均值偏移将无意义。
```

### 阈值调优

| 场景 | `offset_threshold_deg` | 说明 |
|------|----------------------|------|
| 竞赛公路车 | 2.0° | 车头精度要求高 |
| 默认（城市自行车） | 3.0° | 适中 |
| 宽容模式 | 5.0° | 仅检测严重不正 |

### 算法升级方向

**阶段 2：GPS 辅助直行检测**
```
当前缺陷: 无法判断用户是否在直行（转弯时的偏航偏移是正常的）
升级方案:
  1. 利用手机 GPS/罗盘检测行驶方向变化
  2. 仅在"直行片段"上计算均值偏移
  3. 剔除转弯片段（GPS 方向变化 > 5°/s）
```

**阶段 3：多传感器融合**
```
使用加速度计 + 陀螺仪 + 磁力计做姿态估计 (Mahony/Madgwick 滤波器)
→ 获取更准确的偏航角（融合了重力参考和地磁参考）
```

---

## 4. 算法对比总结

| 维度 | 轮胎偏摆 | 链条异响 | 车头不正 |
|------|---------|---------|---------|
| 传感器 | 加速度计 | 麦克风 | 陀螺仪 |
| 采样率 | 50 Hz | 44100 Hz | 50 Hz |
| 最少数据 | 2 秒 | 无硬性要求 | 3 秒 |
| 核心指标 | 组合 RMS | 均值+标准差 | 截尾均值偏移 |
| 阈值参数 | `wobble_threshold`=0.3 | `noise_threshold`=0.5 | `offset_threshold_deg`=3.0 |
| 离群值处理 | 无 | 无 | 10% 截尾 |
| 频域分析 | 已规划 (FFT) | 已规划 (MFCC) | 不适用 |
| 服务函数 | `analyze_wheel_wobble` | `analyze_chain_noise` | `classify_handlebar` |

---

## 5. 公共接口约定

所有检测函数遵循相同的输入输出协议，便于新故障类型的加入：

**输入：** 特定传感器的原始数据列表 + 配置参数
**输出：**
```python
{
    "detected": str,    # normal | suspect | fault | unknown
    "confidence": float, # 0.0 ~ 1.0, 保留两位小数
    "detail": str        # 包含关键指标值和阈值
}
```

添加第 4 种故障类型时：
1. 在 `backend/app/services/` 新建分析函数
2. 在 `backend/app/schemas/__init__.py` 添加请求 Schema
3. 在 `backend/app/api/detection.py` 添加路由
4. 在 `backend/tests/test_services.py` 添加测试类
5. （可选）在 `FaultReport` 模型中添加对应列
