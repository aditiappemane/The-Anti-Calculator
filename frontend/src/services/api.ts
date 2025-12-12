/**
 * API service for communicating with the backend.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ChatMessage {
  message: string;
  conversation_id?: string | null;
}

export interface LeadCapture {
  conversation_id: string;
  name: string;
  email: string;
  phone?: string;
}

export const chatApi = {
  /**
   * Send a chat message and stream the response.
   */
  async sendMessage(message: string, conversationId: string | null): Promise<Response> {
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response;
  },

  /**
   * Capture lead information.
   */
  async captureLead(lead: LeadCapture): Promise<void> {
    const response = await api.post('/api/lead-capture', lead);
    return response.data;
  },

  /**
   * Get conversation history.
   */
  async getConversation(conversationId: string): Promise<any> {
    const response = await api.get(`/api/conversation/${conversationId}`);
    return response.data;
  },
};

