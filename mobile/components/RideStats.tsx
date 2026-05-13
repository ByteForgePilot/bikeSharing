import { View, Text, StyleSheet } from "react-native";

interface Props {
  duration: number; // seconds
  distance: number; // km
  avgSpeed: number; // km/h
}

export default function RideStats({ duration, distance, avgSpeed }: Props) {
  const minutes = Math.floor(duration / 60);
  const seconds = duration % 60;

  return (
    <View style={styles.container}>
      <View style={styles.statBox}>
        <Text style={styles.value}>
          {String(minutes).padStart(2, "0")}:{String(seconds).padStart(2, "0")}
        </Text>
        <Text style={styles.label}>时长</Text>
      </View>
      <View style={styles.divider} />
      <View style={styles.statBox}>
        <Text style={styles.value}>{distance.toFixed(2)}</Text>
        <Text style={styles.label}>距离 (km)</Text>
      </View>
      <View style={styles.divider} />
      <View style={styles.statBox}>
        <Text style={styles.value}>{avgSpeed.toFixed(1)}</Text>
        <Text style={styles.label}>均速 (km/h)</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 16,
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  statBox: { flex: 1, alignItems: "center" },
  value: { fontSize: 22, fontWeight: "bold", color: "#111827", fontFamily: "monospace" },
  label: { fontSize: 12, color: "#9ca3af", marginTop: 4 },
  divider: { width: 1, height: 36, backgroundColor: "#e5e7eb" },
});
