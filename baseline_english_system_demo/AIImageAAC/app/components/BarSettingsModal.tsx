// BarSettingsModal.tsx
import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  Modal,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ScrollView,
  useWindowDimensions,
} from "react-native";
import { MaterialIcons } from "@expo/vector-icons";
import ButtonItem from "./ButtonItem";
import EditAudioModal from "./EditAudioModal";

interface BarSettingsModalProps {
  isVisible: boolean;
  onClose: () => void;
  buttons: { text: string; uri: string | null }[];
  onUpdateButtons: (
    updatedButtons: { text: string; uri: string | null }[]
  ) => void;
  boxesPerRow?: number; // Number of boxes per row
}

const BarSettingsModal: React.FC<BarSettingsModalProps> = ({
  isVisible,
  onClose,
  buttons,
  onUpdateButtons,
  boxesPerRow = 10, // Default number of boxes per row
}) => {
  const [buttonList, setButtonList] = useState([...buttons]);
  const [editingButtonIndex, setEditingButtonIndex] = useState<number | null>(
    null
  );

  const { width } = useWindowDimensions();

  // Calculate box dimensions
  const boxMargin = 5;
  const containerPadding = 15;
  const availableWidth =
    width - containerPadding * 2 - boxMargin * (boxesPerRow - 1);
  const boxSize = availableWidth / boxesPerRow;

  useEffect(() => {
    setButtonList([...buttons]);
  }, [buttons]);

  const MAX_BUTTONS = 10; // Maximum number of buttons allowed

  const handleAddButton = () => {
    if (buttonList.length >= MAX_BUTTONS) {
      Alert.alert(
        "Maximum Buttons Reached",
        `You can only have up to ${MAX_BUTTONS} buttons.`
      );
      return;
    }
    setButtonList((prev) => [...prev, { text: "New Button", uri: null }]);
  };

  const handleDeleteButton = (index: number) => {
    if (buttonList.length === 1) {
      Alert.alert("Error", "You must have at least one button!");
      return;
    }
    setButtonList((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpdateButton = (
    index: number,
    updatedButton: { text: string; uri: string | null }
  ) => {
    setButtonList((prev) =>
      prev.map((btn, i) => (i === index ? updatedButton : btn))
    );
  };

  const handleSave = () => {
    onUpdateButtons(buttonList);
    onClose();
  };

  return (
    <Modal visible={isVisible} transparent animationType="slide">
      <View style={styles.overlay}>
        <View style={styles.modalContent}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.modalTitle}>Edit Buttons</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <MaterialIcons name="close" size={30} color="#000" />
            </TouchableOpacity>
          </View>

          {/* Content */}
          <ScrollView contentContainerStyle={styles.scrollContainer}>
            <View style={styles.gridContainer}>
              {buttonList.map((item, index) => (
                <ButtonItem
                  key={index}
                  index={index}
                  button={item}
                  boxSize={boxSize}
                  boxMargin={boxMargin}
                  onEdit={() => setEditingButtonIndex(index)}
                  onDelete={handleDeleteButton}
                />
              ))}
              {/* Add New Button */}
              {buttonList.length < MAX_BUTTONS && (
                <TouchableOpacity
                  style={[
                    styles.addButton,
                    {
                      width: boxSize,
                      height: boxSize,
                      margin: boxMargin / 2,
                    },
                  ]}
                  onPress={handleAddButton}
                >
                  <MaterialIcons name="add" size={40} color="#4caf50" />
                  <Text style={styles.addButtonText}>Add</Text>
                </TouchableOpacity>
              )}
            </View>
          </ScrollView>

          {/* Footer */}
          <View style={styles.footer}>
            <TouchableOpacity style={styles.saveButton} onPress={handleSave}>
              <MaterialIcons name="save" size={30} color="#4caf50" />
              <Text style={styles.saveButtonText}>Save</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>

      {/* Edit Audio Modal */}
      {editingButtonIndex !== null && (
        <EditAudioModal
          isVisible={editingButtonIndex !== null}
          onClose={() => setEditingButtonIndex(null)}
          button={buttonList[editingButtonIndex]}
          onUpdate={(updatedButton) => {
            handleUpdateButton(editingButtonIndex, updatedButton);
            setEditingButtonIndex(null);
          }}
        />
      )}
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
    width: "100%",
    maxHeight: "50%", // Fixed amount at the top
    backgroundColor: "#fff",
    padding: 10,
    borderRadius: 15,
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
  scrollContainer: {
    paddingTop: 10,
    paddingBottom: 20,
  },
  gridContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  addButton: {
    backgroundColor: "#e0f2f1",
    borderRadius: 10,
    justifyContent: "center",
    alignItems: "center",
  },
  addButtonText: {
    fontSize: 14,
    color: "#4caf50",
    marginTop: 5,
    fontWeight: "bold",
    textAlign: "center",
  },
  footer: {
    alignItems: "flex-end",
  },
  saveButton: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#e8f5e9",
    paddingVertical: 8,
    paddingHorizontal: 20,
    borderRadius: 10,
  },
  saveButtonText: {
    fontSize: 18,
    color: "#4caf50",
    marginLeft: 10,
    fontWeight: "bold",
  },
});

export default BarSettingsModal;
