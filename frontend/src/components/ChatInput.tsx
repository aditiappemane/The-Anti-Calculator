import React, { useState, KeyboardEvent } from 'react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-end space-x-2 max-w-4xl mx-auto">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 
          focus:outline-none focus:ring-2 focus:ring-primary-500 
          bg-white text-black dark:bg-gray-800 dark:text-gray-100 
          disabled:opacity-50 disabled:cursor-not-allowed"

          style={{ minHeight: '48px', maxHeight: '120px' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !message.trim()}
          className="bg-primary-600 hover:bg-primary-700 text-white px-6 py-3 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  );
};

