import * as FileSystem from "expo-file-system";
import type { SensorDataPoint } from "./sensors";

const RIDES_DIR = `${FileSystem.documentDirectory}rides/`;

export interface OfflineRideMeta {
  rideId: string;
  bikeId: string;
  startedAt: string;
  endedAt: string | null;
  status: "active" | "completed";
}

export interface OfflineRide {
  meta: OfflineRideMeta;
  sensors: {
    accelerometer: SensorDataPoint[];
    gyroscope: SensorDataPoint[];
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
  sampleRate: number
): Promise<void> {
  const rideDir = `${RIDES_DIR}${rideId}/`;

  // Update meta
  const metaStr = await FileSystem.readAsStringAsync(`${rideDir}meta.json`);
  const meta: OfflineRideMeta = JSON.parse(metaStr);
  meta.endedAt = new Date().toISOString();
  meta.status = "completed";
  await FileSystem.writeAsStringAsync(`${rideDir}meta.json`, JSON.stringify(meta));

  // Save all sensor data
  await FileSystem.writeAsStringAsync(
    `${rideDir}sensor_data.json`,
    JSON.stringify({ accelerometer, gyroscope, sampleRate })
  );
}

export async function saveSensorChunk(
  rideId: string,
  accelerometer: SensorDataPoint[],
  gyroscope: SensorDataPoint[]
): Promise<void> {
  const rideDir = `${RIDES_DIR}${rideId}/`;
  const chunkFile = `${rideDir}chunk_${Date.now()}.json`;
  await FileSystem.writeAsStringAsync(
    chunkFile,
    JSON.stringify({ accelerometer, gyroscope })
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

    let sensors = { accelerometer: [] as SensorDataPoint[], gyroscope: [] as SensorDataPoint[], sampleRate: 20 };

    // Try to read the full sensor_data.json (written at finish)
    const sensorFile = await FileSystem.getInfoAsync(`${rideDir}sensor_data.json`);
    if (sensorFile.exists) {
      const sensorStr = await FileSystem.readAsStringAsync(`${rideDir}sensor_data.json`);
      sensors = JSON.parse(sensorStr);
    } else {
      // Merge chunk files
      const files = await FileSystem.readDirectoryAsync(rideDir);
      for (const f of files) {
        if (f.startsWith("chunk_")) {
          const chunkStr = await FileSystem.readAsStringAsync(`${rideDir}${f}`);
          const chunk = JSON.parse(chunkStr);
          sensors.accelerometer.push(...chunk.accelerometer);
          sensors.gyroscope.push(...chunk.gyroscope);
        }
      }
    }

    return { meta, sensors };
  } catch {
    return null;
  }
}

/** Check if backend API is reachable */
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
