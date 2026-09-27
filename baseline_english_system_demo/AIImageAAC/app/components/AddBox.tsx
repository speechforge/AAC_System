import React, { useState } from "react";
import { Text, StyleSheet, TouchableOpacity } from "react-native";
import CreateBoxModal from "./CreateBoxModal";
import { BoxInfo } from "../types";

interface AddBoxProps {
  boxSize: number;
  margin: number;
  onAdd: (text: string, color: string, image: string, isFolder: boolean) => void;
  deletedBoxes: BoxInfo[];
  onReAdd: (box: BoxInfo) => void;
  isFolderOpen: boolean;
}

const AddBox: React.FC<AddBoxProps> = ({
  boxSize,
  margin,
  onAdd,
  deletedBoxes,
  onReAdd,
  isFolderOpen,
}) => {
  const [isModalVisible, setIsModalVisible] = useState(false);

  return (
    <>
      <TouchableOpacity
        style={[
          styles.addBox,
          { width: boxSize, height: boxSize, margin: margin / 2 },
        ]}
        onPress={() => setIsModalVisible(true)}
      >
        <Text style={[styles.addBoxText, { fontSize: boxSize / 2 }]}>+</Text>
      </TouchableOpacity>

      <CreateBoxModal
        isVisible={isModalVisible}
        onClose={() => setIsModalVisible(false)}
        onAdd={onAdd}
        deletedBoxes={deletedBoxes}
        onReAdd={(box) => {
          onReAdd(box);
          setIsModalVisible(false);
        }}
        isFolderOpen={isFolderOpen}
      />
    </>
  );
};

const styles = StyleSheet.create({
  addBox: {
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#e0e0e0",
    borderRadius: 4,
    borderColor: "#aaa",
    borderWidth: 1,
  },
  addBoxText: {
    fontWeight: "bold",
    color: "#555",
  },
});

export default AddBox;
