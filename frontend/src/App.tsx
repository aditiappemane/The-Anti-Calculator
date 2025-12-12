import React, { useState, useRef, useEffect } from 'react';
import { Message, ConversationState, LeadCaptureForm } from './types';
import { ChatMessageComponent } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { LoadingIndicator } from './components/LoadingIndicator';
import { LeadCaptureFormComponent } from './components/LeadCaptureForm';
import { chatApi } from './services/api';

function App() {
  const [state, setState] = useState<ConversationState>({
    conversationId: null,
    messages: [],
    isLoading: false,
    showLeadForm: false,
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [state.messages, state.isLoading]);

  const addMessage = (content: string, role: 'user' | 'assistant') => {
    const newMessage: Message = {
      id: Date.now().toString(),
      role,
      content,
      timestamp: new Date(),
    };
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, newMessage],
    }));
  };

  const handleSendMessage = async (message: string) => {
    // Add user message immediately
    addMessage(message, 'user');
    setState((prev) => ({ ...prev, isLoading: true }));

    try {
      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();

      const response = await chatApi.sendMessage(
        message,
        state.conversationId
      );

      // Extract conversation ID from headers if new conversation
      const conversationId =
        response.headers.get('X-Conversation-ID') || state.conversationId;

      if (conversationId && !state.conversationId) {
        setState((prev) => ({ ...prev, conversationId }));
      }

      // Stream the response
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = '';
      let messageId = Date.now().toString();

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          assistantMessage += chunk;

          // Update the last message or create new one
          setState((prev) => {
            const lastMessage = prev.messages[prev.messages.length - 1];
            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.id === messageId) {
              // Update existing streaming message
              const updatedMessages = [...prev.messages];
              updatedMessages[updatedMessages.length - 1] = {
                ...lastMessage,
                content: assistantMessage,
              };
              return { ...prev, messages: updatedMessages };
            } else {
              // Create new assistant message
              return {
                ...prev,
                messages: [
                  ...prev.messages,
                  {
                    id: messageId,
                    role: 'assistant',
                    content: assistantMessage,
                    timestamp: new Date(),
                  },
                ],
              };
            }
          });
        }
      }

      // Check for conversation ID in the message
      if (assistantMessage.includes('[CONVERSATION_ID:')) {
        const match = assistantMessage.match(/\[CONVERSATION_ID:([^\]]+)\]/);
        if (match && match[1]) {
          const extractedId = match[1];
          setState((prev) => ({
            ...prev,
            conversationId: extractedId,
          }));
          // Remove the marker from the message
          assistantMessage = assistantMessage.replace(
            /\[CONVERSATION_ID:[^\]]+\]/g,
            ''
          );
          setState((prev) => {
            const updatedMessages = [...prev.messages];
            const lastMessage = updatedMessages[updatedMessages.length - 1];
            if (lastMessage) {
              lastMessage.content = assistantMessage;
            }
            return { ...prev, messages: updatedMessages };
          });
        }
      }

      // Show lead form after a helpful conversation
      if (
        assistantMessage.length > 100 &&
        (assistantMessage.toLowerCase().includes('contact') ||
          assistantMessage.toLowerCase().includes('assistance') ||
          assistantMessage.toLowerCase().includes('help'))
      ) {
        setTimeout(() => {
          setState((prev) => ({ ...prev, showLeadForm: true }));
        }, 2000);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      addMessage(
        'Sorry, I encountered an error. Please try again.',
        'assistant'
      );
    } finally {
      setState((prev) => ({ ...prev, isLoading: false }));
      abortControllerRef.current = null;
    }
  };

  const handleLeadSubmit = async (form: LeadCaptureForm) => {
    if (!state.conversationId) {
      throw new Error('No conversation ID available');
    }

    await chatApi.captureLead({
      conversation_id: state.conversationId,
      ...form,
    });

    setState((prev) => ({ ...prev, showLeadForm: false }));
    addMessage(
      'Thank you! We have received your information and will be in touch soon.',
      'assistant'
    );
  };

  const handleLeadCancel = () => {
    setState((prev) => ({ ...prev, showLeadForm: false }));
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            🏠 AI Mortgage Advisor - UAE
          </h1>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            Get expert advice on buying vs renting, and mortgage refinancing
          </p>
        </div>
      </header>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto">
          {state.messages.length === 0 && (
            <div className="text-center mt-12">
              <div className="text-6xl mb-4">🏠</div>
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Welcome to AI Mortgage Advisor
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                I can help you decide whether to buy or rent a property in the UAE,
                <br />
                or assist with mortgage refinancing decisions.
              </p>
              <div className="mt-8 space-y-2 text-left max-w-md mx-auto">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  💡 <strong>Try asking:</strong>
                </p>
                <ul className="text-sm text-gray-600 dark:text-gray-300 space-y-1 ml-6">
                  <li>• "I want to buy a 2M AED apartment"</li>
                  <li>• "Should I rent or buy if rent is 8,000 AED/month?"</li>
                  <li>• "Help me refinance my mortgage"</li>
                </ul>
              </div>
            </div>
          )}

          {state.messages.map((message) => (
            <ChatMessageComponent key={message.id} message={message} />
          ))}

          {state.isLoading && <LoadingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Chat Input */}
      <ChatInput
        onSendMessage={handleSendMessage}
        disabled={state.isLoading}
      />

      {/* Lead Capture Form Modal */}
      {state.showLeadForm && state.conversationId && (
        <LeadCaptureFormComponent
          conversationId={state.conversationId}
          onSubmit={handleLeadSubmit}
          onCancel={handleLeadCancel}
        />
      )}
    </div>
  );
}

export default App;

