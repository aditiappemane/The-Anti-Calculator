import axios from 'axios';
import { UserCreate } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const loginUser = async (email: string, password: string): Promise<string> => {
  const response = await axios.post(`${API_URL}/api/token`, new URLSearchParams({
    username: email,
    password: password,
  }), {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });
  return response.data.access_token;
};

export const registerUser = async (userData: UserCreate): Promise<any> => {
  const response = await axios.post(`${API_URL}/api/signup`, userData);
  return response.data;
};
