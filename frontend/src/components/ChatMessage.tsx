import React from 'react';
import { Message } from '../types';

interface ChatMessageProps {
  message: string;
  sender: 'user' | 'ai';
  timestamp: string; // Add timestamp prop
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, sender, timestamp }) => {
  const isUser = sender === 'user';
  const formattedTime = new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg shadow ${isUser
          ? 'bg-blue-500 text-white'
          : 'bg-gray-300 text-gray-900 dark:bg-gray-700 dark:text-gray-200' // Changed text-gray-800 to text-gray-900 for darker text
        }`}
      >
        <pre className="text-sm mb-1 whitespace-pre-wrap font-sans">
          {message}
        </pre>
        <span className={`text-xs ${isUser ? 'text-blue-200' : 'text-gray-500 dark:text-gray-400'}`}>
          {formattedTime}
        </span>
      </div>
    </div>
  );
};

export default ChatMessage;

