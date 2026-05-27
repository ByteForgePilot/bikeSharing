/** Lightweight on-device fault pre-screening. Pure JS, O(n), microseconds. */

export interface QuickAlert {
  type: "wheel_wobble" | "chain_noise" | "handlebar";
  level: "warning";
  value: number;
  threshold: number;
  timestamp: number;
}

export function quickWheelCheck(
  accelData: Array<{ x: number; y: number; z: number }>,
  threshold: number = 2.0
): QuickAlert | null {
  if (accelData.length === 0) return null;
  let sumSq = 0;
  for (const a of accelData) {
    sumSq += a.x * a.x;
  }
  const rms = Math.sqrt(sumSq / accelData.length);
  if (rms > threshold) {
    return { type: "wheel_wobble", level: "warning", value: rms, threshold, timestamp: Date.now() };
  }
  return null;
}

export function quickHandlebarCheck(
  gyroData: Array<{ x: number; y: number; z: number }>,
  thresholdRad: number = 0.05
): QuickAlert | null {
  if (gyroData.length === 0) return null;
  let sum = 0;
  for (const g of gyroData) {
    sum += g.z;
  }
  const meanZ = sum / gyroData.length;
  const offset = Math.abs(meanZ);
  if (offset > thresholdRad) {
    return { type: "handlebar", level: "warning", value: offset, threshold: thresholdRad, timestamp: Date.now() };
  }
  return null;
}
