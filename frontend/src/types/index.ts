/**
 * TypeScript interfaces for the AI Mortgage Advisor application.
 */

export interface ChatMessage {
  id: number;
  text: string;
  sender: 'user' | 'ai';
  timestamp: string;
}

export interface LeadData {
  conversation_id: string;
  name: string;
  email: string;
  phone: string;
}

export interface User {
  id: number;
  email: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
  documents?: Document[];
}

export interface UserCreate {
  email: string;
  password: string;
  first_name?: string;
  last_name?: string;
  phone_number?: string;
}

export interface UserUpdate {
  first_name?: string;
  last_name?: string;
  phone_number?: string;
}

export interface Document {
  id: number;
  file_name: string;
  file_path: string;
  file_type?: string;
  owner_id: number;
  uploaded_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

