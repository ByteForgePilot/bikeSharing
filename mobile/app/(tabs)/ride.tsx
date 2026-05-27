import { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Animated,
  Alert,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { useAuthContext } from "../../hooks/AuthContext";
import { sensorCollector, type SensorDataPoint, type GPSDataPoint, type SensorBuffer } from "../../services/sensors";
import { audioRecorder } from "../../services/audioRecorder";
import * as api from "../../services/api";
import * as offlineStorage from "../../services/offlineStorage";
import FaultIndicator from "../../components/FaultIndicator";
import { quickWheelCheck, quickHandlebarCheck, type QuickAlert } from "../../services/onDeviceDetection";

const SAMPLE_RATE = 20;
const BACKEND_CHECK_INTERVAL_MS = 30000;

interface FaultResult {
  detected: string;
  confidence: number;
  detail: string;
}

// --- Animated sensor bar ---
function SensorBar({ label, value, maxVal = 15, unit }: { label: string; value: number; maxVal?: number; unit: string }) {
  const animWidth = useRef(new Animated.Value(0)).current;
  const clampedVal = Math.min(Math.abs(value) / maxVal, 1);

  useEffect(() => {
    Animated.spring(animWidth, {
      toValue: clampedVal,
      friction: 6,
      tension: 40,
      useNativeDriver: false,
    }).start();
  }, [value]);

  const barColor = value > maxVal * 0.7 ? "#EF4444" : value > maxVal * 0.4 ? "#F59E0B" : "#22C55E";

  return (
    <View style={sbStyles.container}>
      <View style={sbStyles.labelRow}>
        <Text style={sbStyles.label}>{label}</Text>
        <Text style={[sbStyles.value, { color: barColor }]}>{value.toFixed(2)} {unit}</Text>
      </View>
      <View style={sbStyles.track}>
        <Animated.View
          style={[sbStyles.fill, { width: animWidth.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"] }), backgroundColor: barColor }]}
        />
      </View>
    </View>
  );
}

const sbStyles = StyleSheet.create({
  container: { marginBottom: 10 },
  labelRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 4 },
  label: { fontSize: 12, color: "#64748B" },
  value: { fontSize: 12, fontWeight: "700" },
  track: { height: 6, backgroundColor: "#E2E8F0", borderRadius: 3, overflow: "hidden" },
  fill: { height: "100%", borderRadius: 3 },
});

// --- Activity ring ---
function ActivityRing({ active }: { active: boolean }) {
  const rotateAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (active) {
      const loop = Animated.loop(
        Animated.timing(rotateAnim, { toValue: 1, duration: 2000, useNativeDriver: true })
      );
      loop.start();
      return () => loop.stop();
    }
  }, [active]);

  const spin = rotateAnim.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "360deg"] });

  return (
    <View style={ringStyles.outer}>
      <Animated.View style={[ringStyles.ring, { transform: [{ rotate: spin }] }]}>
        <View style={[ringStyles.segment, { backgroundColor: "#22C55E" }]} />
        <View style={[ringStyles.segment, { backgroundColor: "#3B82F6" }]} />
        <View style={[ringStyles.segment, { backgroundColor: "#22C55E" }]} />
        <View style={[ringStyles.segment, { backgroundColor: "#3B82F6" }]} />
      </Animated.View>
      <View style={ringStyles.center} />
    </View>
  );
}

const ringStyles = StyleSheet.create({
  outer: { width: 60, height: 60, borderRadius: 30, backgroundColor: "#E2E8F0", justifyContent: "center", alignItems: "center" },
  ring: { width: 54, height: 54, borderRadius: 27, flexDirection: "row", flexWrap: "wrap", overflow: "hidden" },
  segment: { width: "50%", height: "50%" },
  center: { position: "absolute", width: 36, height: 36, borderRadius: 18, backgroundColor: "#fff" },
});

