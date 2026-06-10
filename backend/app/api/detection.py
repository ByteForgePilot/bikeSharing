from fastapi import APIRouter, Depends, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, Undefined
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas import (
    WheelWobbleRequest,
    HandlebarRequest,
    ChainNoiseRequest,
)
from app.services import detection as detection_service
router = APIRouter()
# Jinja2 templates (for dashboard)
env = Environment(loader=FileSystemLoader("app/templates"), auto_reload=True, undefined=Undefined)
# ---------------------------------------------------------------------------
# Individual detection endpoints (real-time, per-sensor)
# ---------------------------------------------------------------------------
@router.post(
    "/wheel-wobble/{ride_id}",
    summary="Tire wobble detection",
    description="Analyze accelerometer data using FFT + wheel-frequency analysis.",
)
async def detect_wheel_wobble(
    ride_id: int,
    body: WheelWobbleRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = [d.model_dump() for d in body.accelerometer_data]
    result = await detection_service.detect_wheel_wobble(db, ride_id, data, body.sample_rate)
    return {"ride_id": ride_id, "wheel_wobble": result}
@router.post(
    "/chain-noise/{ride_id}",
    summary="Chain noise detection",
    description="Analyze audio features using envelope spectrum analysis.",
)
async def detect_chain_noise(
    ride_id: int,
    body: ChainNoiseRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import numpy as np
    audio = np.array(body.audio_features, dtype=np.float32)
    result = await detection_service.detect_chain_noise(db, ride_id, audio)
    return {"ride_id": ride_id, "chain_noise": result}
@router.post(
    "/handlebar/{ride_id}",
    summary="Handlebar misalignment detection",
    description="Analyze gyroscope data for handlebar offset.",
)
async def detect_handlebar_misalignment(
    ride_id: int,
    body: HandlebarRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = [d.model_dump() for d in body.gyroscope_data]
    result = await detection_service.detect_handlebar(db, ride_id, data, body.sample_rate)
    return {"ride_id": ride_id, "handlebar_misalignment": result}
# ---------------------------------------------------------------------------
# File upload full detection (BicycleDataLogger output)
# ---------------------------------------------------------------------------
@router.post(
    "/upload/{ride_id}",
    summary="Upload BicycleDataLogger files for full detection",
    description="""Upload the three files produced by BicycleDataLogger:
- sensor: 浼犳劅鍣ㄦ暟鎹?txt (CSV with accel + gyro + GPS rows)
- audio_pcm: 闊抽.pcm (16-bit LE PCM)
- audio_ts: 闊抽_鏃堕棿鎴?csv (timestamp + cumulative samples)
Runs all three detections + composite health scoring.""",
)
async def upload_detection_files(
    ride_id: int,
    sensor: UploadFile = File(...),
    audio_pcm: UploadFile = File(...),
    audio_ts: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sensor_text = (await sensor.read()).decode("utf-8")
    pcm_bytes = await audio_pcm.read()
    ts_text = (await audio_ts.read()).decode("utf-8")
    result = await detection_service.detect_from_files(
        db, ride_id, sensor_text, pcm_bytes, ts_text
    )
    return result
# ---------------------------------------------------------------------------
# Web dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Standalone dashboard: run detection on real data and render."""
    import json
    from pathlib import Path
    from types import SimpleNamespace
    from app.services.detection_engine import (
        parse_sensor_csv, parse_pcm, parse_audio_ts, run_full_detection,
    )
    data_dir = Path(__file__).resolve().parents[3] / "data"
    sensor_files = list(data_dir.glob("*浼犳劅鍣?鏁版嵁*")) + list(data_dir.glob("*.txt"))
    pcm_files = list(data_dir.glob("*.pcm"))
    ts_files = list(data_dir.glob("*鏃堕棿鎴?")) + list(data_dir.glob("*timestamp*"))
    if sensor_files and pcm_files and ts_files:
        sensor_text = sensor_files[0].read_text("utf-8")
        pcm_bytes = pcm_files[0].read_bytes()
        ts_text = ts_files[0].read_text("utf-8")
        accel, gyro = parse_sensor_csv(sensor_text)
        audio = parse_pcm(pcm_bytes)
        audio_ts = parse_audio_ts(ts_text)
        result = run_full_detection(accel, gyro, audio, audio_ts)
    else:
        result = {"health":{"total_score":0,"level":"unknown","recommendation":"No data files found"}}
    # Map to template format: health + f1_charts/f2_charts/f3_charts
    tmpl_data = {
        "health": result["health"],
        "sub_scores": result["health"].get("sub_scores", {}),
        "f1_result": result.get("f1", {}),
        "f2_result": result.get("f2", {}),
        "f3_result": result.get("f3", {}),
        "data_summary": result.get("data_summary", {}),
        "f1_charts": {},
        "f2_charts": {},
        "f3_charts": {},
    }
    def to_ns(d):
        if isinstance(d, dict):
            return SimpleNamespace(**{k: to_ns(v) for k, v in d.items()})
        return d
    template = env.get_template("index.html")
    return HTMLResponse(template.render(request=request, result=to_ns(tmpl_data), raw=tmpl_data))
# API-compatible process endpoint (mirrors algorithm-branch Flask API)
@router.post("/process")
async def api_process(
    sensor: UploadFile = File(...),
    audio_pcm: UploadFile = File(...),
    audio_ts: UploadFile = File(...),
):
    """File-upload detection without ride_id (standalone, no auth required)."""
    sensor_text = (await sensor.read()).decode("utf-8")
    pcm_bytes = await audio_pcm.read()
    ts_text = (await audio_ts.read()).decode("utf-8")
    from app.services.detection_engine import (
        parse_sensor_csv,
        parse_pcm,
        parse_audio_ts,
        run_full_detection,
    )
    accel, gyro = parse_sensor_csv(sensor_text)
    audio = parse_pcm(pcm_bytes)
    audio_ts_list = parse_audio_ts(ts_text)
    result = run_full_detection(accel, gyro, audio, audio_ts_list)
    return {
        "health": result["health"],
        "f1_charts": _build_f1_chart(accel),
        "f2_charts": _build_f2_chart(audio),
        "f3_charts": _build_f3_chart(gyro),
        "data_summary": result["data_summary"],
    }

@router.post("/process-test")
async def api_process_test():
    """Process test data files from data/ directory."""
    from pathlib import Path
    from app.services.detection_engine import (
        parse_sensor_csv, parse_pcm, parse_audio_ts, run_full_detection,
    )
    data_dir = Path(__file__).resolve().parents[3] / "data"
    sensor_file = list(data_dir.glob("*浼犳劅鍣?鏁版嵁*"))[0]
    pcm_file = list(data_dir.glob("*.pcm"))[0]
    ts_file = list(data_dir.glob("*鏃堕棿鎴?"))[0]
    sensor_text = sensor_file.read_text("utf-8")
    pcm_bytes = pcm_file.read_bytes()
    ts_text = ts_file.read_text("utf-8")
    accel, gyro = parse_sensor_csv(sensor_text)
    audio = parse_pcm(pcm_bytes)
    audio_ts_list = parse_audio_ts(ts_text)
    result = run_full_detection(accel, gyro, audio, audio_ts_list)
    return {
        "health": result["health"],
        "f1_charts": _build_f1_chart(accel),
        "f2_charts": _build_f2_chart(audio),
        "f3_charts": _build_f3_chart(gyro),
        "data_summary": result["data_summary"],
    }
# ---------------------------------------------------------------------------
# Report query
# ---------------------------------------------------------------------------
@router.get(
    "/report/{ride_id}",
    summary="Get detection report",
    description="Get the comprehensive detection report for a ride.",
)
async def get_detection_report(
    ride_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await detection_service.get_detection_report(db, ride_id)
@router.get(
    "/health-score/{ride_id}",
    summary="Get health score",
    description="Get the composite health score (0-100) for a ride.",
)
async def get_health_score(
    ride_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    report = await detection_service.get_detection_report(db, ride_id)
    return report
# ---------------------------------------------------------------------------
# 


@router.post("/process-json")
async def api_process_json(body: dict):
    import base64
    from app.services.detection_engine import (
        parse_sensor_csv, parse_pcm, parse_audio_ts, run_full_detection,
    )
    sensor_text = base64.b64decode(body["sensor"]).decode("utf-8")
    pcm_bytes = base64.b64decode(body["pcm"])
    ts_text = base64.b64decode(body["audio_ts"]).decode("utf-8")
    accel, gyro = parse_sensor_csv(sensor_text)
    audio = parse_pcm(pcm_bytes)
    audio_ts_list = parse_audio_ts(ts_text)
    result = run_full_detection(accel, gyro, audio, audio_ts_list)
    return {
        "health": result["health"],
        "f1_charts": _build_f1_chart(accel),
        "f2_charts": _build_f2_chart(audio),
        "f3_charts": _build_f3_chart(gyro),
        "data_summary": result["data_summary"],
    }




@router.post("/log-upload-result")
async def log_upload_result(body: dict):
    """Log upload diagnostic result."""
    import os, json as jm
    path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "diagnostic_result.log")
    with open(path, "w", encoding="utf-8") as f:
        jm.dump(body, f, ensure_ascii=False, indent=2)
    return {"status": "ok"}

@router.get("/diag-upload")
async def diag_upload_page():
    """Diagnostic page for testing file uploads."""
    from fastapi.responses import HTMLResponse
    html = '''<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Upload Test</title>
<style>body{background:#111;color:#d4e4f0;font-family:sans-serif;padding:20px}button{padding:10px 24px;font-size:14px;cursor:pointer;background:#448aff;color:#fff;border:none;border-radius:8px}pre{background:#1a2736;padding:12px;border-radius:8px;margin-top:12px;white-space:pre-wrap}</style></head>
<body>
<h2>璇婃柇 - 鏂囦欢涓婁紶娴嬭瘯</h2>
<p>閫夋嫨涓変釜鏂囦欢鍚庣偣"娴嬭瘯涓婁紶"</p>
<input type="file" id="f1" accept=".txt,.csv"><br><br>
<input type="file" id="f2" accept=".pcm,.raw,.bin"><br><br>
<input type="file" id="f3" accept=".csv"><br><br>
<button onclick="test()">娴嬭瘯涓婁紶 FormData</button>
<button onclick="testJSON()" style="margin-left:8px">娴嬭瘯涓婁紶 JSON</button>
<pre id="out">绛夊緟娴嬭瘯...</pre>
<script>
async function test() {
  const out = document.getElementById('out');
  out.textContent = '鍙戦€佷腑...';
  try {
    const fd = new FormData();
    fd.append('sensor', document.getElementById('f1').files[0]);
    fd.append('audio_pcm', document.getElementById('f2').files[0]);
    fd.append('audio_ts', document.getElementById('f3').files[0]);
    const r = await fetch('/api/detection/process', {method:'POST',body:fd});
    if (!r.ok) { out.textContent = 'HTTP ' + r.status + ': ' + await r.text().catch(()=>'') || ''; return; }
    const d = await r.json();
    out.textContent = '鎴愬姛! 璇勫垎: ' + d.health.total_score + '\n' + JSON.stringify(d, null, 2);
  } catch(e) { out.textContent = 'ERROR: ' + e.name + ' ' + e.message + '\\n' + (e.stack || '');
  try { await fetch('/api/detection/log-upload-result', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'error',name:e.name,message:e.message,stack:(e.stack||'').slice(0,500)})}); } catch(ex) {} }
}
async function testJSON() {
  const out = document.getElementById('out');
  function b64(b) { let s=''; new Uint8Array(b).forEach(v=>s+=String.fromCharCode(v)); return btoa(s); }
  out.textContent = '璇诲彇鏂囦欢涓?..';
  try {
    const [sb,pb,tb] = await Promise.all([
      document.getElementById('f1').files[0].arrayBuffer(),
      document.getElementById('f2').files[0].arrayBuffer(),
      document.getElementById('f3').files[0].arrayBuffer()
    ]);
    out.textContent = '鍙戦€?JSON 涓?..';
    const r = await fetch('/api/detection/process-json', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({sensor:b64(sb),pcm:b64(pb),audio_ts:b64(tb)})
    });
    if (!r.ok) { out.textContent = 'HTTP ' + r.status; return; }
    const d = await r.json();
    out.textContent = '鎴愬姛! 璇勫垎: ' + d.health.total_score;
  } catch(e) { out.textContent = 'ERROR: ' + e.name + ' ' + e.message + '\\n' + (e.stack || '').slice(0,500); }
}
</script>
</body>
</html>''';
    return HTMLResponse(html);
# Chart data helpers (for /api/process)
# ---------------------------------------------------------------------------
def _build_f1_chart(accel: list) -> dict:
    """Build F1 chart data from accelerometer readings."""
    import numpy as np
    if not accel:
        return {}
    t0 = accel[0].timestamp_ns
    times = [(s.timestamp_ns - t0) / 1e9 for s in accel]
    az = [s.az for s in accel]
    n = len(az)
    if n < 4:
        return {"waveform": {"times": times, "az_filtered": az}, "fft": {"freqs": [], "magnitude": []}}
    dt = (times[-1] - times[0]) / max(n - 1, 1)
    fft_vals = np.fft.rfft(az)
    fft_freqs = np.fft.rfftfreq(n, d=dt).tolist()
    fft_mag = (np.abs(fft_vals) / n).tolist()
    return {
        "waveform": {"times": times, "az_filtered": az},
        "fft": {"freqs": fft_freqs, "magnitude": fft_mag},
    }

def _build_f2_chart(audio: np.ndarray) -> dict:
    """Build F2 chart data from audio PCM samples."""
    import numpy as np
    if audio is None or len(audio) == 0:
        return {}
    sr = 8000.0
    max_len = min(len(audio), 10000)
    times = [i / sr for i in range(max_len)]
    amp = audio[:max_len].tolist()
    window = audio[:min(len(audio), 8192)]
    n = len(window)
    if n < 4:
        return {"waveform": {"times": times, "amplitude": amp}, "fft": {"freqs": [], "magnitude": []}}
    fft_vals = np.fft.rfft(window)
    fft_freqs = (np.fft.rfftfreq(n, d=1.0/sr) * (sr / 2)).tolist() if n > 0 else []
    fft_mag = (np.abs(fft_vals) / n).tolist()
    return {
        "waveform": {"times": times, "amplitude": amp},
        "fft": {"freqs": fft_freqs, "magnitude": fft_mag},
    }

def _build_f3_chart(gyro: list) -> dict:
    """Build F3 chart data from gyroscope readings."""
    import numpy as np
    if not gyro:
        return {}
    t0 = gyro[0].timestamp_ns
    times = [(s.timestamp_ns - t0) / 1e9 for s in gyro]
    gx = [s.gx for s in gyro]
    gy_arr = [s.gy for s in gyro]
    gz = [s.gz for s in gyro]
    n = len(gz)
    if n < 2:
        return {"gyro": {"times": times, "gx": gx, "gy": gy_arr, "gz": gz}, "yaw_angle": {"times": [], "angle_deg": []}}
    dt = (times[-1] - times[0]) / max(n - 1, 1)
    yaw_rad = np.cumsum(gz) * dt
    yaw_deg = (yaw_rad - yaw_rad[0]) * 180.0 / np.pi
    return {
        "gyro": {"times": times, "gx": gx, "gy": gy_arr, "gz": gz},
        "yaw_angle": {"times": times, "angle_deg": yaw_deg.tolist()},
    }
