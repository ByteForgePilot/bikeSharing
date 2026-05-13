import { View, Text, StyleSheet } from "react-native";

interface FaultInfo {
  detected: string; // normal | suspect | fault | unknown
  confidence: number;
  detail: string;
}

interface Props {
  wheel?: FaultInfo | null;
  chain?: FaultInfo | null;
  handlebar?: FaultInfo | null;
}

function getStatusColor(status: string): string {
  switch (status) {
    case "normal":
      return "#22c55e";
    case "suspect":
      return "#f59e0b";
    case "fault":
      return "#ef4444";
    default:
      return "#9ca3af";
  }
}

function getStatusLabel(status: string): string {
  switch (status) {
    case "normal":
      return "正常";
    case "suspect":
      return "疑似异常";
    case "fault":
      return "故障";
    default:
      return "未检测";
  }
}

function FaultRow({ icon, label, fault }: { icon: string; label: string; fault?: FaultInfo | null }) {
  const status = fault?.detected ?? "unknown";
  const color = getStatusColor(status);

  return (
    <View style={styles.row}>
      <Text style={styles.icon}>{icon}</Text>
      <Text style={styles.label}>{label}</Text>
      <View style={[styles.badge, { backgroundColor: color + "18" }]}>
        <Text style={[styles.status, { color }]}>{getStatusLabel(status)}</Text>
      </View>
      {fault?.confidence != null && (
        <Text style={styles.confidence}>{Math.round(fault.confidence * 100)}%</Text>
      )}
    </View>
  );
}

export default function FaultIndicator({ wheel, chain, handlebar }: Props) {
  return (
    <View style={styles.container}>
      <FaultRow icon="🛞" label="轮胎偏摆" fault={wheel} />
      <FaultRow icon="🔗" label="链条异响" fault={chain} />
      <FaultRow icon="🔧" label="车头不正" fault={handlebar} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: 4 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 8,
    gap: 8,
  },
  icon: { fontSize: 18 },
  label: { flex: 1, fontSize: 14, color: "#374151" },
  badge: {
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  status: { fontSize: 13, fontWeight: "600" },
  confidence: {
    fontSize: 12,
    color: "#9ca3af",
    width: 40,
    textAlign: "right",
  },
});
