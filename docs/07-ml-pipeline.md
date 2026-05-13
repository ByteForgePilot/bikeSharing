# 07 — ML 流水线与实验

## 概述

ML 实验目录 `ml/` 为算法工程师提供独立的工作空间，用于数据探索、特征工程、
模型训练和评估。ML 代码与后端服务代码分离，训练好的模型可通过序列化文件
（`.pkl` / `.joblib`）部署到后端。

---

## 目录结构

```
ml/
├── requirements.txt              # ML 环境依赖（独立 pip install）
├── data/
│   ├── raw/                      # 原始传感器数据 (CSV/WAV)
│   │   └── .gitkeep
│   ├── processed/                # 预处理后的特征数据
│   │   └── .gitkeep
├── models/                       # 训练完成的模型文件
│   └── .gitkeep
└── notebooks/                    # Jupyter 实验笔记
    └── 01_data_exploration.ipynb
```

**`.gitkeep` 说明：** 数据文件和模型文件被 `.gitignore` 排除，
`.gitkeep` 仅用于在 git 中保留目录结构。

---

## 环境配置

### 使用根目录 Conda 环境（推荐）

```bash
conda activate bikeSharing
# 已包含 numpy, scipy, pandas, matplotlib, seaborn,
# scikit-learn, jupyter, librosa
```

`ml/requirements.txt` 中的依赖已全部包含在 `environment.yml` 中。

### 使用 pip 独立安装

```bash
cd ml
pip install -r requirements.txt
```

---

## 依赖清单

| 包 | 版本 | 用途 |
|----|------|------|
| numpy | 2.2.1 | 数值计算基础 |
| scipy | 1.14.1 | FFT/信号处理 |
| librosa | 0.10.2 | 音频特征提取 (MFCC, 频谱等) |
| scikit-learn | 1.6.0 | ML 分类器 (SVM, RF, etc.) |
| pandas | 2.2.3 | 数据加载/清洗/分析 |
| matplotlib | 3.10.0 | 数据可视化 (波形图/频谱图) |
| seaborn | 0.13.2 | 统计可视化 (热力图/分布图) |
| jupyter | 1.1.1 | 交互式笔记环境 |
| joblib | 1.4.2 | 模型序列化/反序列化 |

---

## Notebook 01: 数据探索

**文件：** `ml/notebooks/01_data_exploration.ipynb`

### 内容结构

| Cell | 类型 | 内容 |
|------|------|------|
| 0 | Markdown | 标题 + 目标说明 + 传感器参数表 |
| 1 | Code | 导入 numpy, pandas, matplotlib, seaborn |
| 2 | Markdown | "加载并可视化加速度计数据" |
| 3 | Code | 生成合成加速度计数据（正常 vs 偏摆），绘制时序图 |
| 4 | Markdown | "频谱分析 (FFT)" |
| 5 | Code | 使用 `scipy.fft.rfft` 对比正常/偏摆频谱 (0-10Hz) |

### 合成数据生成逻辑

```python
sample_rate = 50  # Hz
duration = 10     # 秒
t = np.arange(0, duration, 1/sample_rate)

# 正常骑行: 仅低幅值随机噪声
normal_x = np.random.randn(len(t)) * 0.05

# 偏摆骑行: 3 Hz 正弦波 + 噪声
wobble_x = 0.5 * np.sin(2 * np.pi * 3 * t) + np.random.randn(len(t)) * 0.1
```

### FFT 分析

```python
from scipy.fft import rfft, rfftfreq

def plot_spectrum(signal, sr, label, ax):
    N = len(signal)
    fft_vals = rfft(signal)
    freqs = rfftfreq(N, 1/sr)
    ax.plot(freqs[:N//10], np.abs(fft_vals[:N//10]))  # 只显示前 10% 频率
    ax.set_xlim(0, 10)  # 0-10 Hz 区间
```

---

## 数据采集计划

### 真实数据需求

| 数据类型 | 格式 | 时长/数量 | 采集场景 |
|---------|------|----------|---------|
| 正常骑行加速度计 | CSV | 50 次 × 60 秒 | 各种路况（平坦/颠簸） |
| 偏摆骑行加速度计 | CSV | 20 次 × 60 秒 | 已知偏摆故障车 |
| 正常链条音频 | WAV | 50 次 × 30 秒 | 不同速度/踏频 |
| 异常链条音频 | WAV | 20 次 × 30 秒 | 干涩链/松链 |
| 正常车头陀螺仪 | CSV | 50 次 × 30 秒 | 直线骑行 |
| 不正车头陀螺仪 | CSV | 20 次 × 30 秒 | 已知车头不正车 |

