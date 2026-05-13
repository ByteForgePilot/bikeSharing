import { useEffect, useRef, useState } from "react";
import { View, Text, StyleSheet } from "react-native";
import { sensorCollector, type SensorBuffer } from "../services/sensors";

interface Props {
  active: boolean;
  onDataFlush: (buffer: SensorBuffer) => void;
}

export default function SensorCollector({ active, onDataFlush }: Props) {
  const [sampleCount, setSampleCount] = useState(0);
  const countRef = useRef(0);

  useEffect(() => {
    if (active) {
      sensorCollector.start((buffer) => {
        countRef.current += buffer.sampleCount;
        setSampleCount(countRef.current);
        onDataFlush(buffer);
      });
      return () => {
        sensorCollector.stop();
      };
    }
  }, [active]);

  return (
    <View style={styles.container}>
      <Text style={styles.label}>数据采集: {sampleCount} 样本</Text>
      <View style={[styles.indicator, active && styles.indicatorActive]} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  label: { fontSize: 12, color: "#6b7280", fontFamily: "monospace" },
  indicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#d1d5db",
  },
  indicatorActive: {
    backgroundColor: "#22c55e",
  },
});
