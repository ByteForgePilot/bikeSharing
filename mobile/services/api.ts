const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

interface ApiOptions {
  method?: string;
  body?: unknown;
  token?: string;
}

export async function request<T = unknown>(
  endpoint: string,
  options: ApiOptions = {}
): Promise<T> {
  const { method = "GET", body, token } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API Error ${response.status}: ${error}`);
  }

  return response.json();
}

// --- Auth ---

export async function register(username: string, password: string) {
  return request("/api/auth/register", {
    method: "POST",
    body: { username, password },
  });
}

export async function login(username: string, password: string) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  const response = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData.toString(),
  });

  if (!response.ok) {
    throw new Error("Login failed");
  }
  return response.json() as Promise<{ access_token: string; token_type: string }>;
}

// --- Rides ---

export async function startRide(bikeId: string, lat: number, lng: number, token: string) {
  return request(`/api/rides/start?bike_id=${bikeId}&lat=${lat}&lng=${lng}`, {
    method: "POST",
    token,
  });
}

export async function endRide(rideId: number, lat: number, lng: number, token: string) {
  return request(`/api/rides/${rideId}/end?lat=${lat}&lng=${lng}`, {
    method: "POST",
    token,
  });
}

export async function uploadSensorData(
  rideId: number,
  accelerometer: Array<{ x: number; y: number; z: number; timestamp: number }>,
  gyroscope: Array<{ x: number; y: number; z: number; timestamp: number }>,
  timestamps: number[],
  token: string
) {
  return request(`/api/rides/${rideId}/sensor-data`, {
    method: "POST",
    body: { accelerometer, gyroscope, timestamps },
    token,
  });
}

// --- Detection ---

export async function detectWheelWobble(
  rideId: number,
  data: Array<{ x: number; y: number; z: number; timestamp: number }>,
  sampleRate: number,
  token: string
) {
  return request(`/api/detection/wheel-wobble/${rideId}`, {
    method: "POST",
    body: { accelerometer_data: data, sample_rate: sampleRate },
    token,
  });
}

export async function detectHandlebarMisalignment(
  rideId: number,
  data: Array<{ x: number; y: number; z: number; timestamp: number }>,
  sampleRate: number,
  token: string
) {
  return request(`/api/detection/handlebar/${rideId}`, {
    method: "POST",
    body: { gyroscope_data: data, sample_rate: sampleRate },
    token,
  });
}

export async function getDetectionReport(rideId: number, token: string) {
  return request(`/api/detection/report/${rideId}`, { token });
}
