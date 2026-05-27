import * as api from "./api";
import * as offlineStorage from "./offlineStorage";

export interface SyncResult {
  uploaded: number;
  failed: number;
}

export async function syncPendingRides(token: string): Promise<SyncResult> {
  const rides = await offlineStorage.listRides();
  let uploaded = 0;
  let failed = 0;

  for (const ride of rides) {
    if (ride.status !== "completed") continue;

    try {
      const data = await offlineStorage.getRide(ride.rideId);
      if (!data) continue;

      await offlineStorage.setSyncStatus(ride.rideId, "syncing");

      // Parse rideId: offline rides have format "timestamp_bikeId"
      const numericId = parseInt(ride.rideId, 10);
      const useOnlineId = !isNaN(numericId);

      // 1. Upload sensor data
      if (data.sensors.accelerometer.length > 0) {
        if (useOnlineId) {
          await api.uploadSensorData(
            numericId,
            data.sensors.accelerometer,
            data.sensors.gyroscope,
            data.sensors.gps,
            data.sensors.sampleRate,
            token
          );
        }
      }

      // 2. Upload audio if available
      const hasAudio = (data.meta as any).hasAudio;
      if (hasAudio && useOnlineId) {
        const audioUri = `${offlineStorage.RIDES_DIR}${ride.rideId}/audio_recording.wav`;
        try {
          await api.uploadAudioFile(numericId, audioUri, token);
        } catch {
          // audio upload is non-critical
        }
      }

      // 3. Run detections (online rides only)
      if (useOnlineId && data.sensors.accelerometer.length > 0) {
        try {
          await api.detectWheelWobble(numericId, data.sensors.accelerometer, data.sensors.sampleRate, token);
        } catch { /* non-critical */ }
        try {
          const features = data.sensors.accelerometer.map(
            (d) => Math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
          );
          await api.detectChainNoise(numericId, features, token);
        } catch { /* non-critical */ }
      }
      if (useOnlineId && data.sensors.gyroscope.length > 0) {
        try {
          await api.detectHandlebarMisalignment(numericId, data.sensors.gyroscope, data.sensors.sampleRate, token);
        } catch { /* non-critical */ }
      }

      // 4. End ride on server if it was started there
      if (useOnlineId) {
        const gpsData = data.sensors.gps;
        const endLat = gpsData.length > 0 ? gpsData[gpsData.length - 1].lat : 0;
        const endLng = gpsData.length > 0 ? gpsData[gpsData.length - 1].lng : 0;
        try {
          await api.endRide(numericId, endLat, endLng, token);
        } catch { /* might already be ended */ }
      }

      // 5. Clean up local files
      await offlineStorage.deleteRide(ride.rideId);
      uploaded++;
    } catch {
      await offlineStorage.setSyncStatus(ride.rideId, "failed");
      failed++;
    }
  }

  return { uploaded, failed };
}
