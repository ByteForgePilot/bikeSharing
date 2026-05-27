import { Accelerometer, Gyroscope } from "expo-sensors";
import * as Location from "expo-location";

interface Subscription {
  remove: () => void;
}

export interface SensorDataPoint {
  x: number;
  y: number;
  z: number;
  timestamp: number;
}

export interface GPSDataPoint {
  lat: number;
  lng: number;
  altitude: number | null;
  accuracy: number | null;
  timestamp: number;
}

export interface SensorBuffer {
  accelerometer: SensorDataPoint[];
  gyroscope: SensorDataPoint[];
  gps: GPSDataPoint[];
  sampleCount: number;
}

const SENSOR_INTERVAL_MS = 50;   // 20 Hz
const GPS_INTERVAL_MS = 1000;    // 1 Hz
const BUFFER_FLUSH_SIZE = 100;   // flush every 100 accel samples

class SensorCollector {
  private accelBuffer: SensorDataPoint[] = [];
  private gyroBuffer: SensorDataPoint[] = [];
  private gpsBuffer: GPSDataPoint[] = [];
  private accelSub: Subscription | null = null;
  private gyroSub: Subscription | null = null;
  private gpsSub: Subscription | null = null;
  private onFlush: ((buffer: SensorBuffer) => void) | null = null;
  private lastGPS: GPSDataPoint | null = null;
  private isRunning = false;
  private gpsStatus: "denied" | "searching" | "locked" = "searching";

  // Per-sample values for real-time UI — updated on every sensor event
  latestAccel: SensorDataPoint | null = null;
  latestGyro: SensorDataPoint | null = null;
  eventCount = 0;

  get latestGPS(): GPSDataPoint | null {
    return this.lastGPS;
  }

  get currentGPSStatus(): "denied" | "searching" | "locked" {
    return this.gpsStatus;
  }

  async start(onFlush: (buffer: SensorBuffer) => void): Promise<void> {
    // If already running, just swap the callback — don't clear buffers or restart subscriptions
    if (this.isRunning) {
      this.onFlush = onFlush;
      return;
    }

    this.onFlush = onFlush;
    this.accelBuffer = [];
    this.gyroBuffer = [];
    this.gpsBuffer = [];
    this.latestAccel = null;
    this.latestGyro = null;
    this.eventCount = 0;
    this.isRunning = true;

    Accelerometer.setUpdateInterval(SENSOR_INTERVAL_MS);
    Gyroscope.setUpdateInterval(SENSOR_INTERVAL_MS);

    this.accelSub = Accelerometer.addListener((data) => {
      const point: SensorDataPoint = { x: data.x, y: data.y, z: data.z, timestamp: Date.now() };
      this.latestAccel = point;
      this.eventCount++;
      this.accelBuffer.push(point);
      if (this.accelBuffer.length >= BUFFER_FLUSH_SIZE) {
        this.flush();
      }
    });

    this.gyroSub = Gyroscope.addListener((data) => {
      const point: SensorDataPoint = { x: data.x, y: data.y, z: data.z, timestamp: Date.now() };
      this.latestGyro = point;
      this.gyroBuffer.push(point);
    });

    // GPS: 1Hz via expo-location
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status === "granted") {
      this.gpsStatus = "searching";
      this.gpsSub = await Location.watchPositionAsync(
        { accuracy: Location.Accuracy.High, timeInterval: GPS_INTERVAL_MS, distanceInterval: 1 },
        (loc) => {
          const point: GPSDataPoint = {
            lat: loc.coords.latitude,
            lng: loc.coords.longitude,
            altitude: loc.coords.altitude,
            accuracy: loc.coords.accuracy,
            timestamp: loc.timestamp,
          };
          this.gpsBuffer.push(point);
          this.lastGPS = point;
          this.gpsStatus = "locked";
        }
      );
    } else {
      this.gpsStatus = "denied";
    }
  }

  stop(): SensorBuffer {
    // Idempotent — only first call does work, prevents double-flush across
    // handleEndRide / handleGoBack / effect-cleanup call sites
    if (!this.isRunning) {
      return { accelerometer: [], gyroscope: [], gps: [], sampleCount: 0 };
    }
    this.isRunning = false;

    // Remove individual subscriptions
    this.accelSub?.remove();
    this.gyroSub?.remove();
    this.gpsSub?.remove();
    this.accelSub = null;
    this.gyroSub = null;
    this.gpsSub = null;

    // Thorough native cleanup — prevents listener leaks across rides
    Accelerometer.removeAllListeners();
    Gyroscope.removeAllListeners();

    // Snapshot then clear internal buffers so stale data can't be re-flushed
    const finalBuffer: SensorBuffer = {
      accelerometer: [...this.accelBuffer],
      gyroscope: [...this.gyroBuffer],
      gps: [...this.gpsBuffer],
      sampleCount: Math.max(this.accelBuffer.length, this.gyroBuffer.length),
    };
    this.accelBuffer = [];
    this.gyroBuffer = [];
    this.gpsBuffer = [];
    this.latestAccel = null;
    this.latestGyro = null;
    this.eventCount = 0;

    if (this.onFlush && finalBuffer.sampleCount > 0) {
      this.onFlush(finalBuffer);
    }

    return finalBuffer;
  }

  private flush(): void {
    if (!this.onFlush || this.accelBuffer.length === 0) return;

    // Take all available data from each buffer — accel triggers the flush,
    // but we carry along whatever gyro/gps has accumulated so far
    const accelChunk = this.accelBuffer.splice(0);
    const gyroChunk = this.gyroBuffer.splice(0);
    const gpsChunk = this.gpsBuffer.splice(0);

    this.onFlush({
      accelerometer: accelChunk,
      gyroscope: gyroChunk,
      gps: gpsChunk,
      sampleCount: accelChunk.length,
    });
  }
}

export const sensorCollector = new SensorCollector();

export async function checkSensorsAvailable(): Promise<{
  accelerometer: boolean;
  gyroscope: boolean;
}> {
  const [accelAvail, gyroAvail] = await Promise.all([
    Accelerometer.isAvailableAsync(),
    Gyroscope.isAvailableAsync(),
  ]);
  return { accelerometer: accelAvail, gyroscope: gyroAvail };
}
