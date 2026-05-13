import { Accelerometer, Gyroscope } from "expo-sensors";
import type { Subscription } from "expo-sensors";

export interface SensorDataPoint {
  x: number;
  y: number;
  z: number;
  timestamp: number;
}

export interface SensorBuffer {
  accelerometer: SensorDataPoint[];
  gyroscope: SensorDataPoint[];
  sampleCount: number;
}

const DEFAULT_INTERVAL_MS = 50; // 20 Hz
const BUFFER_FLUSH_SIZE = 100; // Flush to API every 100 samples

class SensorCollector {
  private accelBuffer: SensorDataPoint[] = [];
  private gyroBuffer: SensorDataPoint[] = [];
  private accelSub: Subscription | null = null;
  private gyroSub: Subscription | null = null;
  private onFlush: ((buffer: SensorBuffer) => void) | null = null;

  start(onFlush: (buffer: SensorBuffer) => void): void {
    this.onFlush = onFlush;
    this.accelBuffer = [];
    this.gyroBuffer = [];

    Accelerometer.setUpdateInterval(DEFAULT_INTERVAL_MS);
    Gyroscope.setUpdateInterval(DEFAULT_INTERVAL_MS);

    this.accelSub = Accelerometer.addListener((data) => {
      this.accelBuffer.push({
        x: data.x,
        y: data.y,
        z: data.z,
        timestamp: Date.now(),
      });
      if (this.accelBuffer.length >= BUFFER_FLUSH_SIZE) {
        this.flush();
      }
    });

    this.gyroSub = Gyroscope.addListener((data) => {
      this.gyroBuffer.push({
        x: data.x,
        y: data.y,
        z: data.z,
        timestamp: Date.now(),
      });
    });
  }

  stop(): SensorBuffer {
    this.accelSub?.remove();
    this.gyroSub?.remove();
    this.accelSub = null;
    this.gyroSub = null;

    // Flush remaining data
    const finalBuffer: SensorBuffer = {
      accelerometer: [...this.accelBuffer],
      gyroscope: [...this.gyroBuffer],
      sampleCount: Math.max(this.accelBuffer.length, this.gyroBuffer.length),
    };

    if (this.onFlush && finalBuffer.sampleCount > 0) {
      this.onFlush(finalBuffer);
    }

    return finalBuffer;
  }

  private flush(): void {
    if (this.onFlush && this.accelBuffer.length > 0) {
      this.onFlush({
        accelerometer: this.accelBuffer.splice(0),
        gyroscope: this.gyroBuffer.splice(0),
        sampleCount: BUFFER_FLUSH_SIZE,
      });
    }
  }
}

export const sensorCollector = new SensorCollector();

/** Check if sensors are available on this device */
export async function checkSensorsAvailable(): Promise<{
  accelerometer: boolean;
  gyroscope: boolean;
}> {
  const [accelAvail, gyroAvail] = await Promise.all([
    Accelerometer.isAvailableAsync(),
    Gyroscope.isAvailableAsync(),
  ]);
  return {
    accelerometer: accelAvail,
    gyroscope: gyroAvail,
  };
}
