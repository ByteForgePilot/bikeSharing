import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  LayoutAnimation,
  Platform,
  UIManager,
} from "react-native";
import { useAuthContext } from "../../hooks/AuthContext";
import * as api from "../../services/api";
import * as offlineStorage from "../../services/offlineStorage";
import type { OfflineRideMeta, SyncStatusType } from "../../services/offlineStorage";
import { formatDate } from "../../utils/formatters";

// Enable LayoutAnimation on Android
if (Platform.OS === "android" && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

interface RideDisplayItem {
  id: string;
  bike_id: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  syncStatus?: SyncStatusType;
  dataSource: "server" | "local";
}

type FilterMode = "全部" | "已完成" | "进行中";

const FILTERS: FilterMode[] = ["全部", "已完成", "进行中"];

function ExpandIcon({ expanded }: { expanded: boolean }) {
  return (
    <Text style={{ fontSize: 14, color: "#94A3B8" }}>{expanded ? "▲" : "▼"}</Text>
  );
}

export default function HistoryScreen() {
  const { token, online, isSyncing, syncPendingRides } = useAuthContext();
  const [rides, setRides] = useState<RideDisplayItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterMode>("全部");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const fetchRides = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (online && token) {
        const data = await api.getRides(token, 50, 0);
        setRides(
          data.rides.map((r) => ({
            id: String(r.id),
            bike_id: r.bike_id,
            started_at: r.started_at,
            ended_at: r.ended_at,
            status: r.status,
            dataSource: "server" as const,
          }))
        );
      } else {
        const metas: OfflineRideMeta[] = await offlineStorage.listRides();
        setRides(
          metas.map((m) => ({
            id: m.rideId,
            bike_id: m.bikeId,
            started_at: m.startedAt,
            ended_at: m.endedAt,
            status: m.status,
            syncStatus: m.syncStatus ?? "local",
            dataSource: "local" as const,
          }))
        );
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "未知错误";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [token, online]);

  useEffect(() => {
    fetchRides();
  }, [fetchRides]);

  const handleSync = async () => {
    const result = await syncPendingRides();
    if (result.uploaded > 0 || result.failed > 0) {
      fetchRides();
    }
  };

  const toggleExpand = (id: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const formatDuration = (started: string, ended: string | null): string => {
    const start = new Date(started).getTime();
    const end = ended ? new Date(ended).getTime() : Date.now();
    const totalSec = Math.floor((end - start) / 1000);
    const m = Math.floor(totalSec / 60);
    const s = totalSec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const filteredRides = rides.filter((r) => {
    if (filter === "已完成") return r.status !== "active";
    if (filter === "进行中") return r.status === "active";
    return true;
  });

  const activeCount = rides.filter((r) => r.status === "active").length;
  const completedCount = rides.filter((r) => r.status !== "active").length;

  const renderItem = ({ item }: { item: RideDisplayItem }) => {
    const expanded = expandedIds.has(item.id);
    const isActive = item.status === "active";

    return (
      <TouchableOpacity
        style={[styles.card, isActive && styles.cardActive]}
        onPress={() => toggleExpand(item.id)}
        activeOpacity={0.7}
      >
        {/* Main row */}
        <View style={styles.cardMain}>
          <View style={styles.cardLeft}>
            <Text style={styles.bikeIcon}>🚲</Text>
            <View>
              <Text style={styles.bikeId}>{item.bike_id}</Text>
              <Text style={styles.date}>{formatDate(item.started_at)}</Text>
            </View>
          </View>
          <View style={styles.cardRight}>
            <View style={[styles.statusBadge, isActive ? styles.badgeActive : styles.badgeDone]}>
              <Text style={[styles.statusText, isActive ? styles.statusTextActive : styles.statusTextDone]}>
                {isActive ? "进行中" : "已完成"}
              </Text>
            </View>
            <ExpandIcon expanded={expanded} />
          </View>
        </View>

        {/* Expandable detail */}
        {expanded && (
          <View style={styles.detailSection}>
            <View style={styles.detailDivider} />
            <View style={styles.detailGrid}>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>骑行时长</Text>
                <Text style={styles.detailValue}>{formatDuration(item.started_at, item.ended_at)}</Text>
              </View>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>开始时间</Text>
                <Text style={styles.detailValue}>{formatDate(item.started_at)}</Text>
              </View>
              {item.ended_at && (
                <View style={styles.detailItem}>
                  <Text style={styles.detailLabel}>结束时间</Text>
                  <Text style={styles.detailValue}>{formatDate(item.ended_at)}</Text>
                </View>
              )}
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>数据来源</Text>
                <Text style={styles.detailValue}>
                  {item.dataSource === "server"
                    ? "服务器"
                    : item.syncStatus === "syncing"
                      ? "同步中..."
                      : item.syncStatus === "synced"
                        ? "已同步"
                        : item.syncStatus === "failed"
                          ? "同步失败"
                          : "本地 (待同步)"}
                </Text>
              </View>
            </View>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color="#2563EB" />
        <Text style={styles.loadingText}>加载骑行记录...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={[styles.container, styles.centered]}>
        <Text style={styles.errorTitle}>加载失败</Text>
        <Text style={styles.errorDetail}>{error}</Text>
        <TouchableOpacity style={styles.retryBtn} onPress={fetchRides}>
          <Text style={styles.retryText}>重试</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <Text style={styles.title}>骑行历史</Text>
          <View style={styles.headerActions}>
            {!online && (
              <View style={styles.offlineTag}>
                <Text style={styles.offlineTagText}>📱 本地</Text>
              </View>
            )}
            {online && (
              <TouchableOpacity
                style={[styles.syncBtn, isSyncing && { opacity: 0.6 }]}
                onPress={handleSync}
                disabled={isSyncing}
                activeOpacity={0.7}
              >
                <Text style={styles.syncBtnText}>{isSyncing ? "⏳" : "🔄"} 同步</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{rides.length}</Text>
            <Text style={styles.statLabel}>全部</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{activeCount}</Text>
            <Text style={styles.statLabel}>进行中</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{completedCount}</Text>
            <Text style={styles.statLabel}>已完成</Text>
          </View>
        </View>
      </View>

      {/* Filter tabs */}
      <View style={styles.filterRow}>
        {FILTERS.map((f) => (
          <TouchableOpacity
            key={f}
            style={[styles.filterBtn, filter === f && styles.filterBtnActive]}
            onPress={() => setFilter(f)}
            activeOpacity={0.7}
          >
            <Text style={[styles.filterText, filter === f && styles.filterTextActive]}>{f}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* List */}
      {filteredRides.length === 0 ? (
        <View style={styles.emptyBox}>
          <Text style={styles.emptyIcon}>📭</Text>
          <Text style={styles.emptyTitle}>
            {filter !== "全部" ? `没有${filter}的骑行` : "暂无骑行记录"}
          </Text>
          <Text style={styles.emptyHint}>
            {filter !== "全部" ? "试试切换筛选条件" : "开始一次骑行检测吧"}
          </Text>
        </View>
      ) : (
        <FlatList
          data={filteredRides}
          renderItem={renderItem}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.list}
          onRefresh={fetchRides}
          refreshing={loading}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F8FAFC" },
  centered: { justifyContent: "center", alignItems: "center", padding: 20 },
  list: { padding: 20, paddingBottom: 40 },

  // Header
  header: { paddingHorizontal: 20, paddingTop: 24, paddingBottom: 16 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 14 },
  headerActions: { flexDirection: "row", alignItems: "center", gap: 8 },
  title: { fontSize: 26, fontWeight: "800", color: "#1E293B" },
  offlineTag: { backgroundColor: "#FEF3C7", paddingHorizontal: 10, paddingVertical: 3, borderRadius: 10 },
  offlineTagText: { fontSize: 11, fontWeight: "600", color: "#B45309" },
  syncBtn: { backgroundColor: "#DBEAFE", paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10 },
  syncBtnText: { fontSize: 12, fontWeight: "600", color: "#1D4ED8" },

  // Stats
  statsRow: { flexDirection: "row", alignItems: "center", backgroundColor: "#fff", borderRadius: 16, padding: 16, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.03, shadowRadius: 6, elevation: 2 },
  statBox: { flex: 1, alignItems: "center" },
  statNum: { fontSize: 22, fontWeight: "700", color: "#1E293B" },
  statLabel: { fontSize: 12, color: "#94A3B8", marginTop: 2 },
  statDivider: { width: 1, height: 30, backgroundColor: "#F1F5F9" },

  // Filters
  filterRow: { flexDirection: "row", paddingHorizontal: 20, marginBottom: 12, gap: 8 },
  filterBtn: { flex: 1, paddingVertical: 10, borderRadius: 12, backgroundColor: "#F1F5F9", alignItems: "center" },
  filterBtnActive: { backgroundColor: "#1E293B" },
  filterText: { fontSize: 14, fontWeight: "600", color: "#64748B" },
  filterTextActive: { color: "#fff" },

  // Cards
  card: { backgroundColor: "#fff", borderRadius: 16, marginBottom: 10, padding: 16, shadowColor: "#000", shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.03, shadowRadius: 4, elevation: 1 },
  cardActive: { borderLeftWidth: 3, borderLeftColor: "#F59E0B" },
  cardMain: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  cardLeft: { flexDirection: "row", alignItems: "center", gap: 10, flex: 1 },
  bikeIcon: { fontSize: 24 },
  bikeId: { fontSize: 16, fontWeight: "600", color: "#1E293B" },
  date: { fontSize: 12, color: "#94A3B8", marginTop: 2 },
  cardRight: { flexDirection: "row", alignItems: "center", gap: 10 },

  // Status
  statusBadge: { borderRadius: 10, paddingHorizontal: 12, paddingVertical: 5 },
  badgeActive: { backgroundColor: "#FEF3C7" },
  badgeDone: { backgroundColor: "#ECFDF5" },
  statusText: { fontSize: 12, fontWeight: "700" },
  statusTextActive: { color: "#B45309" },
  statusTextDone: { color: "#047857" },

  // Expandable detail
  detailSection: { marginTop: 12 },
  detailDivider: { height: 1, backgroundColor: "#F1F5F9", marginBottom: 12 },
  detailGrid: { gap: 8 },
  detailItem: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  detailLabel: { fontSize: 13, color: "#94A3B8" },
  detailValue: { fontSize: 13, fontWeight: "600", color: "#334155" },

  // Empty
  emptyBox: { flex: 1, justifyContent: "center", alignItems: "center", paddingBottom: 60 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: "#64748B", marginBottom: 6 },
  emptyHint: { fontSize: 13, color: "#CBD5E1" },

  // Loading / Error
  loadingText: { fontSize: 14, color: "#64748B", marginTop: 10 },
  errorTitle: { fontSize: 18, fontWeight: "700", color: "#EF4444", marginBottom: 6 },
  errorDetail: { fontSize: 13, color: "#64748B", textAlign: "center", marginBottom: 16 },
  retryBtn: { backgroundColor: "#2563EB", borderRadius: 14, paddingHorizontal: 28, paddingVertical: 12 },
  retryText: { fontSize: 14, fontWeight: "700", color: "#fff" },
});
