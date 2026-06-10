# 07 -- Detection Algorithm Engineering Reference

Comprehensive technical reference for the bikeSharing fault detection system (v3.0). Designed for engineers modifying or extending the algorithms.

---

## 1. Architecture & Module Map

### File Responsibilities

| File | Role | Functions Exported |
|------|------|--------------------|
| pp/ml/bike_health_detector.py | Core algorithm logic | detect_tire_wobble, detect_chain_noise, detect_handlebar_misalignment, compute_health_score, select_analysis_window, dataclasses |
| pp/services/detection_engine.py | Data format adapter | parse_sensor_csv, parse_pcm, parse_audio_ts, dicts_to_accel, dicts_to_gyro, un_full_detection, un_f1_tire_wobble, un_f2_chain_noise, un_f3_handlebar |
| pp/services/detection.py | Orchestration + DB | detect_from_files, detect_wheel_wobble (DB), detect_chain_noise (DB), detect_handlebar (DB) |
| pp/api/detection.py | HTTP endpoints | /upload, /process, /dashboard, /report |
| pp/ml/__init__.py | Re-exports | AccelSample, GyroSample, AudioChunk, all detect_* functions |

### Call Chain

`
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
`

---

## 2. Data Structures

### AccelSample

`
@dataclass
AccelSample:
  timestamp_ns: int     # Nanoseconds since epoch
  ax: float             # m/s^2
  ay: float             # m/s^2
  az: float             # m/s^2 (gravity included, ~9.81 when stationary)
`

### GyroSample

`
@dataclass
GyroSample:
  timestamp_ns: int     # Nanoseconds since epoch
  gx: float             # rad/s
  gy: float             # rad/s
  gz: float             # rad/s
`

### AudioChunk

`
@dataclass
AudioChunk:
  timestamp_ns: int              # Nanoseconds since epoch
  cumulative_samples: int        # Cumulative audio sample count at this timestamp
`

---

## 3. Utility Functions

### esample_irregular(times, values, target_fs) -> (t_new, v_new)

- Linear interpolation of irregularly-timed sensor data to uniform grid
- Used by all three detectors before spectral analysis
- **Kernel**: 
umpy.interp

### andpass_filter(data, fs, lowcut, highcut, order=4) -> ndarray

- Butterworth bandpass, applied via scipy.signal.filtfilt (zero-phase)
- Built-in clipping: lowcut/highcut clamped to [0.001, 0.999] of Nyquist
- Returns data unchanged if lowcut >= highcut

### sliding_variance(data, window, step) -> ndarray

- Vectorized sliding window variance via 
umpy.lib.stride_tricks.sliding_window_view
- **Complexity**: O(n) per window

### estimate_wheel_frequency(accel_z, fs, speed_ms=None) -> float

- FFT over Z-axis acceleration, search peak in [1.5, 8.0] Hz range
- With GPS speed: center search at  / (2*pi*0.35) with ±2 Hz margin
- Without GPS: full-range peak search

---

## 4. Adaptive Window Selection

### select_analysis_window(accel, gyro, audio, audio_ts) -> dict

For long recordings (>30s), selects the optimal 15s window with highest ride quality.

**Parameters**:

| Variable | Default | Override Env Var | Description |
|----------|---------|-----------------|-------------|
| MAX_DURATION_S | 30.0 | BIKE_MAX_DURATION_S | Threshold to trigger window selection |
| WINDOW_DURATION_S | 15.0 | BIKE_WINDOW_DURATION_S | Selected window length |
| score_fs | 50 | (hardcoded) | Resample rate for scoring grid |

**Algorithm**:
1. Compute sensor and audio duration
2. If any exceeds MAX_DURATION_S, proceed with selection
3. Resample Z-axis accel to uniform 50Hz grid
4. Slide overlapping windows (step = window_len/4)
5. Score each window: z_variance + 10 * gz_variance (lower = better)
6. Pick the lowest-score window → highest ride quality
7. Slice sensor data and audio to match the selected time range

**Edge Cases**:
- If sensor < 64 samples, return original data unchanged
- If resampled length < window_samples (15*50=750), return original
- Audio time-stamp mapping clips to nearest chunk boundaries with ±1 guard chunk

---

## 5. F1 -- Tire Wobble Detection

### detect_tire_wobble(accel, gyro=None, speed_ms=None) -> dict

**Signal Chain**:

`
Accel Z-axis (irregular 100Hz)
  -> [Remove DC] subtract mean
  -> [Resample] uniform 100Hz grid
  -> [Bandpass] Butterworth 4th-order, 2-40 Hz
  -> [Flat-road selection] sliding var < 0.5, 1s windows
  -> [FFT] normalized magnitude |A|/N*2
  -> [Peak extraction] A1 @ wheel_freq, A2 @ 2*wheel_freq
  -> [Score] P = A1 + 0.5*A2, linear interpolation
`

