import axios from 'axios';
import { User, UserUpdate, Document } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getAuthHeaders = () => {
  const token = localStorage.getItem('authToken');
  return {
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
    },
  };
};

export const fetchUserProfile = async (): Promise<User> => {
  const response = await axios.get(`${API_URL}/api/profile`, getAuthHeaders());
  return response.data;
};

export const updateUserProfile = async (userId: number, userData: UserUpdate): Promise<User> => {
  const response = await axios.put(`${API_URL}/api/profile`, userData, getAuthHeaders());
  return response.data;
};

export const uploadDocument = async (file: File): Promise<Document> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(`${API_URL}/api/profile/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
      ...getAuthHeaders().headers, // Correctly merge headers
    },
  });
  return response.data;
};

export const fetchUserDocuments = async (): Promise<Document[]> => {
  const response = await axios.get(`${API_URL}/api/profile/documents`, getAuthHeaders());
  return response.data;
};

export const deleteDocument = async (documentId: number): Promise<void> => {
  await axios.delete(`${API_URL}/api/profile/documents/${documentId}`, getAuthHeaders());
};
