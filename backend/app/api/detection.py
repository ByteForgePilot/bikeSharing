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
- sensor: 传感器数据.txt (CSV with accel + gyro + GPS rows)
- audio_pcm: 音频.pcm (16-bit LE PCM)
- audio_ts: 音频_时间戳.csv (timestamp + cumulative samples)
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
    sensor_files = list(data_dir.glob("*传感器*数据*")) + list(data_dir.glob("*.txt"))
    pcm_files = list(data_dir.glob("*.pcm"))
    ts_files = list(data_dir.glob("*时间戳*")) + list(data_dir.glob("*timestamp*"))
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
        "f1_charts": _build_chart_data(accel, gyro, audio, audio_ts_list),
        "f2_charts": _build_chart_data(accel, gyro, audio, audio_ts_list),
        "f3_charts": _build_f3_charts(gyro),
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
    sensor_file = list(data_dir.glob("*传感器*数据*"))[0]
    pcm_file = list(data_dir.glob("*.pcm"))[0]
    ts_file = list(data_dir.glob("*时间戳*"))[0]
    sensor_text = sensor_file.read_text("utf-8")
    pcm_bytes = pcm_file.read_bytes()
    ts_text = ts_file.read_text("utf-8")
    accel, gyro = parse_sensor_csv(sensor_text)
    audio = parse_pcm(pcm_bytes)
    audio_ts_list = parse_audio_ts(ts_text)
    result = run_full_detection(accel, gyro, audio, audio_ts_list)
    return {
        "health": result["health"],
        "f1_charts": _build_chart_data(accel, gyro, audio, audio_ts_list),
        "f2_charts": _build_chart_data(accel, gyro, audio, audio_ts_list),
        "f3_charts": _build_f3_charts(gyro),
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
        "f1_charts": _build_chart_data(accel, gyro, audio, audio_ts_list),
        "f2_charts": _build_chart_data(accel, gyro, audio, audio_ts_list),
        "f3_charts": _build_f3_charts(gyro),
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
<h2>诊断 - 文件上传测试</h2>
<p>选择三个文件后点"测试上传"</p>
<input type="file" id="f1" accept=".txt,.csv"><br><br>
<input type="file" id="f2" accept=".pcm,.raw,.bin"><br><br>
<input type="file" id="f3" accept=".csv"><br><br>
<button onclick="test()">测试上传 FormData</button>
<button onclick="testJSON()" style="margin-left:8px">测试上传 JSON</button>
<pre id="out">等待测试...</pre>
<script>
async function test() {
  const out = document.getElementById('out');
  out.textContent = '发送中...';
  try {
    const fd = new FormData();
    fd.append('sensor', document.getElementById('f1').files[0]);
    fd.append('audio_pcm', document.getElementById('f2').files[0]);
    fd.append('audio_ts', document.getElementById('f3').files[0]);
    const r = await fetch('/api/detection/process', {method:'POST',body:fd});
    if (!r.ok) { out.textContent = 'HTTP ' + r.status + ': ' + await r.text().catch(()=>'') || ''; return; }
    const d = await r.json();
    out.textContent = '成功! 评分: ' + d.health.total_score + '\n' + JSON.stringify(d, null, 2);
  } catch(e) { out.textContent = 'ERROR: ' + e.name + ' ' + e.message + '\\n' + (e.stack || '');
  try { await fetch('/api/detection/log-upload-result', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:'error',name:e.name,message:e.message,stack:(e.stack||'').slice(0,500)})}); } catch(ex) {} }
}
async function testJSON() {
  const out = document.getElementById('out');
  function b64(b) { let s=''; new Uint8Array(b).forEach(v=>s+=String.fromCharCode(v)); return btoa(s); }
  out.textContent = '读取文件中...';
  try {
    const [sb,pb,tb] = await Promise.all([
      document.getElementById('f1').files[0].arrayBuffer(),
      document.getElementById('f2').files[0].arrayBuffer(),
      document.getElementById('f3').files[0].arrayBuffer()
    ]);
    out.textContent = '发送 JSON 中...';
    const r = await fetch('/api/detection/process-json', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({sensor:b64(sb),pcm:b64(pb),audio_ts:b64(tb)})
    });
    if (!r.ok) { out.textContent = 'HTTP ' + r.status; return; }
    const d = await r.json();
    out.textContent = '成功! 评分: ' + d.health.total_score;
  } catch(e) { out.textContent = 'ERROR: ' + e.name + ' ' + e.message + '\\n' + (e.stack || '').slice(0,500); }
}
</script>
</body>
</html>''';
    return HTMLResponse(html);
# Chart data helpers (for /api/process)
# ---------------------------------------------------------------------------
def _build_chart_data(accel, gyro, audio, audio_ts) -> dict:
    """Build minimal chart data; full charts computed on demand."""
    return {}
def _build_f3_charts(gyro) -> dict:
    return {}
