// EditAudioModal.tsx
import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  Modal,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Platform,
} from "react-native";
import { Audio, AVPlaybackStatus } from "expo-av";
import * as DocumentPicker from "expo-document-picker";
import { MaterialIcons } from "@expo/vector-icons";
import * as FileSystem from "expo-file-system";
import { useWebSocket } from "../provider/WebSocketProvider";
import Toast from 'react-native-toast-message';

const kidFriendlySentences = [
  "The sun is shining so brightly today, and it feels like the perfect day to go outside and enjoy the warm weather together!",
  "My favorite animal in the whole world is a cute, fluffy bunny with long ears and a wiggly little nose.",
  "Let’s go outside and have some fun playing with the big, colorful ball that bounces so high into the air!",
  "The sky above us is so wonderfully blue, and it’s filled with the most beautiful, soft, fluffy white clouds floating by.",
  "I really love eating delicious ice cream, especially when it’s a warm and sunny day like this one—it tastes so good!",
];

const sampleSentences = [
  "Hello, how are you today?",
  "This is a sample sentence to test the TTS system.",
  "Let's see how well your audio works with this text.",
];

interface EditAudioModalProps {
  isVisible: boolean;
  onClose: () => void;
  button: { text: string; uri: string | null };
  onUpdate: (updatedButton: { text: string; uri: string | null }) => void;
}

