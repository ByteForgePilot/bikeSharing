import { Audio } from "expo-av";
import type { Recording } from "expo-av";

class AudioRecorder {
  private recording: Recording | null = null;
  private isRecording = false;

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

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      this.recording = recording;
      this.isRecording = true;
    } catch (error) {
      throw new Error(`Failed to start recording: ${error}`);
    }
  }

  async stop(): Promise<string | null> {
    if (!this.recording) return null;

    try {
      await this.recording.stopAndUnloadAsync();
      const uri = this.recording.getURI();
      this.recording = null;
      this.isRecording = false;
      return uri;
    } catch (error) {
      this.isRecording = false;
      return null;
    }
  }

  getIsRecording(): boolean {
    return this.isRecording;
  }
}

export const audioRecorder = new AudioRecorder();