### 数据列格式

**加速度计/陀螺仪 CSV:**
```csv
timestamp,x,y,z
0.0,0.12,0.05,9.81
0.02,0.15,0.04,9.79
...
```

**音频 WAV:**
- 44100 Hz, 16-bit, 单声道

---

## 特征工程管线（规划中）

### 加速度计特征（轮胎偏摆）

```
时间域特征:
  - RMS (当前实现)
  - 峰值因子 (crest factor)
  - 过零率

频率域特征 (FFT):
  - 1-5 Hz 带内峰值频率
  - 1-5 Hz 带内能量 / 全频带能量比
  - 频谱熵 (spectral entropy)

统计特征:
  - 均值, 标准差, 偏度, 峰度
  - 四分位距 (IQR)
```

### 音频特征（链条异响）

```
帧级特征 (librosa):
  - MFCC (13维) → 每帧
  - 频谱质心 (spectral centroid)
  - 频谱带宽 (spectral bandwidth)
  - 频谱滚降 (spectral rolloff)
  - 过零率 (zero-crossing rate)

帧级统计:
  - 各特征在音频片段上的: mean, std, min, max, skew

全段特征:
  - MFCC delta (一阶差分) 和 delta-delta (二阶差分)
```

### 陀螺仪特征（车头不正）

```
统计特征 (去离群值后):
  - 均值 (当前实现)
  - 中位数
  - 截尾均值 (10%, 当前实现)

分段特征:
  - 滑动窗口均值趋势
  - 均值方差比
```

---

## 模型训练计划

### 阶段 1: 纯阈值法（✅ 当前已实现）

```
传感器 → 阈值分类 → {normal, suspect, fault}
无训练过程, 阈值人工设定
```

### 阶段 2: 经典 ML（待实现）

```
原始数据 → 特征提取 → 特征向量 → SVM/RandomForest → 类别概率
需要: 标注数据集 + sklearn Pipeline
```

**推荐流水线：**
```python
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("classifier", RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        class_weight="balanced"  # 故障样本可能较少
    )),
])

# 训练
pipeline.fit(X_train, y_train)  # y ∈ {normal, suspect, fault}

# 评估
from sklearn.metrics import classification_report
y_pred = pipeline.predict(X_test)
print(classification_report(y_test, y_pred,
      target_names=["normal", "suspect", "fault"]))

# 保存
import joblib
joblib.dump(pipeline, "ml/models/wheel_wobble_rf.joblib")
```

### 阶段 3: 深度学习（远期）

```
MFCC/频谱图 → CNN / LSTM → 分类
适用场景: 链条异响（音频时序模式）
需 GPU + 大数据集
```

---

## 模型部署

训练完成的模型通过 joblib 序列化，后端在启动时加载：

```python
# backend/app/services/fault_classifier.py (未来)
import joblib
from app.config import settings

_model = None

def get_model():
    global _model
    if _model is None:
        _model = joblib.load("ml/models/handlebar_rf.joblib")
    return _model

def classify_handlebar(gyroscope_data, ...):
    model = get_model()
    features = extract_features(gyroscope_data)  # 特征工程
    proba = model.predict_proba([features])[0]
    # ...
```

理想情况下模型加载放在 FastAPI lifespan 中：

```python
# backend/app/main.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load ML models
    load_all_models()  # 预加载到内存
    yield
    # Shutdown: cleanup
```

---

## 评估指标

| 指标 | 含义 | 目标 |
|------|------|------|
| Accuracy | 总体准确率 | > 85% |
| Recall (故障类) | 实际故障中被检出的比例 | > 90%（少漏报） |
| Precision (故障类) | 判定故障中确实为故障的比例 | > 80%（少误报） |
| F1-Score | Precision/Recall 调和平均 | > 85% |

对于安全相关的检测（偏摆可能导致摔车），Recall 优先于 Precision。
对于维护建议类检测（链条异响），两者平衡即可。

---

## 启动 Jupyter

```bash
conda activate bikeSharing
cd ml
jupyter notebook
# 浏览器自动打开 → 打开 notebooks/01_data_exploration.ipynb
```
