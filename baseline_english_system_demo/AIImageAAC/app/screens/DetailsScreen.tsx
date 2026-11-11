import React from "react";
import { View, Text, Button, StyleSheet } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";

// Import the type of your stack
import {RootStackParamList} from "../index";

type Props = NativeStackScreenProps<RootStackParamList, "Details">;

export default function DetailsScreen({ navigation }: Props) {
  return (
    <View style={styles.container}>
      <Text>Details Screen</Text>
      <Button
        title="Go Back"
        onPress={() => navigation.goBack()}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
});
