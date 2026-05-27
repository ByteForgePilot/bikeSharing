import { Audio } from "expo-av";

// Recording options — 16kHz mono for backend compatibility.
// NOTE: Android MediaRecorder does NOT support WAV/PCM output.
// On Android we record AAC in MPEG-4 container (.m4a); iOS records LINEARPCM (.wav).
const RECORDING_OPTIONS: Audio.RecordingOptions = {
  android: {
    extension: ".m4a",
    outputFormat: Audio.AndroidOutputFormat.MPEG_4,
    audioEncoder: Audio.AndroidAudioEncoder.AAC,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 128000,
  },
  ios: {
    extension: ".wav",
    outputFormat: Audio.IOSOutputFormat.LINEARPCM,
    audioQuality: Audio.IOSAudioQuality.MEDIUM,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 256000,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  web: {
    mimeType: "audio/wav",
    bitsPerSecond: 256000,
  },
};

class AudioRecorder {
  private recording: Audio.Recording | null = null;
  private isRecording = false;

  async isAvailable(): Promise<boolean> {
    try {
      const permission = await Audio.getPermissionsAsync();
      return permission.granted;
    } catch {
      return false;
    }
  }

  async start(): Promise<void> {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        throw new Error("Microphone permission denied");
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(RECORDING_OPTIONS);
      this.recording = recording;
      this.isRecording = true;
    } catch (error) {
      throw new Error(`Failed to start recording: ${error}`);
    }
  }

  async stop(): Promise<string | null> {
    if (!this.recording || !this.isRecording) return null;

    try {
      this.isRecording = false;
      await this.recording.stopAndUnloadAsync();
      const uri = this.recording.getURI();
      this.recording = null;
      return uri;
    } catch {
      this.recording = null;
      return null;
    }
  }

  getIsRecording(): boolean {
    return this.isRecording;
  }
}

export const audioRecorder = new AudioRecorder();
