import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: "#2563eb",
        tabBarInactiveTintColor: "#6b7280",
        headerStyle: { backgroundColor: "#2563eb" },
        headerTintColor: "#fff",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "骑行",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="bicycle" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="ride"
        options={{
          title: "检测中",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="speedometer" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: "历史",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="time" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