// --- Main screen ---
export default function RideScreen() {
  const { bikeId, rideId: rideIdParam } = useLocalSearchParams<{ bikeId: string; rideId: string }>();
  const rideId = rideIdParam ?? `${Date.now()}_${bikeId ?? "unknown"}`;
  const { token, online } = useAuthContext();

  const [elapsed, setElapsed] = useState(0);
  const [accelLatest, setAccelLatest] = useState<SensorDataPoint | null>(null);
  const [gyroLatest, setGyroLatest] = useState<SensorDataPoint | null>(null);
  const [gpsLatest, setGpsLatest] = useState<GPSDataPoint | null>(null);
  const [sampleCount, setSampleCount] = useState(0);
  const [audioRecording, setAudioRecording] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [ending, setEnding] = useState(false);

  const [liveAlerts, setLiveAlerts] = useState<QuickAlert[]>([]);
  const [backendChecking, setBackendChecking] = useState(false);

  const [wheelResult, setWheelResult] = useState<FaultResult | null>(null);
  const [chainResult, setChainResult] = useState<FaultResult | null>(null);
  const [handlebarResult, setHandlebarResult] = useState<FaultResult | null>(null);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const accelAll = useRef<SensorDataPoint[]>([]);
  const gyroAll = useRef<SensorDataPoint[]>([]);
  const gpsAll = useRef<GPSDataPoint[]>([]);
  const totalSamples = useRef(0);

  const handleFlush = useCallback(
    async (buffer: SensorBuffer) => {
      if (buffer.sampleCount === 0) return;
      // Always save locally first — primary data store
      try {
        await offlineStorage.saveSensorChunk(rideId, buffer.accelerometer, buffer.gyroscope, buffer.gps);
      } catch { /* local storage is non-critical during flush */ }
      // If online, also upload to server as enhancement
      if (online && token) {
        try {
          await api.uploadSensorData(
            parseInt(rideId, 10) || 0,
            buffer.accelerometer,
            buffer.gyroscope,
            buffer.gps,
            SAMPLE_RATE,
            token
          );
        } catch { /* server upload is non-critical during ride */ }
      }
    },
    [rideId, token, online]
  );

  // Stable ref so the sensor subscription never needs to restart when deps change
  const handleFlushRef = useRef(handleFlush);
  handleFlushRef.current = handleFlush;

  // Keep isRideOver accessible in the periodic-check timer callback without stale closure
  const isRideOverRef = useRef(isRideOver);
  isRideOverRef.current = isRideOver;

  // Reset all state when a new ride starts (expo-router may reuse the component)
  useEffect(() => {
    setElapsed(0);
    setAccelLatest(null);
    setGyroLatest(null);
    setGpsLatest(null);
    setSampleCount(0);
    setAudioRecording(false);
    setUploading(false);
    setEnding(false);
    setLiveAlerts([]);
    setBackendChecking(false);
    setWheelResult(null);
    setChainResult(null);
    setHandlebarResult(null);
    accelAll.current = [];
    gyroAll.current = [];
    gpsAll.current = [];
    totalSamples.current = 0;
  }, [rideId]);

  // Start sensors — restarts for each new ride (rideId change), but NOT on
  // connectivity/auth changes (online/token accessed via handleFlushRef)
  useEffect(() => {
    timerRef.current = setInterval(() => setElapsed((prev) => prev + 1), 1000);

    (async () => {
      if (await audioRecorder.isAvailable()) {
        try {
          await audioRecorder.start();
          setAudioRecording(true);
        } catch {
          setAudioRecording(false);
        }
      }
    })();

    sensorCollector.start((buffer) => {
      accelAll.current.push(...buffer.accelerometer);
      gyroAll.current.push(...buffer.gyroscope);
      gpsAll.current.push(...buffer.gps);
      totalSamples.current += buffer.sampleCount;
      setSampleCount(totalSamples.current);

      // On-device quick check
      const acc = buffer.accelerometer;
      const gyr = buffer.gyroscope;
      const wheelAlert = quickWheelCheck(acc);
      const handlebarAlert = quickHandlebarCheck(gyr);
      if (wheelAlert || handlebarAlert) {
        setLiveAlerts((prev) => {
          const next = prev.filter((a) => a.type !== (wheelAlert?.type ?? handlebarAlert?.type));
          if (wheelAlert) next.push(wheelAlert);
          if (handlebarAlert) next.push(handlebarAlert);
          return next.slice(-5);
        });
      }
      if (acc.length > 0) setAccelLatest(acc[acc.length - 1]);
      if (gyr.length > 0) setGyroLatest(gyr[gyr.length - 1]);

      setUploading(true);
      handleFlushRef.current(buffer).finally(() => setUploading(false));
    });

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      sensorCollector.stop();
      // Use instance method instead of stale closure state
      if (audioRecorder.getIsRecording()) {
        audioRecorder.stop().catch(() => {});
      }
    };
  }, [rideId]);

  // UI refresh at 20 Hz — reads per-sample values from collector for responsive display
  useEffect(() => {
    const uiTimer = setInterval(() => {
      const gps = sensorCollector.latestGPS;
      if (gps) setGpsLatest(gps);
      if (sensorCollector.latestAccel) setAccelLatest(sensorCollector.latestAccel);
      if (sensorCollector.latestGyro) setGyroLatest(sensorCollector.latestGyro);
      if (sensorCollector.eventCount > 0) setSampleCount(sensorCollector.eventCount);
    }, 50);
    return () => clearInterval(uiTimer);
  }, []);

  const isRideOver = !!(wheelResult || chainResult || handlebarResult);

  // Periodic backend detection (every 30s, online only)
  useEffect(() => {
    const checkTimer = setInterval(async () => {
      if (!online || !token || backendChecking || isRideOverRef.current) return;
      const accData = accelAll.current;
      const gyrData = gyroAll.current;
      if (accData.length < SAMPLE_RATE * 5) return; // need at least 5s of data

      setBackendChecking(true);
      const numericId = parseInt(rideId, 10) || 0;

      // Send recent 30s window for wheel wobble
      if (accData.length > 0) {
        const windowAcc = accData.slice(-Math.floor(SAMPLE_RATE * 30));
        try {
          const wr = await api.detectWheelWobble(numericId, windowAcc, SAMPLE_RATE, token);
          if (wr?.wheel_wobble && (wr.wheel_wobble.detected === "fault" || wr.wheel_wobble.detected === "suspect")) {
            setLiveAlerts((prev) => {
              const next = prev.filter((a) => a.type !== "wheel_wobble");
              next.push({ type: "wheel_wobble", level: "warning", value: wr.wheel_wobble.confidence, threshold: 0.5, timestamp: Date.now() });
              return next.slice(-5);
            });
          }
        } catch { /* ignore */ }
      }

      if (gyrData.length > 0) {
        const windowGyr = gyrData.slice(-Math.floor(SAMPLE_RATE * 30));
        try {
          const hr = await api.detectHandlebarMisalignment(numericId, windowGyr, SAMPLE_RATE, token);
          if (hr?.handlebar_misalignment && (hr.handlebar_misalignment.detected === "fault" || hr.handlebar_misalignment.detected === "suspect")) {
            setLiveAlerts((prev) => {
              const next = prev.filter((a) => a.type !== "handlebar");
              next.push({ type: "handlebar", level: "warning", value: hr.handlebar_misalignment.confidence, threshold: 0.5, timestamp: Date.now() });
              return next.slice(-5);
            });
          }
        } catch { /* ignore */ }
      }

      setBackendChecking(false);
    }, BACKEND_CHECK_INTERVAL_MS);

    return () => clearInterval(checkTimer);
  }, [online, token, backendChecking, rideId]);

  const handleEndRide = async () => {
    if (ending) return;
    setEnding(true);

    // Stop timer and sensors immediately
    if (timerRef.current) clearInterval(timerRef.current);
    const finalBuffer = sensorCollector.stop();
    // stop() already flushed via onFlush → accelAll/gyroAll/gpsAll refs are current
    setSampleCount(totalSamples.current);

    const accelData = accelAll.current;
    const gyroData = gyroAll.current;
    const gpsData = gpsAll.current;
    const endLat = gpsData.length > 0 ? gpsData[gpsData.length - 1].lat : 0;
    const endLng = gpsData.length > 0 ? gpsData[gpsData.length - 1].lng : 0;

    try {
      // Stop audio (safe — uses instance state, not React state)
      let audioFileUri: string | null = null;
      try {
        if (audioRecorder.getIsRecording()) {
          audioFileUri = await audioRecorder.stop();
          setAudioRecording(false);
        }
      } catch { /* audio stop failure is non-critical */ }

      // === Always persist locally as primary store ===
      try {
        await offlineStorage.finishRide(rideId, accelData, gyroData, gpsData, SAMPLE_RATE);
        if (audioFileUri) {
          await offlineStorage.saveAudioUri(rideId, audioFileUri).catch(() => {});
        }
      } catch { /* local save failure */ }

      // === If online, also try server-side detection ===
      let gotServerResult = false;
      if (online && token) {
        const numericId = parseInt(rideId, 10) || 0;

        try { await api.endRide(numericId, endLat, endLng, token); } catch { /* ignore */ }

        if (accelData.length > 0) {
          try {
            const wr = await api.detectWheelWobble(numericId, accelData, SAMPLE_RATE, token);
            if (wr?.wheel_wobble) { setWheelResult(wr.wheel_wobble); gotServerResult = true; }
          } catch { /* ignore */ }

          let chainDetected = false;
          if (audioFileUri) {
            try {
              const cr = await api.uploadAudioFile(numericId, audioFileUri, token);
              if (cr?.chain_noise) { setChainResult(cr.chain_noise); chainDetected = true; gotServerResult = true; }
            } catch { /* fall through */ }
          }
          if (!chainDetected) {
            try {
              const features = accelData.map((d) => Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z));
              const cr = await api.detectChainNoise(numericId, features, token);
              if (cr?.chain_noise) { setChainResult(cr.chain_noise); gotServerResult = true; }
            } catch { /* ignore */ }
          }
        }
        if (gyroData.length > 0) {
          try {
            const hr = await api.detectHandlebarMisalignment(numericId, gyroData, SAMPLE_RATE, token);
            if (hr?.handlebar_misalignment) { setHandlebarResult(hr.handlebar_misalignment); gotServerResult = true; }
          } catch { /* ignore */ }
        }
      }

      // Fallback result when server detection didn't produce anything
      if (!gotServerResult) {
        setWheelResult({
          detected: "unknown",
          confidence: 0,
          detail: `已保存 ${accelData.length} 个加速度样本、${gyroData.length} 个陀螺仪样本、${gpsData.length} 个 GPS 点`,
        });
      }
    } finally {
      setEnding(false);
    }
  };

  const handleGoBack = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    sensorCollector.stop();
    if (audioRecorder.getIsRecording()) {
      audioRecorder.stop().catch(() => {});
    }
    router.replace("/");
  };

  const handleCancelRide = () => {
    Alert.alert(
      "取消骑行",
      "确定要取消吗？已采集的传感器数据将丢失。",
      [
        { text: "继续骑行", style: "cancel" },
        {
          text: "确定取消",
          style: "destructive",
          onPress: async () => {
            if (timerRef.current) clearInterval(timerRef.current);
            sensorCollector.stop();
            if (audioRecorder.getIsRecording()) {
              audioRecorder.stop().catch(() => {});
            }
            try { await offlineStorage.deleteRide(rideId); } catch { /* ignore */ }
            router.replace("/");
          },
        },
      ]
    );
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const isSensing = !isRideOver && sampleCount > 0;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Timer + Status Header */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <View>
            <Text style={styles.bikeLabel}>当前车辆</Text>
            <Text style={styles.bikeValue}>{bikeId}</Text>
          </View>
          <ActivityRing active={isSensing} />
        </View>
        <Text style={styles.timer}>{formatTime(elapsed)}</Text>
        <View style={styles.statusRow}>
          <View style={[styles.statusDot, { backgroundColor: uploading ? "#FBBF24" : isRideOver ? "#22C55E" : "#3B82F6" }]} />
          <Text style={styles.statusLabel}>
            {uploading ? "保存中" : isRideOver ? "检测完成" : online ? "采集中 · 在线" : "采集中 · 离线"}
          </Text>
          <Text style={styles.sampleBadge}>{sampleCount} 样本</Text>
        </View>
      </View>

      {/* GPS status — always visible */}
      <View style={styles.gpsBar}>
        <Text style={styles.gpsIcon}>📍</Text>
        {gpsLatest ? (
          <>
            <Text style={styles.gpsText}>
              {gpsLatest.lat.toFixed(5)}, {gpsLatest.lng.toFixed(5)}
            </Text>
            {gpsLatest.accuracy != null && (
              <Text style={styles.gpsAcc}>±{gpsLatest.accuracy.toFixed(1)}m</Text>
            )}
          </>
        ) : (
          <Text style={styles.gpsWaiting}>
            {sensorCollector.currentGPSStatus === "denied"
              ? "GPS 权限被拒绝"
              : "等待 GPS 信号..."}
          </Text>
        )}
      </View>

      {/* Live sensor visualization */}
      <View style={styles.card}>
        <View style={styles.cardTitleRow}>
          <Text style={styles.cardTitleIcon}>📊</Text>
          <Text style={styles.cardTitle}>实时传感器数据</Text>
        </View>

        <Text style={styles.sectionLabel}>加速度计 (m/s²)</Text>
        <SensorBar label="X 轴" value={accelLatest?.x ?? 0} maxVal={15} unit="m/s²" />
        <SensorBar label="Y 轴" value={accelLatest?.y ?? 0} maxVal={15} unit="m/s²" />
        <SensorBar label="Z 轴" value={accelLatest?.z ?? 0} maxVal={15} unit="m/s²" />

        <View style={styles.divider} />

        <Text style={styles.sectionLabel}>陀螺仪 (rad/s)</Text>
        <SensorBar label="X 轴" value={gyroLatest?.x ?? 0} maxVal={9} unit="rad/s" />
        <SensorBar label="Y 轴" value={gyroLatest?.y ?? 0} maxVal={9} unit="rad/s" />
        <SensorBar label="Z 轴" value={gyroLatest?.z ?? 0} maxVal={9} unit="rad/s" />

        {!isSensing && !isRideOver && (
          <Text style={styles.waitingHint}>等待传感器数据...</Text>
        )}
      </View>

      {/* Live alerts */}
      {liveAlerts.length > 0 && (
        <View style={styles.card}>
          <View style={styles.cardTitleRow}>
            <Text style={styles.cardTitleIcon}>⚡</Text>
            <Text style={styles.cardTitle}>实时预警</Text>
          </View>
          {liveAlerts.map((alert, idx) => (
            <View key={idx} style={alertStyles.row}>
              <Text style={alertStyles.type}>
                {alert.type === "wheel_wobble" ? "🛞 轮胎偏摆" : alert.type === "chain_noise" ? "🔗 链条异响" : "🔧 车头不正"}
              </Text>
              <Text style={alertStyles.detail}>⚠️ 注意 ({alert.value.toFixed(2)})</Text>
            </View>
          ))}
        </View>
      )}

      {/* Fault detection results */}
      <View style={styles.card}>
        <View style={styles.cardTitleRow}>
          <Text style={styles.cardTitleIcon}>🔬</Text>
          <Text style={styles.cardTitle}>故障检测结果</Text>
        </View>
        {isRideOver ? (
          online ? (
            <FaultIndicator wheel={wheelResult} chain={chainResult} handlebar={handlebarResult} />
          ) : (
            <View style={styles.resultBox}>
              <Text style={styles.resultTitle}>✅ 数据已保存到本地</Text>
              <Text style={styles.resultDetail}>{wheelResult?.detail}</Text>
              <Text style={styles.resultHint}>连接服务器后可上传并获取检测结果</Text>
            </View>
          )
        ) : ending ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator size="small" color="#2563EB" />
            <Text style={styles.loadingText}>{online ? "正在云端分析检测..." : "正在保存数据..."}</Text>
          </View>
        ) : (
          <View style={styles.idleRow}>
            <Text style={styles.idleIcon}>⏳</Text>
            <Text style={styles.idleText}>
              {online ? "结束骑行后自动进行云端检测" : "结束骑行后数据将保存到本地文件"}
            </Text>
          </View>
        )}
      </View>

      {/* Action buttons */}
      {!isRideOver ? (
        <>
          <TouchableOpacity
            style={[styles.endBtn, ending && { opacity: 0.6 }]}
            onPress={handleEndRide}
            disabled={ending}
            activeOpacity={0.8}
          >
            <Text style={styles.endBtnIcon}>🛑</Text>
            <Text style={styles.endBtnText}>{ending ? (online ? "检测中..." : "保存中...") : "结束骑行"}</Text>
          </TouchableOpacity>
          {!ending && (
            <TouchableOpacity style={styles.cancelBtn} onPress={handleCancelRide} activeOpacity={0.7}>
              <Text style={styles.cancelBtnText}>取消骑行</Text>
            </TouchableOpacity>
          )}
        </>
      ) : (
        <TouchableOpacity style={styles.backBtn} onPress={handleGoBack} activeOpacity={0.8}>
          <Text style={styles.backBtnText}>← 返回首页</Text>
        </TouchableOpacity>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAFC" },
  content: { padding: 20, paddingBottom: 40 },

  header: { backgroundColor: "#1E293B", borderRadius: 20, padding: 24, marginBottom: 12 },
  headerTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  bikeLabel: { fontSize: 12, color: "#94A3B8" },
  bikeValue: { fontSize: 22, fontWeight: "700", color: "#fff", marginTop: 2 },
  timer: { fontSize: 48, fontWeight: "800", color: "#fff", fontVariant: ["tabular-nums"], letterSpacing: 2, marginBottom: 12 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusLabel: { fontSize: 13, color: "#CBD5E1", flex: 1 },
  sampleBadge: { fontSize: 11, color: "#64748B", backgroundColor: "#334155", paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },

  gpsBar: { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#fff", borderRadius: 14, paddingVertical: 10, paddingHorizontal: 16, marginBottom: 16, shadowColor: "#000", shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 4, elevation: 1 },
  gpsIcon: { fontSize: 16 },
  gpsText: { fontSize: 13, fontWeight: "600", color: "#334155", fontVariant: ["tabular-nums"], flex: 1 },
  gpsAcc: { fontSize: 11, color: "#94A3B8" },
  gpsWaiting: { fontSize: 13, color: "#94A3B8", fontStyle: "italic", flex: 1 },

  card: { backgroundColor: "#fff", borderRadius: 20, padding: 20, marginBottom: 16, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  cardTitleRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 16 },
  cardTitleIcon: { fontSize: 18 },
  cardTitle: { fontSize: 17, fontWeight: "700", color: "#1E293B" },
  sectionLabel: { fontSize: 12, fontWeight: "600", color: "#94A3B8", marginBottom: 8, marginTop: 4, textTransform: "uppercase", letterSpacing: 1 },
  divider: { height: 1, backgroundColor: "#F1F5F9", marginVertical: 12 },

  waitingHint: { textAlign: "center", color: "#94A3B8", fontSize: 13, marginTop: 8, fontStyle: "italic" },

  loadingRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 16 },
  loadingText: { fontSize: 14, color: "#64748B" },
  idleRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 12 },
  idleIcon: { fontSize: 20 },
  idleText: { fontSize: 13, color: "#94A3B8", flex: 1, lineHeight: 20 },
  resultBox: { paddingVertical: 12 },
  resultTitle: { fontSize: 16, fontWeight: "700", color: "#059669", marginBottom: 6 },
  resultDetail: { fontSize: 13, color: "#475569", marginBottom: 4, lineHeight: 20 },
  resultHint: { fontSize: 12, color: "#94A3B8", marginTop: 4 },

  endBtn: { backgroundColor: "#EF4444", borderRadius: 18, paddingVertical: 18, flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 8, shadowColor: "#EF4444", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  endBtnIcon: { fontSize: 20 },
  endBtnText: { fontSize: 18, fontWeight: "700", color: "#fff" },
  cancelBtn: { marginTop: 12, paddingVertical: 12, alignItems: "center" },
  cancelBtnText: { fontSize: 14, color: "#94A3B8", fontWeight: "600" },
  backBtn: { backgroundColor: "#2563EB", borderRadius: 18, paddingVertical: 18, alignItems: "center", shadowColor: "#2563EB", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  backBtnText: { fontSize: 18, fontWeight: "700", color: "#fff" },
});

const alertStyles = StyleSheet.create({
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 6, paddingHorizontal: 4 },
  type: { fontSize: 14, fontWeight: "600", color: "#1E293B" },
  detail: { fontSize: 13, fontWeight: "700", color: "#D97706" },
});
