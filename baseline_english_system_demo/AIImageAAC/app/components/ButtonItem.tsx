// ButtonItem.tsx
import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
} from "react-native";
import { MaterialIcons } from "@expo/vector-icons";
import { Audio } from "expo-av";

interface ButtonItemProps {
  index: number;
  button: { text: string; uri: string | null };
  boxSize: number;
  boxMargin: number;
  onEdit: () => void;
  onDelete: (index: number) => void;
}

const ButtonItem: React.FC<ButtonItemProps> = ({
  index,
  button,
  boxSize,
  boxMargin,
  onEdit,
  onDelete,
}) => {
  const [sound, setSound] = React.useState<Audio.Sound | null>(null);

  const playAudio = async () => {
    if (button.uri) {
      try {
        const { sound } = await Audio.Sound.createAsync({ uri: button.uri });
        setSound(sound);
        await sound.playAsync();
      } catch {
        Alert.alert("Error", "Failed to play audio.");
      }
    } else {
      Alert.alert("No Audio", "This button has no audio.");
    }
  };

  React.useEffect(() => {
    return sound
      ? () => {
          sound.unloadAsync();
        }
      : undefined;
  }, [sound]);

  return (
    <View
      style={[
        styles.container,
        {
          width: boxSize,
          height: boxSize,
          margin: boxMargin / 2,
        },
      ]}
    >
      <Text style={styles.title} numberOfLines={1}>
        {button.text}
      </Text>

      <TouchableOpacity style={styles.playButton} onPress={playAudio}>
        <MaterialIcons name="play-arrow" size={60} color="#fff" />
      </TouchableOpacity>

      <View style={styles.actionContainer}>
        <TouchableOpacity onPress={onEdit} style={styles.actionButton}>
          <MaterialIcons name="edit" size={60} color="#2196f3" />
        </TouchableOpacity>
        <TouchableOpacity
          onPress={() => onDelete(index)}
          style={styles.actionButton}
        >
          <MaterialIcons name="delete" size={60} color="#f44336" />
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: "#f0f0f0",
    borderRadius: 10,
    padding: 5,
    justifyContent: "space-between",
    alignItems: "center",
  },
  title: {
    fontSize: 14,
    fontWeight: "600",
    color: "#333",
    textAlign: "center",
    marginBottom: 5,
  },
  playButton: {
    backgroundColor: "#4caf50",
    borderRadius: 50,
    padding: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  actionContainer: {
    flexDirection: "row",
    marginTop: 5,
  },
  actionButton: {
    marginHorizontal: 5,
  },
});

export default ButtonItem;