**Key Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| WHEEL_RADIUS | 0.35 m | Shared bike wheel radius |
| 	arget_fs | 100.0 Hz | Accelerometer resample rate |
| andpass low/high | 2.0 / 40.0 Hz | Remove low-freq drift and high-freq noise |
| lat_window_s | 1.0 s | Window for road surface quality check |
| lat_threshold | 0.5 (m/s^2)^2 | Variance below this = flat road |
| lat_min_fraction | 0.2 (20%) | Minimum flat segments to use flat-only data |
| P_healthy | 0.15 | Below this → score=100 |
| P_severe | 0.60 | Above this → score=0 |
| lat_confidence_threshold | 0.3 (30%) | If flat fraction < 30%, cap score at 75 |
| ft_margin_hz | 0.3 Hz | Frequency window for amplitude_at() |

**Score Mapping**:
`
score = 100                          if P <= 0.15
        100 * (1 - (P-0.15)/(0.45))  if 0.15 < P < 0.60
        0                             if P >= 0.60
`

**Output Dict**:
`python
{
    "score": float,          # 0-100
    "wheel_freq_hz": float,  # Estimated wheel rotation frequency
    "amplitude_f": float,    # FFT magnitude at wheel_freq
    "amplitude_2f": float,   # FFT magnitude at 2*wheel_freq
    "P_value": float,        # A1 + 0.5*A2
    "flat_fraction": float,  # Proportion of windows classified as flat road
}
`

**Modification Guide**:
- To change sensitivity: adjust P_healthy / P_severe thresholds
- To change frequency range: edit andpass_filter parameters or estimate_wheel_frequency search range
- To add GPS integration: pass speed_ms from ride GPS data
- Flat-road selection can be disabled by setting lat_threshold to a large value

---

## 6. F2 -- Chain Noise Detection

### detect_chain_noise(audio, audio_chunks, pedal_freq_hz=None) -> dict

**Signal Chain**:

`
Audio PCM (variable sample rate)
  -> [Resample] 8kHz uniform
  -> [Pedal freq estimation] autocorrelation if not provided
  -> [Bandpass] Butterworth 4th-order, 2000-4000 Hz (chain resonance band)
  -> [Hilbert envelope] analytic signal magnitude
  -> [Lowpass] 4th-order, 10 Hz (keep only pedal-frequency envelope)
  -> [Feature extraction]:
     |- Envelope spectrum SNR @ pedal_freq (with ±0.3 Hz margin)
     |- Harmonic detection (2f, 3f)
     |- Phase consistency (circular variance of peak intervals)
     |- Cepstrum periodic score (quefrency SNR @ 1/pedal_freq)
  -> [Auxiliary features]:
     |- High-frequency energy ratio (2000-4000 Hz / full band)
     |- Crest factor (peak / RMS)
  -> [Fusion] weighted anomaly score -> confidence -> final score
`

**Key Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| 	arget_fs | 8000.0 Hz | Audio resample rate |
| andpass low/high | 2000 / 4000 Hz | Chain resonance band |
| envelope_lp_cutoff | 10.0 Hz | Keep pedal-band envelope |
| snr_margin | 0.3 Hz | Spectrum search window around pedal freq |
| 
_harmonics | 3 | Number of harmonics to check (2f, 3f, 4f) |
| harmonics_noise_factor | 2.0 | Peak must be >2x noise floor to count |
| phase_consistency_min_peaks | 4 | Minimum peaks for phase analysis |
| cepstrum_snr_healthy_range | ≤2 | Cepstrum SNR: below 2 → 0 (normal) |
| cepstrum_snr_bad_range | ≥8 | Cepstrum SNR: above 8 → 1 (chain issue) |

**Feature Fusion Weights**:

`
envelope_score = 0.35*snr_score + 0.25*harm_score + 0.20*phase_score + 0.20*cepstrum_score
auxiliary_score = 0.55*hf_ratio_score + 0.45*crest_factor_score
anomaly_score = 0.60*envelope_score + 0.40*auxiliary_score
`

**Score Mapping**:
`
anomaly < 0.25 => prediction="正常", confidence=0.8 + (0.25-anomaly)*0.8
anomaly > 0.55 => prediction="异响", confidence=0.8 + (anomaly-0.55)*0.5
0.25-0.40      => prediction="正常", confidence=0.5 + (0.40-anomaly)*2.0
0.40-0.55      => prediction="异响", confidence=0.5 + (anomaly-0.40)*2.0
`

