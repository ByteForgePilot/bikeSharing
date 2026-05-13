import { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import * as Sensors from "expo-sensors";

export default function RideScreen() {
  const { bikeId } = useLocalSearchParams<{ bikeId: string }>();

  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [accelData, setAccelData] = useState<{ x: number; y: number; z: number } | null>(null);
  const [gyroData, setGyroData] = useState<{ x: number; y: number; z: number } | null>(null);
  const [faultStatus, setFaultStatus] = useState({
    wheel: "检测中...",
    chain: "检测中...",
    handlebar: "检测中...",
  });

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const accelSub = useRef<Sensors.Subscription | null>(null);
  const gyroSub = useRef<Sensors.Subscription | null>(null);

  useEffect(() => {
    startSensors();
    return () => {
      stopSensors();
    };
  }, []);

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  useEffect(() => {
    // Simulate fault detection updates
    if (elapsed > 3) {
      setFaultStatus({
        wheel: "正常",
        chain: "正常",
        handlebar: "检测中...",
      });
    }
    if (elapsed > 10) {
      setFaultStatus({
        wheel: "正常",
        chain: "异常 ⚠️",
        handlebar: "正常",
      });
    }
  }, [elapsed]);

  const startSensors = () => {
    setIsRecording(true);

    // Accelerometer
    accelSub.current = Sensors.Accelerometer.addListener((data) => {
      setAccelData({ x: data.x, y: data.y, z: data.z });
    });
    Sensors.Accelerometer.setUpdateInterval(50); // 50ms = 20Hz

    // Gyroscope
    gyroSub.current = Sensors.Gyroscope.addListener((data) => {
      setGyroData({ x: data.x, y: data.y, z: data.z });
    });
    Sensors.Gyroscope.setUpdateInterval(50);
  };

  const stopSensors = () => {
    setIsRecording(false);
    accelSub.current?.remove();
    gyroSub.current?.remove();
  };

  const handleEndRide = () => {
    stopSensors();
    router.back();
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.bikeId}>车辆: {bikeId}</Text>
        <Text style={styles.timer}>{formatTime(elapsed)}</Text>
        <View style={[styles.statusDot, isRecording && styles.statusDotActive]} />
      </View>

      {/* Sensor data */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>传感器实时数据</Text>
        <View style={styles.sensorRow}>
          <View style={styles.sensorBox}>
            <Text style={styles.sensorLabel}>加速度计 (m/s²)</Text>
            <Text style={styles.sensorValue}>
              X: {accelData?.x.toFixed(2) ?? "--"}
            </Text>
            <Text style={styles.sensorValue}>
              Y: {accelData?.y.toFixed(2) ?? "--"}
            </Text>
            <Text style={styles.sensorValue}>
              Z: {accelData?.z.toFixed(2) ?? "--"}
            </Text>
          </View>
          <View style={styles.sensorBox}>
            <Text style={styles.sensorLabel}>陀螺仪 (rad/s)</Text>
            <Text style={styles.sensorValue}>
              X: {gyroData?.x.toFixed(2) ?? "--"}
            </Text>
            <Text style={styles.sensorValue}>
              Y: {gyroData?.y.toFixed(2) ?? "--"}
            </Text>
            <Text style={styles.sensorValue}>
              Z: {gyroData?.z.toFixed(2) ?? "--"}
            </Text>
          </View>
        </View>
      </View>

      {/* Fault detection status */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>故障检测状态</Text>
        <View style={styles.faultRow}>
          <Text style={styles.faultIcon}>🛞</Text>
          <Text style={styles.faultLabel}>轮胎偏摆</Text>
          <Text
            style={[
              styles.faultStatus,
              faultStatus.wheel === "异常 ⚠️" && styles.faultAbnormal,
            ]}
          >
            {faultStatus.wheel}
          </Text>
        </View>
        <View style={styles.faultRow}>
          <Text style={styles.faultIcon}>🔗</Text>
          <Text style={styles.faultLabel}>链条异响</Text>
          <Text
            style={[
              styles.faultStatus,
              faultStatus.chain === "异常 ⚠️" && styles.faultAbnormal,
            ]}
          >
            {faultStatus.chain}
          </Text>
        </View>
        <View style={[styles.faultRow, { borderBottomWidth: 0 }]}>
          <Text style={styles.faultIcon}>🔧</Text>
          <Text style={styles.faultLabel}>车头不正</Text>
          <Text
            style={[
              styles.faultStatus,
              faultStatus.handlebar === "异常 ⚠️" && styles.faultAbnormal,
            ]}
          >
            {faultStatus.handlebar}
          </Text>
        </View>
      </View>

      {/* End ride button */}
      <TouchableOpacity style={styles.endButton} onPress={handleEndRide}>
        <Text style={styles.endButtonText}>结束骑行</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f3f4f6" },
  content: { padding: 20, paddingBottom: 40 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#2563eb",
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
  },
  bikeId: { flex: 1, fontSize: 16, color: "#fff", fontWeight: "500" },
  timer: { fontSize: 32, fontWeight: "bold", color: "#fff", marginRight: 12 },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: "#fbbf24",
  },
  statusDotActive: { backgroundColor: "#22c55e" },
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  cardTitle: { fontSize: 16, fontWeight: "600", marginBottom: 16 },
  sensorRow: { flexDirection: "row", gap: 12 },
  sensorBox: {
    flex: 1,
    backgroundColor: "#f9fafb",
    borderRadius: 12,
    padding: 12,
  },
  sensorLabel: { fontSize: 12, color: "#6b7280", marginBottom: 8 },
  sensorValue: { fontSize: 13, color: "#374151", marginBottom: 2, fontFamily: "monospace" },
  faultRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#f3f4f6",
  },
  faultIcon: { fontSize: 20, marginRight: 12 },
  faultLabel: { flex: 1, fontSize: 15, color: "#374151" },
  faultStatus: { fontSize: 15, fontWeight: "500", color: "#22c55e" },
  faultAbnormal: { color: "#ef4444" },
  endButton: {
    backgroundColor: "#ef4444",
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: "center",
    marginTop: 8,
  },
  endButtonText: { fontSize: 18, fontWeight: "bold", color: "#fff" },
});
