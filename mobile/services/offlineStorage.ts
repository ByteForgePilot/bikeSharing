import * as FileSystem from "expo-file-system";
import type { SensorDataPoint, GPSDataPoint } from "./sensors";

const RIDES_DIR = `${FileSystem.documentDirectory}rides/`;

export type SyncStatusType = "local" | "syncing" | "synced" | "failed";

export interface OfflineRideMeta {
  rideId: string;
  bikeId: string;
  startedAt: string;
  endedAt: string | null;
  status: "active" | "completed";
  syncStatus?: SyncStatusType;
  hasAudio?: boolean;
}

export interface OfflineRide {
  meta: OfflineRideMeta;
  sensors: {
    accelerometer: SensorDataPoint[];
    gyroscope: SensorDataPoint[];
    gps: GPSDataPoint[];
    sampleRate: number;
  };
}

async function ensureDir() {
  const info = await FileSystem.getInfoAsync(RIDES_DIR);
  if (!info.exists) {
    await FileSystem.makeDirectoryAsync(RIDES_DIR, { intermediates: true });
  }
}

export async function createRide(rideId: string, bikeId: string): Promise<void> {
  await ensureDir();
  const meta: OfflineRideMeta = {
    rideId,
    bikeId,
    startedAt: new Date().toISOString(),
    endedAt: null,
    status: "active",
  };
  const rideDir = `${RIDES_DIR}${rideId}/`;
  await FileSystem.makeDirectoryAsync(rideDir);
  await FileSystem.writeAsStringAsync(`${rideDir}meta.json`, JSON.stringify(meta));
}

export async function finishRide(
  rideId: string,
  accelerometer: SensorDataPoint[],
  gyroscope: SensorDataPoint[],
  gps: GPSDataPoint[],
  sampleRate: number
): Promise<void> {
  const rideDir = `${RIDES_DIR}${rideId}/`;

  const metaStr = await FileSystem.readAsStringAsync(`${rideDir}meta.json`);
  const meta: OfflineRideMeta = JSON.parse(metaStr);
  meta.endedAt = new Date().toISOString();
  meta.status = "completed";
  await FileSystem.writeAsStringAsync(`${rideDir}meta.json`, JSON.stringify(meta));

  await FileSystem.writeAsStringAsync(
    `${rideDir}sensor_data.json`,
    JSON.stringify({ accelerometer, gyroscope, gps, sampleRate })
  );
}

export async function saveSensorChunk(
  rideId: string,
  accelerometer: SensorDataPoint[],
  gyroscope: SensorDataPoint[],
  gps: GPSDataPoint[]
): Promise<void> {
  const rideDir = `${RIDES_DIR}${rideId}/`;
  // Ensure directory exists (may not if ride started online then went offline)
  const dirInfo = await FileSystem.getInfoAsync(rideDir);
  if (!dirInfo.exists) {
    await FileSystem.makeDirectoryAsync(rideDir, { intermediates: true });
  }
  const chunkFile = `${rideDir}chunk_${Date.now()}.json`;
  await FileSystem.writeAsStringAsync(
    chunkFile,
    JSON.stringify({ accelerometer, gyroscope, gps })
  );
}

export async function listRides(): Promise<OfflineRideMeta[]> {
  await ensureDir();
  const dirs = await FileSystem.readDirectoryAsync(RIDES_DIR);
  const metas: OfflineRideMeta[] = [];
  for (const dir of dirs) {
    try {
      const metaStr = await FileSystem.readAsStringAsync(`${RIDES_DIR}${dir}/meta.json`);
      metas.push(JSON.parse(metaStr));
    } catch {
      // skip corrupted entries
    }
  }
  metas.sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime());
  return metas;
}

export async function getRide(rideId: string): Promise<OfflineRide | null> {
  const rideDir = `${RIDES_DIR}${rideId}/`;
  try {
    const metaStr = await FileSystem.readAsStringAsync(`${rideDir}meta.json`);
    const meta: OfflineRideMeta = JSON.parse(metaStr);

    let sensors = {
      accelerometer: [] as SensorDataPoint[],
      gyroscope: [] as SensorDataPoint[],
      gps: [] as GPSDataPoint[],
      sampleRate: 20,
    };

    const sensorFile = await FileSystem.getInfoAsync(`${rideDir}sensor_data.json`);
    if (sensorFile.exists) {
      const sensorStr = await FileSystem.readAsStringAsync(`${rideDir}sensor_data.json`);
      const parsed = JSON.parse(sensorStr);
      sensors = { ...sensors, ...parsed };
    } else {
      const files = await FileSystem.readDirectoryAsync(rideDir);
      for (const f of files) {
        if (f.startsWith("chunk_")) {
          const chunkStr = await FileSystem.readAsStringAsync(`${rideDir}${f}`);
          const chunk = JSON.parse(chunkStr);
          sensors.accelerometer.push(...(chunk.accelerometer || []));
          sensors.gyroscope.push(...(chunk.gyroscope || []));
          sensors.gps.push(...(chunk.gps || []));
        }
      }
    }

    return { meta, sensors };
  } catch {
    return null;
  }
}

export async function deleteRide(rideId: string): Promise<void> {
  const rideDir = `${RIDES_DIR}${rideId}/`;
  await FileSystem.deleteAsync(rideDir, { idempotent: true });
}

export async function setSyncStatus(rideId: string, status: SyncStatusType): Promise<void> {
  const rideDir = `${RIDES_DIR}${rideId}/`;
  try {
    const metaStr = await FileSystem.readAsStringAsync(`${rideDir}meta.json`);
    const meta: OfflineRideMeta = JSON.parse(metaStr);
    meta.syncStatus = status;
    await FileSystem.writeAsStringAsync(`${rideDir}meta.json`, JSON.stringify(meta));
  } catch {
    // ride directory may not exist
  }
}

export async function saveAudioUri(rideId: string, audioUri: string): Promise<void> {
  const rideDir = `${RIDES_DIR}${rideId}/`;
  const destUri = `${rideDir}audio_recording.wav`;
  await FileSystem.copyAsync({ from: audioUri, to: destUri });
  const metaStr = await FileSystem.readAsStringAsync(`${rideDir}meta.json`);
  const meta: OfflineRideMeta = JSON.parse(metaStr);
  meta.hasAudio = true;
  await FileSystem.writeAsStringAsync(`${rideDir}meta.json`, JSON.stringify(meta));
}

export { RIDES_DIR };

export async function isBackendReachable(): Promise<boolean> {
  const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);
    const resp = await fetch(`${BASE_URL}/api/health`, { signal: controller.signal });
    clearTimeout(timeout);
    return resp.ok;
  } catch {
    return false;
  }
}