**Pedal Frequency Estimation**:
- Only used when pedal_freq_hz is not provided from F1
- Method: Hilbert envelope -> lowpass -> autocorrelation, search 0.2-1.0s delays (1-5 Hz)
- Fallback: 3.0 Hz if estimation fails

**Output Dict**:
`python
{
    "score": float,             # 0-100
    "prediction": str,          # "正常" or "异响"
    "confidence": float,        # 0.5-1.0
    "pedal_snr_db": float,      # Envelope spectrum SNR at pedal frequency
    "harmonic_ratio": float,    # Proportion of harmonics detected (0-1)
    "phase_consistency": float, # Circular variance R (0-1, 1=perfect)
    "cepstrum_score": float,    # Cepstrum periodicity (0-1)
    "hf_energy_ratio": float,   # 2-4kHz / full-band energy ratio
    "anomaly_score": float,     # Composite anomaly (0-1)
}
`

**Modification Guide**:
- **Too many false positives**: increase nomaly_score thresholds (0.25 -> 0.35, 0.55 -> 0.65)
- **Too many false negatives**: decrease thresholds
- **Chain resonance band**: the 2000-4000 Hz band is empirically chosen. Test with real chain noise recordings to verify and adjust.
- **To add new features**: extend the fusion formula in section 11, assign weights
- **Pedal freq coupling**: F1's wheel_freq_hz is reused as pedal_freq in un_full_detection -- if speeds differ, decouple these

---

## 7. F3 -- Handlebar Misalignment Detection

### detect_handlebar_misalignment(gyro) -> dict

**Signal Chain**:

`
Gyro Z-axis (irregular 50Hz)
  -> [Resample] uniform 50Hz
  -> [Window scan] 5s sliding windows, step=1.25s
  -> [Select best 30%] lowest gz_variance
  -> [Quality gate] best gz_std < 0.3 rad/s
  -> [Compute bias] mean gz across best windows
  -> [Compute yaw] cumulative sum of gz * dt
  -> [Delta theta] 0.7*|bias|*2s + 0.3*|yaw_deviation|
  -> [Score] linear interpolation 5°/15°
`

**Key Parameters**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| 	arget_fs | 50.0 Hz | Gyro resample rate |
| window_s | 5.0 s | Window length for straight-segment analysis |
| est_fraction | 0.3 (30%) | Fraction of windows to keep |
| MAX_STRAIGHT_STD | 0.3 rad/s | Quality gate: reject if best window gz_std > 0.3 |
| T_obs | 2.0 s | Observation timescale: maps gz bias to angle |
| 	heta_ok | 5.0 degrees | Below this -> score=100 |
| 	heta_bad | 15.0 degrees | Above this -> score=0 |
| yaw_weight | 0.7 | Weight for bias-derived angle in fusion |
| yaw_deviation_weight | 0.3 | Weight for cumulative yaw deviation |

**Score Mapping**:
`
score = 100                    if delta_theta <= 5°
        100 * (1 - (t-5)/10)  if 5° < delta_theta < 15°
        0                       if delta_theta >= 15°
`

**Output Dict**:
`python
{
    "score": float,             # 0-100
    "delta_theta_deg": float,  # Equivalent steering offset in degrees
    "yaw_bias_rad_s": float,   # Steady-state gyro Z bias
    "straight_segments": int,  # Number of qualified straight segments
    "warning": str,            # Present when no valid straight segments found
}
`

**Edge Cases**:
- gyro < 32 samples: return score=100 ("no data, assume healthy")
- Best segment gz_std > 0.3 rad/s: return warning, score=100 ("can't measure")
- No straight segments found (all data is turns): return warning

**Modification Guide**:
- **Sensitivity**: lower 	heta_bad to detect smaller misalignments
- **Straight segment detection**: lower MAX_STRAIGHT_STD to require straighter riding
- **Observation time**: increase T_obs to amplify small biases (risk: noise amplification)
- **Turn filtering**: if the bike is consistently ridden on curved paths, increase window_s to compensate

---

## 8. Composite Health Score

### compute_health_score(f1, f2, f3) -> dict

**Formula**:
`
H = 1 / (0.4/F1 + 0.3/F2 + 0.3/F3)     # Weighted harmonic mean
penalty = min(F1, F2, F3) / 100          # Minimum penalty factor
S = H * penalty                          # Final score 0-100
`

**Weights Rationale**:
| Component | Weight | Reasoning |
|-----------|--------|-----------|
| F1 (Tire) | 0.40 | Safety-critical, highest failure rate |
| F2 (Chain) | 0.30 | Important but rarely catastrophic |
| F3 (Handlebar) | 0.30 | Important but gradual degradation |

