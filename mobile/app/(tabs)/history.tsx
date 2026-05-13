import { View, Text, FlatList, StyleSheet } from "react-native";

const MOCK_RIDES = [
  {
    id: "1",
    bikeId: "BIKE-001",
    date: "2026-05-13 14:30",
    duration: "12:34",
    wheel_wobble: "正常",
    chain_noise: "正常",
    handlebar: "正常",
  },
  {
    id: "2",
    bikeId: "BIKE-042",
    date: "2026-05-12 09:15",
    duration: "08:22",
    wheel_wobble: "正常",
    chain_noise: "异常 ⚠️",
    handlebar: "正常",
  },
  {
    id: "3",
    bikeId: "BIKE-018",
    date: "2026-05-11 17:45",
    duration: "15:07",
    wheel_wobble: "异常 ⚠️",
    chain_noise: "正常",
    handlebar: "异常 ⚠️",
  },
];

export default function HistoryScreen() {
  const renderItem = ({ item }: { item: (typeof MOCK_RIDES)[0] }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.bikeId}>{item.bikeId}</Text>
        <Text style={styles.date}>{item.date}</Text>
      </View>
      <Text style={styles.duration}>骑行时长: {item.duration}</Text>
      <View style={styles.faultRow}>
        <FaultBadge label="轮胎" status={item.wheel_wobble} />
        <FaultBadge label="链条" status={item.chain_noise} />
        <FaultBadge label="车头" status={item.handlebar} />
      </View>
    </View>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>骑行历史</Text>
      <FlatList
        data={MOCK_RIDES}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={styles.list}
      />
    </View>
  );
}

function FaultBadge({ label, status }: { label: string; status: string }) {
  const isAbnormal = status.includes("异常");
  return (
    <View
      style={[
        styles.badge,
        isAbnormal ? styles.badgeAbnormal : styles.badgeNormal,
      ]}
    >
      <Text style={styles.badgeLabel}>{label}</Text>
      <Text
        style={[
          styles.badgeStatus,
          isAbnormal ? styles.badgeStatusAbnormal : styles.badgeStatusNormal,
        ]}
      >
        {status}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f3f4f6", padding: 20 },
  title: {
    fontSize: 24,
    fontWeight: "bold",
    color: "#111827",
    marginTop: 20,
    marginBottom: 16,
  },
  list: { gap: 12, paddingBottom: 40 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  bikeId: { fontSize: 16, fontWeight: "600", color: "#2563eb" },
  date: { fontSize: 13, color: "#9ca3af" },
  duration: { fontSize: 14, color: "#6b7280", marginBottom: 12 },
  faultRow: { flexDirection: "row", gap: 8 },
  badge: {
    flex: 1,
    borderRadius: 10,
    padding: 8,
    alignItems: "center",
  },
  badgeNormal: { backgroundColor: "#ecfdf5" },
  badgeAbnormal: { backgroundColor: "#fef2f2" },
  badgeLabel: { fontSize: 12, color: "#6b7280", marginBottom: 2 },
  badgeStatus: { fontSize: 13, fontWeight: "600" },
  badgeStatusNormal: { color: "#059669" },
  badgeStatusAbnormal: { color: "#dc2626" },
});
