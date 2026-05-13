import { useState, useEffect, useRef, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  ActivityIndicator,
  Animated,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { useAuthContext } from "../../hooks/AuthContext";
import { sensorCollector, type SensorDataPoint, type SensorBuffer } from "../../services/sensors";
import * as api from "../../services/api";
import * as offlineStorage from "../../services/offlineStorage";
import FaultIndicator from "../../components/FaultIndicator";

const SAMPLE_RATE = 20;

interface FaultResult {
  detected: string;
  confidence: number;
  detail: string;
}

// Animated sensor bar component
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

// Animated circular gauge for overall activity
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

export default function RideScreen() {
  const { bikeId, rideId: rideIdParam } = useLocalSearchParams<{ bikeId: string; rideId: string }>();
  const rideId = rideIdParam ?? `${Date.now()}_${"unknown"}`;
  const { token, online } = useAuthContext();

  const [elapsed, setElapsed] = useState(0);
  const [accelLatest, setAccelLatest] = useState<SensorDataPoint | null>(null);
  const [gyroLatest, setGyroLatest] = useState<SensorDataPoint | null>(null);
  const [sampleCount, setSampleCount] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [ending, setEnding] = useState(false);

  const [wheelResult, setWheelResult] = useState<FaultResult | null>(null);
  const [chainResult, setChainResult] = useState<FaultResult | null>(null);
  const [handlebarResult, setHandlebarResult] = useState<FaultResult | null>(null);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const accelAll = useRef<SensorDataPoint[]>([]);
  const gyroAll = useRef<SensorDataPoint[]>([]);
  const totalSamples = useRef(0);

  const handleFlush = useCallback(
    async (buffer: SensorBuffer) => {
      if (buffer.sampleCount === 0) return;
      if (online && token) {
        try {
          await api.uploadSensorData(parseInt(rideId, 10) || 0, buffer.accelerometer, buffer.gyroscope, SAMPLE_RATE, token);
        } catch { /* 非关键错误 */ }
      } else {
        await offlineStorage.saveSensorChunk(rideId, buffer.accelerometer, buffer.gyroscope);
      }
    },
    [rideId, token, online]
  );

  useEffect(() => {
    timerRef.current = setInterval(() => setElapsed((prev) => prev + 1), 1000);

    sensorCollector.start((buffer) => {
      accelAll.current.push(...buffer.accelerometer);
      gyroAll.current.push(...buffer.gyroscope);
      totalSamples.current += buffer.sampleCount;
      setSampleCount(totalSamples.current);

      const acc = buffer.accelerometer;
      const gyr = buffer.gyroscope;
      if (acc.length > 0) setAccelLatest(acc[acc.length - 1]);
      if (gyr.length > 0) setGyroLatest(gyr[gyr.length - 1]);

      setUploading(true);
      handleFlush(buffer).finally(() => setUploading(false));
    });

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      sensorCollector.stop();
    };
  }, [handleFlush]);

  const handleEndRide = async () => {
    if (ending) return;
    setEnding(true);

    if (timerRef.current) clearInterval(timerRef.current);
    const finalBuffer = sensorCollector.stop();

    if (finalBuffer.sampleCount > 0) {
      accelAll.current.push(...finalBuffer.accelerometer);
      gyroAll.current.push(...finalBuffer.gyroscope);
      totalSamples.current += finalBuffer.sampleCount;
      setSampleCount(totalSamples.current);
      await handleFlush(finalBuffer);
    }

    const accelData = accelAll.current;
    const gyroData = gyroAll.current;

    if (online && token) {
      try {
        const numericId = parseInt(rideId, 10) || 0;
        await api.endRide(numericId, 0, 0, token);
      } catch { /* ignore */ }

      if (accelData.length > 0) {
        try {
          const wr = await api.detectWheelWobble(parseInt(rideId, 10) || 0, accelData, SAMPLE_RATE, token);
          if (wr?.wheel_wobble) setWheelResult(wr.wheel_wobble);
        } catch { /* ignore */ }
        try {
          const features = accelData.map((d) => Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z));
          const cr = await api.detectChainNoise(parseInt(rideId, 10) || 0, features, token);
          if (cr?.chain_noise) setChainResult(cr.chain_noise);
        } catch { /* ignore */ }
      }
      if (gyroData.length > 0) {
        try {
          const hr = await api.detectHandlebarMisalignment(parseInt(rideId, 10) || 0, gyroData, SAMPLE_RATE, token);
          if (hr?.handlebar_misalignment) setHandlebarResult(hr.handlebar_misalignment);
        } catch { /* ignore */ }
      }
    } else {
      await offlineStorage.finishRide(rideId, accelData, gyroData, SAMPLE_RATE);
      setWheelResult({ detected: "unknown", confidence: 0, detail: `已保存 ${accelData.length} 个加速度样本、${gyroData.length} 个陀螺仪样本` });
    }

    setEnding(false);
  };

  const handleGoBack = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    sensorCollector.stop();
    router.back();
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const isRideOver = wheelResult || chainResult || handlebarResult;
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

      {/* Action button */}
      {!isRideOver ? (
        <TouchableOpacity
          style={[styles.endBtn, ending && { opacity: 0.6 }]}
          onPress={handleEndRide}
          disabled={ending}
          activeOpacity={0.8}
        >
          <Text style={styles.endBtnIcon}>🛑</Text>
          <Text style={styles.endBtnText}>{ending ? (online ? "检测中..." : "保存中...") : "结束骑行"}</Text>
        </TouchableOpacity>
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

  // Header
  header: { backgroundColor: "#1E293B", borderRadius: 20, padding: 24, marginBottom: 20 },
  headerTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  bikeLabel: { fontSize: 12, color: "#94A3B8" },
  bikeValue: { fontSize: 22, fontWeight: "700", color: "#fff", marginTop: 2 },
  timer: { fontSize: 48, fontWeight: "800", color: "#fff", fontVariant: ["tabular-nums"], letterSpacing: 2, marginBottom: 12 },
  statusRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusLabel: { fontSize: 13, color: "#CBD5E1", flex: 1 },
  sampleBadge: { fontSize: 11, color: "#64748B", backgroundColor: "#334155", paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },

  // Cards
  card: { backgroundColor: "#fff", borderRadius: 20, padding: 20, marginBottom: 16, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  cardTitleRow: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 16 },
  cardTitleIcon: { fontSize: 18 },
  cardTitle: { fontSize: 17, fontWeight: "700", color: "#1E293B" },
  sectionLabel: { fontSize: 12, fontWeight: "600", color: "#94A3B8", marginBottom: 8, marginTop: 4, textTransform: "uppercase", letterSpacing: 1 },
  divider: { height: 1, backgroundColor: "#F1F5F9", marginVertical: 12 },

  // Sensor
  waitingHint: { textAlign: "center", color: "#94A3B8", fontSize: 13, marginTop: 8, fontStyle: "italic" },

  // Detection
  loadingRow: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 16 },
  loadingText: { fontSize: 14, color: "#64748B" },
  idleRow: { flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 12 },
  idleIcon: { fontSize: 20 },
  idleText: { fontSize: 13, color: "#94A3B8", flex: 1, lineHeight: 20 },
  resultBox: { paddingVertical: 12 },
  resultTitle: { fontSize: 16, fontWeight: "700", color: "#059669", marginBottom: 6 },
  resultDetail: { fontSize: 13, color: "#475569", marginBottom: 4, lineHeight: 20 },
  resultHint: { fontSize: 12, color: "#94A3B8", marginTop: 4 },

  // Buttons
  endBtn: { backgroundColor: "#EF4444", borderRadius: 18, paddingVertical: 18, flexDirection: "row", justifyContent: "center", alignItems: "center", gap: 8, shadowColor: "#EF4444", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  endBtnIcon: { fontSize: 20 },
  endBtnText: { fontSize: 18, fontWeight: "700", color: "#fff" },
  backBtn: { backgroundColor: "#2563EB", borderRadius: 18, paddingVertical: 18, alignItems: "center", shadowColor: "#2563EB", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 4 },
  backBtnText: { fontSize: 18, fontWeight: "700", color: "#fff" },
});
