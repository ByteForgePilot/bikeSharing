import { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  TextInput,
  Alert,
} from "react-native";
import { router } from "expo-router";

export default function HomeScreen() {
  const [bikeId, setBikeId] = useState("");
  const [isRiding, setIsRiding] = useState(false);

  const handleStartRide = () => {
    if (!bikeId.trim()) {
      Alert.alert("提示", "请输入车辆编号");
      return;
    }
    setIsRiding(true);
    router.push({
      pathname: "/(tabs)/ride",
      params: { bikeId: bikeId.trim() },
    });
  };

  const handleScanQR = () => {
    // Placeholder for QR scanner
    Alert.alert("扫码", "扫码功能开发中，请手动输入车辆编号");
  };

  return (
    <View style={styles.container}>
      <View style={styles.hero}>
        <Text style={styles.title}>bikeSharing</Text>
        <Text style={styles.subtitle}>共享单车故障智能检测</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>开始骑行检测</Text>
        <TextInput
          style={styles.input}
          placeholder="输入车辆编号"
          value={bikeId}
          onChangeText={setBikeId}
          autoCapitalize="none"
        />
        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={styles.scanButton}
            onPress={handleScanQR}
          >
            <Text style={styles.scanButtonText}>扫码</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.startButton, !bikeId && styles.startButtonDisabled]}
            onPress={handleStartRide}
            disabled={!bikeId.trim()}
          >
            <Text style={styles.startButtonText}>开始骑行</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.infoCard}>
        <Text style={styles.infoTitle}>检测项目</Text>
        <Text style={styles.infoItem}>🛞 轮胎偏摆 — 加速度计分析</Text>
        <Text style={styles.infoItem}>🔗 链条异响 — 麦克风检测</Text>
        <Text style={styles.infoItem}>🔧 车头不正 — 陀螺仪分析</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    padding: 20,
  },
  hero: {
    alignItems: "center",
    marginTop: 40,
    marginBottom: 30,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#2563eb",
  },
  subtitle: {
    fontSize: 14,
    color: "#6b7280",
    marginTop: 4,
  },
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
    marginBottom: 20,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 16,
  },
  input: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    marginBottom: 16,
  },
  buttonRow: {
    flexDirection: "row",
    gap: 12,
  },
  scanButton: {
    flex: 1,
    backgroundColor: "#f3f4f6",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  scanButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#374151",
  },
  startButton: {
    flex: 2,
    backgroundColor: "#2563eb",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
  },
  startButtonDisabled: {
    backgroundColor: "#93c5fd",
  },
  startButtonText: {
    fontSize: 16,
    fontWeight: "600",
    color: "#fff",
  },
  infoCard: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 12,
  },
  infoItem: {
    fontSize: 14,
    color: "#4b5563",
    marginBottom: 6,
  },
});