const EditAudioModal: React.FC<EditAudioModalProps> = ({
  isVisible,
  onClose,
  button,
  onUpdate,
}) => {
  const [currentSentence, setCurrentSentence] = useState<string>(
    kidFriendlySentences[0]
  );
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [buttonText, setButtonText] = useState(button.text);
  const [serverUri, setServerUri] = useState<string | null>(button.uri);
  const [sound, setSound] = useState<Audio.Sound | null>(null);
  const [activeTab, setActiveTab] = useState<"record" | "upload">("record");
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isTTSSpeaking, setIsTTSSpeaking] = useState<boolean>(false);
  const [waitingForTTS, setWaitingForTTS] = useState<boolean>(false);

  // New States for TTS Playback
  const [ttsSound, setTTSSound] = useState<Audio.Sound | null>(null);
  const [currentTTSSentence, setCurrentTTSSentence] = useState<string | null>(null);
  const [ttsPlaying, setTtsPlaying] = useState<boolean>(false);
  const lastRequestedTTSSentenceRef = useRef<string | null>(null);

  // Access WebSocket context
  const { messages, sendMessage, connectionStatus } = useWebSocket();

  // Ref to track the last processed message
  const lastProcessedMessageRef = useRef<any>(null);

  // Ref to store the timeout ID for TTS waiting
  const ttsTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Effect to listen for UPLOAD_AUDIO_response and SYNTHESISE_response
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      
      // Check if this message has already been processed
      if (lastProcessedMessageRef.current !== lastMessage) {
        if (
          lastMessage.event === "UPLOAD_AUDIO_response" &&
          lastMessage.data.data.audio_url
        ) {
          setServerUri(lastMessage.data.data.audio_url);
          Toast.show({
            type: "success",
            text1: "Audio Uploaded",
            text2: "Your audio has been successfully uploaded.",
          });
        }

        if (
          lastMessage.event === "SYNTHESISE_response" &&
          lastMessage.data.data.audio_url &&
          waitingForTTS
        ) {
          setWaitingForTTS(false);
          if (ttsTimeoutRef.current) {
            clearTimeout(ttsTimeoutRef.current);
            ttsTimeoutRef.current = null;
          }

          const sentence = lastRequestedTTSSentenceRef.current;
          if (sentence) {
            playTTSAudio(lastMessage.data.data.audio_url, sentence);
          }

          Toast.show({
            type: "success",
            text1: "TTS Audio Generated",
            text2: "Playing the generated audio.",
          });
        }

        if (lastMessage.error) {
          Toast.show({
            type: "error",
            text1: "Error",
            text2: lastMessage.error,
          });
        }

        // Update the ref to mark this message as processed
        lastProcessedMessageRef.current = lastMessage;
      }
    }
  }, [messages]);

  // Effect to handle TTS timeout
  useEffect(() => {
    if (waitingForTTS) {
      // Start a 10-second timer
      ttsTimeoutRef.current = setTimeout(() => {
        setWaitingForTTS(false);
        Toast.show({
          type: "error",
          text1: "TTS Timeout",
          text2: "TTS generation is taking longer than expected. Please try again.",
        });
      }, 10000); // 10,000 milliseconds = 10 seconds
    }

    // Cleanup function to clear the timeout if waitingForTTS changes
    return () => {
      if (ttsTimeoutRef.current) {
        clearTimeout(ttsTimeoutRef.current);
        ttsTimeoutRef.current = null;
      }
    };
  }, [waitingForTTS]);

  // Separate playback status handler for TTS audio
  const onTTSSoundPlaybackStatusUpdate = (status: AVPlaybackStatus) => {
    if (status.isLoaded) {
      if (status.didJustFinish && !status.isLooping) {
        setTtsPlaying(false);
        setIsTTSSpeaking(false);
        ttsSound?.unloadAsync();
        setTTSSound(null);
        setCurrentTTSSentence(null);
      }
    }
  };

  const playTTSAudio = async (audioUrl: string, sentence: string) => {
    try {
      const { sound: newTTSSound } = await Audio.Sound.createAsync(
        { uri: audioUrl },
        {},
        onTTSSoundPlaybackStatusUpdate
      );
      setTTSSound(newTTSSound);
      setTtsPlaying(true);
      setCurrentTTSSentence(sentence);
      setIsTTSSpeaking(true);
      await newTTSSound.playAsync();
    } catch (error) {
      console.error("Error playing TTS audio:", error);
      Toast.show({
        type: "error",
        text1: "Error",
        text2: "Failed to play TTS audio.",
      });
    }
  };

  // Playback status update handler for main audio
  const onPlaybackStatusUpdate = (status: AVPlaybackStatus) => {
    if (status.isLoaded) {
      if (status.didJustFinish && !status.isLooping) {
        setIsPlaying(false);
        setSound(null);
      }
    }
  };

  // Cleanup main audio on unmount or when sound changes
  useEffect(() => {
    return () => {
      sound?.unloadAsync();
    };
  }, [sound]);

  // Cleanup TTS audio on unmount or when ttsSound changes
  useEffect(() => {
    return () => {
      ttsSound?.unloadAsync();
    };
  }, [ttsSound]);

  useEffect(() => {
    loadNewSentence();
  }, []);

  const loadNewSentence = () => {
    const newSentence =
      kidFriendlySentences[Math.floor(Math.random() * kidFriendlySentences.length)];
    setCurrentSentence(newSentence);
  };

  const handleStartRecording = async () => {
    try {
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) {
        Toast.show({
          type: "error",
          text1: "Permission Denied",
          text2: "We need permission to record.",
        });
        return;
      }
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(recording);
      setIsRecording(true);
    } catch (error) {
      console.error(error);
      Toast.show({
        type: "error",
        text1: "Oops!",
        text2: "We couldn't start recording. Try again.",
      });
    }
  };

  const handleStopRecording = async () => {
    try {
      await recording?.stopAndUnloadAsync();
      const uri = recording?.getURI();
      if (uri) {
        if (Platform.OS === "web") {
          // Web-specific handling
          fetch(uri)
            .then((response) => response.blob())
            .then((blob) => {
              const reader = new FileReader();
              reader.onloadend = () => {
                const base64Audio = (reader.result as string).split(",")[1];
                const message = {
                  audio: base64Audio,
                  filename: `audio_${Date.now()}.wav`,
                };
                sendMessage("UPLOAD_AUDIO", { data: message });
              };
              reader.readAsDataURL(blob);
            })
            .catch((error) => {
              console.error(error);
              Toast.show({
                type: "error",
                text1: "Error",
                text2: "Failed to process recorded audio.",
              });
            });
        } else {
          // Native handling
          const base64Audio = await FileSystem.readAsStringAsync(uri, {
            encoding: FileSystem.EncodingType.Base64,
          });

          const message = {
            audio: base64Audio,
            filename: `audio_${Date.now()}.wav`,
          };

          sendMessage("UPLOAD_AUDIO", { data: message });
        }
      }
      setRecording(null);
      setIsRecording(false);
    } catch (error) {
      console.error(error);
      Toast.show({
        type: "error",
        text1: "Oops!",
        text2: "We couldn't stop recording. Try again.",
      });
    }
  };

  const handleUploadAudio = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({ type: "audio/*" });
      if (result.type === "success" && result.uri) {
        if (Platform.OS === "web") {
          // Web-specific handling
          fetch(result.uri)
            .then((response) => response.blob())
            .then((blob) => {
              const reader = new FileReader();
              reader.onloadend = () => {
                const base64Audio = (reader.result as string).split(",")[1];
                const message = {
                  audio: base64Audio,
                  filename: `upload_${Date.now()}.wav`,
                };
                sendMessage("UPLOAD_AUDIO", { data: message });
              };
              reader.readAsDataURL(blob);
            })
            .catch((error) => {
              console.error(error);
              Toast.show({
                type: "error",
                text1: "Error",
                text2: "Failed to process selected audio.",
              });
            });
        } else {
          // Native handling
          const base64Audio = await FileSystem.readAsStringAsync(result.uri, {
            encoding: FileSystem.EncodingType.Base64,
          });

          const message = {
            audio: base64Audio,
            filename: `upload_${Date.now()}.wav`,
          };

          sendMessage("UPLOAD_AUDIO", { data: message });
        }
      }
    } catch (error) {
      console.error("Failed to upload audio.", error);
      Toast.show({
        type: "error",
        text1: "Error",
        text2: "Failed to upload audio.",
      });
    }
  };

  const handleSave = () => {
    onUpdate({ text: buttonText, uri: serverUri });
    onClose();
    // Reset states when closing the modal via Save
    resetModalStates();
  };

  const resetModalStates = async () => {
    // Stop and unload any playing main audio
    if (sound) {
      try {
        await sound.stopAsync();
        await sound.unloadAsync();
      } catch (error) {
        console.error("Error unloading sound:", error);
      }
    }
    setSound(null);
    setIsPlaying(false);

    // Stop and unload any playing TTS audio
    if (ttsSound) {
      try {
        await ttsSound.stopAsync();
        await ttsSound.unloadAsync();
      } catch (error) {
        console.error("Error unloading TTS sound:", error);
      }
    }
    setTTSSound(null);
    setTtsPlaying(false);
    setIsTTSSpeaking(false);
    setCurrentTTSSentence(null);
    lastRequestedTTSSentenceRef.current = null;

    // Reset WebSocket-related states
    lastProcessedMessageRef.current = null;
    setWaitingForTTS(false);

    // Clear any existing TTS timeout
    if (ttsTimeoutRef.current) {
      clearTimeout(ttsTimeoutRef.current);
      ttsTimeoutRef.current = null;
    }
  };

  // Reset states when modal is closed via Close button or other means
  useEffect(() => {
    if (!isVisible) {
      resetModalStates();
    }
  }, [isVisible]);

  const handleTestTTSSentence = (sentence: string) => {
    if (currentTTSSentence === sentence) {
      if (ttsPlaying) {
        // Pause TTS
        ttsSound?.pauseAsync();
        setTtsPlaying(false);
        Toast.show({
          type: "info",
          text1: "TTS Paused",
          text2: "Paused the TTS audio.",
        });
      } else {
        // Resume TTS
        ttsSound?.playAsync();
        setTtsPlaying(true);
        Toast.show({
          type: "success",
          text1: "TTS Resumed",
          text2: "Resumed the TTS audio.",
        });
      }
    } else {
      // If another TTS audio is playing, stop it
      if (ttsSound) {
        ttsSound.stopAsync();
        ttsSound.unloadAsync();
        setTTSSound(null);
        setTtsPlaying(false);
        setCurrentTTSSentence(null);
      }

      if (!connectionStatus) {
        Toast.show({
          type: "error",
          text1: "WebSocket Disconnected",
          text2: "Please wait while the connection is re-established.",
        });
        return;
      }

      if (!serverUri) {
        Toast.show({
          type: "error",
          text1: "No Audio",
          text2: "Please record or upload an audio clip first.",
        });
        return;
      }

      if (!sentence.trim()) {
        Toast.show({
          type: "error",
          text1: "No Text",
          text2: "Please select a valid sentence.",
        });
        return;
      }

      // Send TTS request
      const message = {
        data: {
          audio_file: serverUri, // Assuming serverUri is the URL or Base64-encoded audio
          text: sentence,
        },
      };

      // Track the requested sentence
      lastRequestedTTSSentenceRef.current = sentence;

      sendMessage("SYNTHESISE", message);
      setWaitingForTTS(true);

      Toast.show({
        type: "info",
        text1: "Generating TTS Audio",
        text2: "Please wait while the audio is being generated...",
      });
    }
  };

  // Function to toggle play/pause for main audio
  const togglePlayPause = async () => {
    if (sound) {
      const status = await sound.getStatusAsync();
      if (status.isLoaded && status.isPlaying) {
        await sound.pauseAsync();
        setIsPlaying(false);
      } else {
        await sound.playAsync();
        setIsPlaying(true);
      }
    } else if (serverUri) {
      try {
        const { sound: newSound } = await Audio.Sound.createAsync(
          { uri: serverUri },
          { shouldPlay: true },
          onPlaybackStatusUpdate
        );
        setSound(newSound);
        setIsPlaying(true);
      } catch {
        Toast.show({
          type: "error",
          text1: "Error",
          text2: "Failed to play audio.",
        });
      }
    } else {
      Toast.show({
        type: "error",
        text1: "No Audio",
        text2: "This button has no audio.",
      });
    }
  };

  return (
    <Modal visible={isVisible} transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={styles.modalContent}>
          <ScrollView contentContainerStyle={styles.scrollContent}>
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.modalTitle}>Edit Button</Text>
              <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                <MaterialIcons name="close" size={30} color="#000" />
              </TouchableOpacity>
            </View>

            {/* Tabs */}
            <View style={styles.tabsContainer}>
              <TouchableOpacity
                style={[styles.tab, activeTab === "record" && styles.activeTab]}
                onPress={() => setActiveTab("record")}
              >
                <Text
                  style={[
                    styles.tabText,
                    activeTab === "record" && styles.activeTabText,
                  ]}
                >
                  Record
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.tab, activeTab === "upload" && styles.activeTab]}
                onPress={() => setActiveTab("upload")}
              >
                <Text
                  style={[
                    styles.tabText,
                    activeTab === "upload" && styles.activeTabText,
                  ]}
                >
                  Upload
                </Text>
              </TouchableOpacity>
            </View>

            {/* Content */}
            <View style={styles.content}>
              <TextInput
                style={styles.textInput}
                value={buttonText}
                onChangeText={setButtonText}
                placeholder="Button Title"
              />

              {activeTab === "record" && (
                <>
                  <Text style={styles.sentenceText}>{currentSentence}</Text>
                  <TouchableOpacity
                    style={styles.nextButton}
                    onPress={loadNewSentence}
                  >
                    <Text style={styles.buttonText}>Next Sentence</Text>
                  </TouchableOpacity>

                  <View style={styles.recordContainer}>
                    <TouchableOpacity
                      style={[
                        styles.recordButton,
                        isRecording && styles.recordButtonActive,
                      ]}
                      onPress={
                        isRecording ? handleStopRecording : handleStartRecording
                      }
                    >
                      <MaterialIcons
                        name={isRecording ? "stop" : "mic"}
                        size={40}
                        color="#fff"
                      />
                    </TouchableOpacity>
                  </View>
                </>
              )}

              {activeTab === "upload" && (
                <TouchableOpacity
                  style={styles.uploadButton}
                  onPress={handleUploadAudio}
                >
                  <MaterialIcons name="upload" size={30} color="#fff" />
                  <Text style={styles.uploadButtonText}>Upload Audio</Text>
                </TouchableOpacity>
              )}

              {/* Main Play/Pause Button */}
              {serverUri && (
                <TouchableOpacity
                  style={[
                    styles.playButton,
                    isPlaying && styles.playButtonActive,
                  ]}
                  onPress={togglePlayPause}
                >
                  <MaterialIcons
                    name={isPlaying ? "pause" : "play-arrow"}
                    size={30}
                    color="#fff"
                  />
                </TouchableOpacity>
              )}

              {/* Sample Sentences for TTS Testing */}
              <View style={styles.sampleSection}>
                <Text style={styles.sampleTitle}>Test Your Audio with TTS</Text>
                {sampleSentences.map((sentence, index) => (
                  <View key={index} style={styles.sampleRow}>
                    <Text style={styles.sampleText}>{sentence}</Text>
                    <TouchableOpacity
                      style={[
                        styles.samplePlayButton,
                        (!serverUri || waitingForTTS || isTTSSpeaking) && styles.samplePlayButtonDisabled,
                      ]}
                      onPress={() => handleTestTTSSentence(sentence)}
                      disabled={!serverUri || waitingForTTS || isTTSSpeaking}
                    >
                      <MaterialIcons
                        name={
                          currentTTSSentence === sentence
                            ? ttsPlaying
                              ? "pause"
                              : "play-arrow"
                            : "play-arrow"
                        }
                        size={24}
                        color={
                          currentTTSSentence === sentence && ttsPlaying
                            ? "#fff"
                            : serverUri
                            ? "#fff"
                            : "#aaa"
                        }
                      />
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            </View>

            {/* Footer */}
            <View style={styles.footer}>
              <TouchableOpacity style={styles.saveButton} onPress={handleSave}>
                <MaterialIcons name="save" size={30} color="#4caf50" />
                <Text style={styles.saveButtonText}>Save</Text>
              </TouchableOpacity>
            </View>
          </ScrollView>
        </View>
      </View>
      <Toast />
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.7)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalContent: {
    backgroundColor: "#fff",
    paddingVertical: 20,
    paddingHorizontal: 15,
    borderRadius: 15,
    width: "90%",
    maxHeight: "90%",
  },
  scrollContent: {
    flexGrow: 1,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: "bold",
    color: "#333",
  },
  closeButton: {
    padding: 5,
  },
  tabsContainer: {
    flexDirection: "row",
    marginTop: 20,
    marginBottom: 10,
    borderRadius: 8,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "#ccc",
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    backgroundColor: "#f5f5f5",
    alignItems: "center",
  },
  activeTab: {
    backgroundColor: "#2196f3",
  },
  tabText: {
    fontSize: 16,
    color: "#333",
  },
  activeTabText: {
    color: "#fff",
    fontWeight: "bold",
  },
  content: {
    alignItems: "center",
    marginTop: 10,
  },
  textInput: {
    width: "100%",
    borderWidth: 1,
    borderColor: "#ccc",
    padding: 10,
    borderRadius: 8,
    marginBottom: 20,
    fontSize: 16,
  },
  sentenceText: {
    fontSize: 18,
    fontWeight: "600",
    color: "#333",
    textAlign: "center",
    marginBottom: 10,
  },
  nextButton: {
    backgroundColor: "#2196f3",
    padding: 10,
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 20,
    width: "100%",
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
  },
  recordContainer: {
    flexDirection: "row",
    justifyContent: "center",
    marginBottom: 20,
  },
  recordButton: {
    backgroundColor: "#4caf50",
    padding: 15,
    borderRadius: 50,
    marginHorizontal: 10,
  },
  recordButtonActive: {
    backgroundColor: "#f44336",
  },
  uploadButton: {
    flexDirection: "row",
    backgroundColor: "#2196f3",
    padding: 12,
    borderRadius: 8,
    alignItems: "center",
    marginBottom: 20,
    width: "100%",
    justifyContent: "center",
  },
  uploadButtonText: {
    color: "#fff",
    fontSize: 16,
    marginLeft: 10,
  },
  playButton: {
    backgroundColor: "#4caf50",
    borderRadius: 50,
    padding: 15,
    justifyContent: "center",
    alignItems: "center",
    marginTop: 10,
    marginBottom: 20,
  },
  playButtonActive: {
    backgroundColor: "#2196f3",
  },
  sampleSection: {
    width: "100%",
    marginTop: 20,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: "#ccc",
  },
  sampleTitle: {
    fontSize: 18,
    fontWeight: "bold",
    color: "#333",
    marginBottom: 10,
    textAlign: "center",
  },
  sampleRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 10,
  },
  sampleText: {
    flex: 1,
    fontSize: 16,
    color: "#555",
  },
  samplePlayButton: {
    backgroundColor: "#2196f3",
    borderRadius: 25,
    padding: 8,
  },
  samplePlayButtonDisabled: {
    backgroundColor: "#ccc",
  },
  footer: {
    alignItems: "flex-end",
    marginTop: 10,
  },
  saveButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#e8f5e9",
    paddingVertical: 12,
    paddingHorizontal: 25,
    borderRadius: 10,
  },
  saveButtonText: {
    fontSize: 20,
    color: "#4caf50",
    marginLeft: 10,
    fontWeight: "bold",
  },
});

export default EditAudioModal;