**Classification**:
| S range | Level | Recommendation | Color |
|---------|-------|---------------|-------|
| >= 70 | good | 推荐骑行 | Green |
| 50-69 | caution | 谨慎使用 | Yellow/Orange |
| < 50 | bad | 建议换车 | Red |

**Output Dict**:
`python
{
    "total_score": float,        # S = H * penalty
    "harmonic_mean": float,      # H value
    "penalty_factor": float,     # penalty = min / 100
    "level": str,                # "good" | "caution" | "bad"
    "recommendation": str,       # Chinese recommendation text
    "sub_scores": {
        "tire_wobble": float,     # F1 score
        "chain_noise": float,     # F2 score
        "handlebar_misalignment": float,  # F3 score
    },
    "details": {
        "F1_tire_wobble": dict,   # Full F1 output
        "F2_chain_noise": dict,   # Full F2 output
        "F3_handlebar_misalignment": dict,  # Full F3 output
    },
}
`

**Modification Guide**:
- **Change weight balance**: edit the  .4, 0.3, 0.3 fractions
- **Remove barrel effect**: set penalty = 1.0 (S = H directly)
- **Stricter penalty**: use min(F1,F2,F3)/50 to make penalty harsher
- **Change classification thresholds**: adjust the S >= 70 / S >= 50 boundaries

---

## 9. Testing & Validation

### Unit Tests

`
tests/test_detection_engine.py  # Tests all detect_* functions with synthetic data
`

**Test Data Helpers** (in conftest.py):
- _make_accel(n, freq=0): generate synthetic accel data with optional wheel-frequency vibration
- _make_gyro(n, bias=0): generate synthetic gyro data with optional yaw bias
- _make_audio(n, pedal_freq=0): generate synthetic audio with optional chain impact pattern

**Test Coverage Checklist**:
- F1: test with clean data (expect 100), severe wobble (expect 0), mixed road surfaces
- F2: test with clean chain (expect normal), chain noise (expect 异响), environmental noise (expect normal)
- F3: test with aligned handlebar (expect 100), misaligned (expect <100), turning-only data (expect warning)
- Scoring: verify composite score with known F1/F2/F3 values
- Window selection: verify with data longer than 30s, edge cases with short data

### Real Data Testing

`ash
cd E:\Project\personal\bikrsharing
python data/run_detection.py
`

Reads real sensor data from data/ directory and saves full results to data/detection_result.json.

---

## 10. Modification Checklist

When modifying the detection algorithms, verify:

- [ ] All ## ---- section headers updated in code
- [ ] Parameter values documented in this reference
- [ ] Default values and env var overrides kept in sync
- [ ] Test data regenerated for new edge cases
- [ ] detection_engine.py adapter unchanged unless API format changes
- [ ] Scoring maintains 0-100 range for compatibility
- [ ] data/run_detection.py output shape unchanged for dashboard compatibility

---

## 11. Parameter Quick Reference

All tunable parameters in one table:

| Symbol | Location | Default | Unit | Effect |
|--------|----------|---------|------|--------|
| WHEEL_RADIUS | global | 0.35 | m | Wheel freq from GPS speed |
| MAX_DURATION_S | select_analysis_window | 30 (env: BIKE_MAX_DURATION_S) | s | Window selection trigger |
| WINDOW_DURATION_S | select_analysis_window | 15 (env: BIKE_WINDOW_DURATION_S) | s | Selected window duration |
| flat_threshold | detect_tire_wobble | 0.5 | (m/s^2)^2 | Flat road variance gate |
| P_healthy | detect_tire_wobble | 0.15 | - | Below = perfect score |
| P_severe | detect_tire_wobble | 0.60 | - | Above = zero score |
| chain_bp_lo | detect_chain_noise | 2000 | Hz | Chain resonance low cut |
| chain_bp_hi | detect_chain_noise | 4000 | Hz | Chain resonance high cut |
| envelope_lp | detect_chain_noise | 10 | Hz | Envelope tracking speed |
| MAX_STRAIGHT_STD | detect_handlebar_misalignment | 0.3 | rad/s | Straight-segment quality gate |
| T_obs | detect_handlebar_misalignment | 2.0 | s | Bias-to-angle mapping |
| theta_ok | detect_handlebar_misalignment | 5.0 | deg | Below = perfect score |
| theta_bad | detect_handlebar_misalignment | 15.0 | deg | Above = zero score |
| F1_weight | compute_health_score | 0.40 | - | Tire wobble weight |
| F2_weight | compute_health_score | 0.30 | - | Chain noise weight |
| F3_weight | compute_health_score | 0.30 | - | Handlebar weight |