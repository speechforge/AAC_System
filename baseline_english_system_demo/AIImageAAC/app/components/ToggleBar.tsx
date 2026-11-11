import React, { useState } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";

interface ToggleBarProps {
    buttons: { text: string; uri: string | null }[];
    onToggle: (index: number) => void;
  selectedButtonIndex: number ;
  onOpenSettings: () => void;
}

const ToggleBar: React.FC<ToggleBarProps> = ({
  buttons,
  onToggle,
  selectedButtonIndex,
  onOpenSettings,
}) => {
  return (
    <View style={styles.container}>
      {buttons.map((label, index) => (
        <TouchableOpacity
          key={index}
          style={[
            styles.button,
            selectedButtonIndex === index && styles.toggledButton,
          ]}
          onPress={() => onToggle(index)}
        >
          <Text style={styles.buttonText}>{label.text}</Text>
        </TouchableOpacity>
      ))}
      <TouchableOpacity style={styles.settingsButton} onPress={onOpenSettings}>
        <Text style={styles.settingsIcon}>⚙️</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    backgroundColor: "#000",
    paddingVertical: 5,
    alignItems: "center",
  },
  button: {
    flex: 1,
    backgroundColor: "#333",
    paddingVertical: 10,
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#555",
  },
  toggledButton: {
    backgroundColor: "#555",
  },
  buttonText: {
    color: "#fff",
    fontSize: 16,
    textAlign: "center",
  },
  settingsButton: {
    width: 50,
    backgroundColor: "#444",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#555",
  },
  settingsIcon: {
    color: "#fff",
    fontSize: 20,
  },
});

export default ToggleBar;
