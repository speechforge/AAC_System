import React, { useRef, useEffect, useState } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  Animated,
  View,
  Image,
} from "react-native";
import { MaterialIcons } from "@expo/vector-icons"; // For the "X" icon
import { BoxInfo } from "../types";
import AsyncStorage from "@react-native-async-storage/async-storage";

interface BoxProps {
  id: number;
  size: number;
  margin: number;
  selected: boolean;
  boxInfo: BoxInfo;
  onSelect: (id: number | null) => void;
  onLongSelect: (id: number) => void;
  delayLongPress: number;
  lockEditing: boolean;
  onDelete: (id: number) => void;
  onEdit: (id: number) => void;
}

const WordBox: React.FC<BoxProps> = ({
  id,
  size,
  margin,
  selected,
  onSelect,
  onLongSelect,
  delayLongPress,
  lockEditing,
  onDelete,
  onEdit,
  boxInfo,
}) => {
  const animation = useRef(new Animated.Value(0)).current;
  const animationRef = useRef<Animated.CompositeAnimation | null>(null);


  useEffect(() => {
    if (selected) {
      // Start rotational shaking animation
      animationRef.current = Animated.loop(
        Animated.sequence([
          Animated.timing(animation, {
            toValue: 1,
            duration: 200, // Duration for half rotation
            useNativeDriver: false, // Must be false for web
          }),
          Animated.timing(animation, {
            toValue: -1,
            duration: 400, // Duration for full rotation back
            useNativeDriver: false,
          }),
          Animated.timing(animation, {
            toValue: 0,
            duration: 200, // Return to initial position
            useNativeDriver: false,
          }),
        ])
      );
      animationRef.current.start();
    } else {
      // Stop the animation
      if (animationRef.current) {
        animationRef.current.stop();
        animationRef.current = null;
      }
      animation.setValue(0);
    }
  }, [selected]);

  const rotateAnimation = {
    transform: [
      {
        rotate: animation.interpolate({
          inputRange: [-1, 0, 1],
          outputRange: ["-5deg", "0deg", "5deg"],
        }),
      },
    ],
  };


  return (
    <TouchableOpacity
      style={[
        {
          width: size,
          height: size,
          margin,
        },
      ]}
      onLongPress={() => lockEditing ? undefined : onLongSelect(id)}
      onPress={() => {
        if (selected) {
          onSelect(id);
        } else {
          onSelect(id);
        }
      }}
      delayLongPress={delayLongPress} 
    >
      <Animated.View
        style={[
          styles.box,
          { backgroundColor: boxInfo.color },
          selected && styles.selectedBox,
          selected ? rotateAnimation : undefined,
        ]}
      >
        {<Image source={{ uri: boxInfo.image }} style={styles.boxImage} />}
        <Text style={[styles.boxText, { fontSize: size * 0.25 }]}>{boxInfo.text}</Text>
      </Animated.View>
      {selected && (
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={() => onDelete(id)} // Call the delete callback
        >
          <MaterialIcons name="close" size={64} color="white" />
        </TouchableOpacity>
      )}
      {selected && (
        <TouchableOpacity
          style={styles.editButton}
          onPress={() => onEdit(id)} // Call the delete callback
        >
          <MaterialIcons name="edit" size={64} color="white" />
        </TouchableOpacity>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  box: {
    flex: 1, // Ensures the Animated.View fills the TouchableOpacity
    justifyContent: "center",
    alignItems: "center",
    borderRadius: 4,
    overflow: "hidden",
    position: "relative", // Required for absolute positioning of the text
  },
  selectedBox: {
    borderColor: "blue",
    borderWidth: 2,
  },
  boxText: {
    color: "#fff",
    fontSize: 64, // Adjusted for better readability over images
    fontWeight: "bold",
    textAlign: "center",
    position: "absolute", // Position text over the image
    zIndex: 1, // Ensure text is above the image
    textShadowColor: "#000", // Black shadow for the border effect
    textShadowOffset: { width: 10, height: 10 }, // Top-left shadow
    textShadowRadius: 10,
  },
  boxImage: {
    width: "100%",
    height: "100%",
    resizeMode: "cover",
    position: "absolute", // Make sure the image is the background
    top: 0,
    left: 0,
  },
  deleteButton: {
    position: "absolute",
    top: 4,
    right: 4,
    width: 50,
    height: 50,
    backgroundColor: "red",
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  editButton: {
    position: "absolute",
    top: 4,
    left: 4,
    width: 50,
    height: 50,
    backgroundColor: "green",
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
});

export default WordBox;
