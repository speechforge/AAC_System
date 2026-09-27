import React from "react";
import { NavigationContainer, LinkingOptions } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import HomeScreen from "./screens/HomeScreen";
import DetailsScreen from "./screens/DetailsScreen";
import { WebSocketProvider } from "./provider/WebSocketProvider";

// Define the type of your navigation stack
export type RootStackParamList = {
  Home: undefined;
  Details: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();

// Define linking configuration
const linking: LinkingOptions<RootStackParamList> = {
  prefixes: ["localhost:8081"], // Add your domain
  config: {
    screens: {
      Home: "",          // Maps to the base URL '/'
      Details: "details", // Maps to '/details'
    },
  },
};

export default function Index() {
  return (
    <WebSocketProvider socketUrl="http://130.237.67.212:8000/">
      <HomeScreen/>
    </WebSocketProvider>
  );
}
