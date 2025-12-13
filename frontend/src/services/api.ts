/**
 * API service for communicating with the backend.
 */

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the Authorization header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export const chatStream = async (message: string, conversationId: string | null): Promise<ReadableStreamDefaultReader<Uint8Array>> => {
  const token = localStorage.getItem('authToken');
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  // Check if response is okay (e.g., 200-299 status code)
  if (!response.ok) {
    const errorBody = await response.text(); // Read error response body
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorBody}`);
  }

  if (!response.body) {
    throw new Error("Streaming not supported: response body is null");
  }

  const reader = response.body.getReader();

  // Explicitly check if the reader has a read method
  if (typeof reader.read !== 'function') {
    throw new Error("Invalid reader object: 'read' method is missing.");
  }

  return reader;
};

export const getConversationHistory = async (conversationId: string): Promise<any[]> => {
  const response = await api.get(`/api/conversation/${conversationId}`);
  return response.data;
};

export const captureLead = async (leadData: { conversation_id: string; name: string; email: string; phone: string }): Promise<any> => {
  const response = await api.post('/api/lead-capture', leadData);
  return response.data;
};

