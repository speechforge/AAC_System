// GenericBox.tsx
import React from "react";
import { StyleSheet, TouchableOpacity, ViewStyle, Text } from "react-native";
import { MaterialIcons } from "@expo/vector-icons"; // For the "X" icon

interface GenericBoxProps {
  boxSize: number;
  margin: number;
  onPress: () => void;
  onLongPress?: () => void; // Optional onLongPress handler
  delayLongPress?: number; // Optional delay for long press
  label?: string; // Optional label for the box
  iconName?: string; // Optional Material Icon name
  boxStyle?: ViewStyle; // Customizable box style
  labelStyle?: ViewStyle; // Customizable label style
}

const GenericBox: React.FC<GenericBoxProps> = ({
  boxSize,
  margin,
  onPress,
  onLongPress,
  label = "+",
  iconName,
  boxStyle,
  labelStyle,
}) => {
  return (
    <TouchableOpacity
      style={[
        styles.box,
        { width: boxSize, height: boxSize, margin: margin / 2 },
        boxStyle,
      ]}
      onPress={onPress}
      onLongPress={onLongPress}
      delayLongPress={onLongPress ? 5000 : undefined}
    >
      {iconName ? (
        <MaterialIcons name={iconName} size={boxSize / 2} color="white" style={[styles.icon, labelStyle]}/>
      ) : (
        <Text style={[styles.label]}>{label}</Text>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  box: {
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#e0e0e0",
    borderRadius: 4,
    borderColor: "#aaa",
    borderWidth: 1,
  },
  label: {
    fontSize: 128,
    fontWeight: "bold",
    color: "#555",
  },
  icon: {
    color: "#555",
  },
});

export default GenericBox;
