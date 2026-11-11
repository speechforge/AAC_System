import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';

interface WebSocketContextType {
  isConnected: boolean;
  messages: any[];
  sendMessage: (event: string, message: any) => void;
  connectionStatus: 'connecting' | 'connected' | 'disconnecting' | 'disconnected' | 'error';
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

interface WebSocketProviderProps {
  children: React.ReactNode;
  socketUrl: string;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children, socketUrl }) => {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnecting' | 'disconnected' | 'error'>('connecting');

  const maxReconnectAttempts = 10;

  const sendMessage = useCallback((event: string, message: any) => {
    if (socket && isConnected) {
      socket.emit(event, message);
    } else {
      console.warn('Cannot send message: WebSocket is not connected');
    }
  }, [socket, isConnected]);

  useEffect(() => {
    setConnectionStatus('connecting');

    const newSocket = io(socketUrl, {
      transports: ['websocket'],
      reconnectionAttempts: maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 64000,
      autoConnect: true,
    });

    setSocket(newSocket);

    newSocket.on('connect', () => {
      setIsConnected(true);
      setConnectionStatus('connected');
      console.log('WebSocket connected');
    });

    newSocket.on('disconnect', (reason: string) => {
      setIsConnected(false);
      setConnectionStatus('disconnected');
      console.warn(`WebSocket disconnected: ${reason}`);
    });

    newSocket.on('connect_error', (error: any) => {
      console.error('WebSocket connection error:', error);
      setConnectionStatus('error');
    });

    // Define all expected response events
    const responseEvents = [
      'PREDICT_response',
      'SYNTHESISE_response',
      'AUTOCOMPLETE_response',
      'AUDIO_DATA_response',
      'EVENT_response',
      'GENERATE_IMAGE_response',
      'UPLOAD_AUDIO_response',
    ];

    // Register listeners for each response event
    responseEvents.forEach(event => {
      newSocket.on(event, (data: any) => {
        setMessages(prev => [...prev, { event, data }]);
        console.log(`Received message on event "${event}":`, data);
      });
    });

    return () => {
      console.log('Cleaning up WebSocket connection...');
      newSocket.disconnect();
    };
  }, [socketUrl]);

  return (
    <WebSocketContext.Provider value={{ isConnected, messages, sendMessage, connectionStatus }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
