import { useState, useRef } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  TextInput,
  Alert,
  ActivityIndicator,
  Animated,
  ScrollView,
} from "react-native";
import { router } from "expo-router";
import { useAuthContext } from "../../hooks/AuthContext";
import * as api from "../../services/api";
import * as offlineStorage from "../../services/offlineStorage";

const BIKE_ICONS = ["🚲", "🚴", "🛴", "🛵"];

export default function HomeScreen() {
  const { token, loading: authLoading, online } = useAuthContext();
  const [bikeId, setBikeId] = useState("");
  const [starting, setStarting] = useState(false);
  const pulseAnim = useRef(new Animated.Value(1)).current;

  // Pulse animation for the start button
  const startPulse = () => {
    Animated.sequence([
      Animated.timing(pulseAnim, { toValue: 0.95, duration: 100, useNativeDriver: true }),
      Animated.timing(pulseAnim, { toValue: 1, duration: 100, useNativeDriver: true }),
    ]).start();
  };

  const handleStartRide = async () => {
    startPulse();
    if (!bikeId.trim()) {
      Alert.alert("提示", "请输入车辆编号");
      return;
    }

    setStarting(true);
    try {
      let rideId: string;

      if (online && token) {
        const result = await api.startRide(bikeId.trim(), 0, 0, token);
        rideId = String(result.ride?.id);
        if (!rideId) throw new Error("未返回骑行编号");
      } else {
        rideId = `${Date.now()}_${bikeId.trim()}`;
      }
      // Always create local ride directory so offline fallback works
      await offlineStorage.createRide(rideId, bikeId.trim());

      router.push({
        pathname: "/(tabs)/ride",
        params: { bikeId: bikeId.trim(), rideId },
      });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "未知错误";
      Alert.alert("启动失败", `无法开始骑行: ${message}`);
    } finally {
      setStarting(false);
    }
  };

  if (authLoading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color="#2563EB" />
        <Text style={styles.connectingText}>正在检测后端服务...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.scrollContent}>
      {/* Hero */}
      <View style={styles.hero}>
        <Text style={styles.heroIcon}>🚲</Text>
        <Text style={styles.heroTitle}>共享单车故障检测</Text>
        <Text style={styles.heroSubtitle}>骑行前检测 · 保障出行安全</Text>
        {!online && (
          <View style={styles.offlineBadge}>
            <Text style={styles.offlineBadgeText}>📱 离线模式 · 数据本地保存</Text>
          </View>
        )}
        {online && (
          <View style={styles.onlineBadge}>
            <Text style={styles.onlineBadgeText}>🟢 已连接服务器</Text>
          </View>
        )}
      </View>

      {/* Start ride card */}
      <View style={styles.mainCard}>
        <View style={styles.mainCardHeader}>
          <Text style={styles.mainCardIcon}>🔑</Text>
          <Text style={styles.mainCardTitle}>开始骑行</Text>
        </View>
        <Text style={styles.mainCardDesc}>输入车身编号或扫描二维码</Text>

        <View style={styles.inputWrapper}>
          <TextInput
            style={styles.input}
            placeholder="输入车辆编号，例如：B001"
            placeholderTextColor="#9CA3AF"
            value={bikeId}
            onChangeText={setBikeId}
            autoCapitalize="characters"
            returnKeyType="go"
            onSubmitEditing={handleStartRide}
          />
          <TouchableOpacity
            style={styles.scanBtn}
            onPress={() => Alert.alert("扫码", "请对准车身二维码")}
            activeOpacity={0.7}
          >
            <Text style={styles.scanBtnText}>📷</Text>
          </TouchableOpacity>
        </View>

        <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
          <TouchableOpacity
            style={[styles.startBtn, (!bikeId.trim() || starting) && styles.startBtnDisabled]}
            onPress={handleStartRide}
            disabled={!bikeId.trim() || starting}
            activeOpacity={0.8}
          >
            {starting ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.startBtnText}>🚴 开始骑行检测</Text>
            )}
          </TouchableOpacity>
        </Animated.View>
      </View>

      {/* Detection items */}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>🔍 自动检测项目</Text>
      </View>

      <View style={styles.detectGrid}>
        {[
          { icon: "🛞", title: "轮胎偏摆", desc: "加速度计分析轮毂晃动", color: "#EFF6FF", accent: "#2563EB" },
          { icon: "🔗", title: "链条异响", desc: "振动频谱检测异常噪声", color: "#FFFBEB", accent: "#D97706" },
          { icon: "🔧", title: "车头不正", desc: "陀螺仪检测转向偏移", color: "#ECFDF5", accent: "#059669" },
        ].map((item) => (
          <View key={item.title} style={[styles.detectCard, { backgroundColor: item.color }]}>
            <Text style={styles.detectIcon}>{item.icon}</Text>
            <Text style={[styles.detectTitle, { color: item.accent }]}>{item.title}</Text>
            <Text style={styles.detectDesc}>{item.desc}</Text>
          </View>
        ))}
      </View>

      {/* Quick tips */}
      <View style={styles.tipCard}>
        <Text style={styles.tipTitle}>💡 使用提示</Text>
        <Text style={styles.tipText}>· 骑行中手机会持续采集传感器数据</Text>
        <Text style={styles.tipText}>· 结束骑行后自动执行故障检测</Text>
        <Text style={styles.tipText}>· 离线模式下数据保存在手机本地</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAFC" },
  scrollContent: { padding: 20, paddingBottom: 40 },
  centered: { justifyContent: "center", alignItems: "center" },
  connectingText: { marginTop: 12, fontSize: 14, color: "#64748B" },

  // Hero
  hero: { alignItems: "center", marginTop: 48, marginBottom: 24 },
  heroIcon: { fontSize: 56, marginBottom: 8 },
  heroTitle: { fontSize: 24, fontWeight: "800", color: "#1E293B", letterSpacing: 0.5 },
  heroSubtitle: { fontSize: 14, color: "#64748B", marginTop: 6 },
  offlineBadge: { marginTop: 10, backgroundColor: "#FEF3C7", paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20 },
  offlineBadgeText: { fontSize: 12, color: "#B45309", fontWeight: "600" },
  onlineBadge: { marginTop: 10, backgroundColor: "#D1FAE5", paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20 },
  onlineBadgeText: { fontSize: 12, color: "#047857", fontWeight: "600" },

  // Main card
  mainCard: { backgroundColor: "#fff", borderRadius: 20, padding: 24, marginBottom: 24, shadowColor: "#000", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.06, shadowRadius: 12, elevation: 4 },
  mainCardHeader: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 4 },
  mainCardIcon: { fontSize: 20 },
  mainCardTitle: { fontSize: 20, fontWeight: "700", color: "#1E293B" },
  mainCardDesc: { fontSize: 13, color: "#94A3B8", marginBottom: 16 },

  // Input
  inputWrapper: { flexDirection: "row", gap: 8, marginBottom: 16 },
  input: { flex: 1, borderWidth: 2, borderColor: "#E2E8F0", borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14, fontSize: 16, color: "#1E293B", backgroundColor: "#F8FAFC" },
  scanBtn: { width: 52, height: 52, backgroundColor: "#F1F5F9", borderRadius: 14, justifyContent: "center", alignItems: "center" },
  scanBtnText: { fontSize: 24 },

  // Start button
  startBtn: { backgroundColor: "#2563EB", borderRadius: 16, paddingVertical: 18, alignItems: "center", shadowColor: "#2563EB", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 6 },
  startBtnDisabled: { backgroundColor: "#93C5FD", shadowOpacity: 0 },
  startBtnText: { fontSize: 18, fontWeight: "700", color: "#fff" },

  // Detection grid
  sectionHeader: { marginBottom: 12 },
  sectionTitle: { fontSize: 18, fontWeight: "700", color: "#1E293B" },
  detectGrid: { flexDirection: "row", gap: 10, marginBottom: 24 },
  detectCard: { flex: 1, borderRadius: 16, padding: 14, alignItems: "center" },
  detectIcon: { fontSize: 28, marginBottom: 6 },
  detectTitle: { fontSize: 13, fontWeight: "700", marginBottom: 4 },
  detectDesc: { fontSize: 11, color: "#64748B", textAlign: "center", lineHeight: 16 },

  // Tips
  tipCard: { backgroundColor: "#fff", borderRadius: 16, padding: 20, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 8, elevation: 2 },
  tipTitle: { fontSize: 16, fontWeight: "700", color: "#1E293B", marginBottom: 10 },
  tipText: { fontSize: 13, color: "#64748B", marginBottom: 6, lineHeight: 20 },
});
