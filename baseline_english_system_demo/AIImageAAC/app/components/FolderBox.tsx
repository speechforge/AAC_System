import React, { useRef, useEffect, useState } from "react";
import {
  StyleSheet,
  Text,
  TouchableOpacity,
  Animated,
  View,
  Image,
} from "react-native";
import { MaterialIcons } from "@expo/vector-icons"; // For the "X", "edit", and "folder" icons
import { BoxInfo } from "../types";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as ImageManipulator from 'expo-image-manipulator';
import pako from 'pako';
import { Buffer } from 'buffer'; // Import Buffer

const darkenColor = (hex: string, factor: number = 0.2): string => {
  // Remove the hash if present
  hex = hex.replace(/^#/, "");

  // Expand shorthand form (e.g. "03F") to full form ("0033FF")
  if (hex.length === 3) {
    hex = hex.split('').map(char => char + char).join('');
  }

  if (hex.length !== 6) {
    console.error(`Invalid hex color: ${hex}`);
    return "#000000"; // Default to black if invalid
  }

  // Parse r, g, b values
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  // Function to darken a single color component
  const darken = (c: number): number => {
    const newColor = Math.round(c - c * factor);
    return newColor < 0 ? 0 : newColor;
  };

  const newR = darken(r);
  const newG = darken(g);
  const newB = darken(b);

  // Convert back to hex and return
  const toHex = (c: number): string => c.toString(16).padStart(2, '0');

  return `#${toHex(newR)}${toHex(newG)}${toHex(newB)}`;
};


// Utility function to invert an RGBA color
const invertColor = (rgba: string): string => {
  const match = rgba.match(/rgba?\((\d+),\s*(\d+),\s*(\d+),?\s*([\d.]+)?\)/);
  if (!match) return 'white';
  const r = 255 - parseInt(match[1], 10);
  const g = 255 - parseInt(match[2], 10);
  const b = 255 - parseInt(match[3], 10);
  const a = match[4] !== undefined ? parseFloat(match[4]) : 1;
  return `rgba(${r},${g},${b},${a})`;
};

interface FolderBoxProps {
  id: number;
  size: number;
  margin: number;
  selected: boolean;
  boxInfo: BoxInfo;
  onSelect: (id: number | null, uuid: string) => void;
  onLongSelect: (id: number) => void;
  delayLongPress: number; // Optional delay for long press
  lockEditing: boolean; // Optional lock editing flag
  onDelete: (id: number) => void;
  onEdit: (id: number) => void;
}

const FolderBox: React.FC<FolderBoxProps> = ({
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
  const [averageColor, setAverageColor] = useState<string | null>(null); // State for average color


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

  // Calculate the faint border color by doubling the brightness of the box color
  const faintBorderColor = darkenColor(boxInfo.color);

  // Function to compute the average color of the image
  const getAverageColor = async (uri: string): Promise<string> => {
    console.log("Computing average color for:", uri)
    try {
      const manipResult = await ImageManipulator.manipulateAsync(
        uri,
        [{ resize: { width: 1, height: 1 } }],
        { base64: true, format: ImageManipulator.SaveFormat.PNG }
      );
      const base64 = manipResult.base64;

      // Decode the PNG base64 to get the pixel color
      const pngData = Buffer.from(base64, 'base64');

      // PNG signature is the first 8 bytes
      let pos = 8;
      let idatData: number[] = [];

      // Iterate through chunks to find IDAT
      while (pos < pngData.length) {
        const chunkLength = pngData.readUInt32BE(pos);
        const chunkType = pngData.toString('ascii', pos + 4, pos + 8);
        if (chunkType === 'IDAT') {
          idatData = idatData.concat(Array.from(pngData.slice(pos + 8, pos + 8 + chunkLength)));
        }
        pos += 12 + chunkLength; // Move to the next chunk
      }

      if (idatData.length === 0) {
        throw new Error('No IDAT chunk found');
      }

      // Decompress the IDAT data using pako
      const decompressed = pako.inflate(new Uint8Array(idatData));

      // For a 1x1 image, there's only one scanline
      // The first byte is the filter type
      const filterType = decompressed[0];
      if (filterType !== 0) {
        throw new Error(`Unsupported filter type: ${filterType}`);
      }

      // Assuming the image has RGBA format
      const r = decompressed[1];
      const g = decompressed[2];
      const b = decompressed[3];
      const a = decompressed[4];

      return `rgba(${r},${g},${b},${(a / 255).toFixed(2)})`;
    } catch (error) {
      console.error('Error computing average color:', error);
      return boxInfo.color; // Fallback to boxInfo.color if error occurs
    }
  };

  // useEffect to compute average color when the image changes
  useEffect(() => {
    const computeAverageColor = async () => {
      if (boxInfo.image) {
        const color = await getAverageColor(boxInfo.image);
        setAverageColor(color);
      } else {
        setAverageColor(null);
      }
    };
    computeAverageColor();
  }, [boxInfo.image]);

  // Determine if the folder is defined
  const folderDefined = !!boxInfo.folderId;

  // Determine the border color
  const borderColor = !folderDefined ? darkenColor(boxInfo.color) : (averageColor ? averageColor : faintBorderColor);

  const validImage = boxInfo.image && boxInfo.image.length > 0;

  // Define borderWidth here for easy adjustment
  const dynamicBorderWidth = 8; // Change this value as needed

  return (
    <TouchableOpacity
      style={{
        width: size,
        height: size,
        margin,
      }}
      onLongPress={() => lockEditing ? undefined : onLongSelect(id)}
      onPress={() => onSelect(id, boxInfo.folderId ?? "")}
      delayLongPress={delayLongPress} // Use the loaded duration
    >
      <Animated.View
        style={[
          styles.box,
          {
            backgroundColor: boxInfo.color,
            borderColor: borderColor, // Use the computed border color
            // Remove borderWidth from inline styles to avoid conflicts
            // and use dynamicBorderWidth instead
            borderWidth: dynamicBorderWidth,
          },
          selected && styles.selectedBox,
          selected ? rotateAnimation : undefined,
        ]}
      >
        {<Image source={{ uri: boxInfo.image }} style={styles.boxImage} />}

        <Text style={[styles.boxText, { fontSize: size * 0.25 }]}>
          {boxInfo.text}
        </Text>
        {/* Folder Icon at the Bottom Right */}
        <MaterialIcons
          name="folder"
          size={size * 0.2} // Adjust the size as needed
          color={averageColor ? invertColor(averageColor) : "white"} // Invert color if image is present
          style={styles.folderIcon}
        />
      </Animated.View>
      {selected && (
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={() => onDelete(id)} // Call the delete callback
        >
          <MaterialIcons name="close" size={64} color="white" /> {/* Adjusted size for better visibility */}
        </TouchableOpacity>
      )}
      {selected && (
        <TouchableOpacity
          style={styles.editButton}
          onPress={() => onEdit(id)} // Call the edit callback
        >
          <MaterialIcons name="edit" size={64} color="white" /> {/* Adjusted size for better visibility */}
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
    borderRadius: 10,
    borderTopRightRadius: 80, // Adjusted for better appearance
    overflow: "hidden",
    position: "relative", // Required for absolute positioning of the text and folder icon
    borderColor: "transparent", // Will be overridden dynamically
    // Removed borderWidth: 2 from here
  },
  selectedBox: {
    borderColor: "blue",
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
  folderIcon: {
    position: "absolute",
    bottom: 4,
    right: 4,
  },
});

export default FolderBox;
