/**
 * TypeScript interfaces for the AI Mortgage Advisor application.
 */

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatResponse {
  conversation_id: string;
  message: string;
}

export interface LeadCaptureForm {
  name: string;
  email: string;
  phone?: string;
}

export interface ConversationState {
  conversationId: string | null;
  messages: Message[];
  isLoading: boolean;
  showLeadForm: boolean;
}

