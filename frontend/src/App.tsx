import { useState, useEffect, useRef } from 'react';
import { Route, Routes, Navigate } from 'react-router-dom';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import LoadingIndicator from './components/LoadingIndicator';
import LeadCaptureForm from './components/LeadCaptureForm';
import { chatStream, getConversationHistory } from './services/api';
import { useAuth } from './contexts/AuthContext';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ProfilePage from './pages/ProfilePage';

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'ai';
  timestamp: string;
}

interface ProtectedRouteProps {
  children: React.ReactNode;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { token, loading } = useAuth();

  if (loading) {
    return <LoadingIndicator />;
  }

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [showLeadForm, setShowLeadForm] = useState(false);
  const { user, token } = useAuth();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const storedConversationId = localStorage.getItem('conversationId');
    if (storedConversationId) {
      setConversationId(storedConversationId);
      loadConversationHistory(storedConversationId);
    } else {
      // Initialize with a welcome message if no conversation history
      setMessages([
        {
          id: 0,
          text: "Hello! I'm your AI Mortgage Advisor. How can I help you today with buying, renting, or refinancing in the UAE?",
          sender: 'ai',
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadConversationHistory = async (id: string) => {
    try {
      const response = await getConversationHistory(id);
      const historyMessages = response.messages; // Access the messages array
      const formattedMessages: Message[] = historyMessages.map((msg: any, index: number) => ({
        id: index,
        text: msg.content,
        sender: msg.role === 'user' ? 'user' : 'ai',
        timestamp: new Date().toISOString(), // Use actual timestamp if available
      }));
      setMessages(formattedMessages);
    } catch (error: any) {
      console.error('Failed to load conversation history:', error);
      // If conversation not found (e.g., backend restarted), clear local storage and start fresh
      if (error.response && error.response.status === 404) {
        localStorage.removeItem('conversationId');
        setConversationId(null);
        setMessages([
          {
            id: 0,
            text: "Hello! I'm your AI Mortgage Advisor. How can I help you today with buying, renting, or refinancing in the UAE?",
            sender: 'ai',
            timestamp: new Date().toISOString(),
          },
        ]);
      } else {
        // For other errors, display a generic message
        setMessages([
          {
            id: 0,
            text: 'Failed to load conversation history. Please try refreshing.',
            sender: 'ai',
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    }
  };

  const sendMessage = async () => {
    if (input.trim() === '') return;

    const newMessage: Message = {
      id: messages.length,
      text: input,
      sender: 'user',
      timestamp: new Date().toISOString(),
    };
    setMessages((prevMessages) => [...prevMessages, newMessage]);
    setInput('');
    setLoading(true);

    let aiResponseText = '';
    let newConversationId: string | null = conversationId;
    let isFirstAiChunk = true;
    const decoder = new TextDecoder("utf-8");

    try {
      console.log("Attempting to connect to chatStream...");
      const reader = await chatStream(input, conversationId);
      console.log("Connected to chatStream. Starting to read chunks...");

      while (true) {
        const { value, done } = await reader.read();
        console.log("Raw chunk received:", value);

        if (done) {
          console.log("Stream finished.");
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        console.log("Decoded chunk:", chunk);

        let processedChunk = chunk.replace(/__STATE__\{.*?\}/g, '').trim();
        console.log("Processed chunk (after STATE filter and trim):", processedChunk);

        // Check for CONVERSATION_ID marker first, as it's critical and should not be part of chat text
        const convIdMatch = processedChunk.match(/\[CONVERSATION_ID:(.*?)\]/);
        if (convIdMatch) {
          newConversationId = convIdMatch[1];
          setConversationId(newConversationId);
          localStorage.setItem('conversationId', newConversationId);
          console.log("Conversation ID updated:", newConversationId);
          // Remove the CONVERSATION_ID part from the chunk before processing as text
          processedChunk = processedChunk.replace(convIdMatch[0], '').trim();
        }

        // Check for FUNCTION_CALLS marker
        const functionCallMatch = processedChunk.match(/\[FUNCTION_CALLS:(.*?)\]/);
        if (functionCallMatch) {
          try {
            const calls = JSON.parse(functionCallMatch[1]);
            console.log("Function calls detected:", calls);
          } catch (jsonError) {
            console.error("Error parsing FUNCTION_CALLS JSON:", jsonError, "Chunk part:", functionCallMatch[1]);
          }
          // Remove the FUNCTION_CALLS part from the chunk before processing as text
          processedChunk = processedChunk.replace(functionCallMatch[0], '').trim();
        }

        // Only proceed if there's actual text content to display
        if (processedChunk) {
          aiResponseText += processedChunk + " "; // Add a space to prevent words from merging if chunks split words
          console.log("Accumulated AI Response Text:", aiResponseText);

          setMessages((prevMessages) => {
            const lastMessage = prevMessages[prevMessages.length - 1];

            // If it's the first chunk for an AI message (or previous was user's), create new entry
            if (isFirstAiChunk || (lastMessage && lastMessage.sender === 'user')) {
              isFirstAiChunk = false; // Now we're past the first chunk
              return [
                ...prevMessages,
                {
                  id: prevMessages.length,
                  text: aiResponseText.trim(), // Trim final text before setting
                  sender: 'ai',
                  timestamp: new Date().toISOString(),
                },
              ];
            } else if (lastMessage && lastMessage.sender === 'ai') {
              // Otherwise, update the existing last AI message by appending to its text
              return prevMessages.map((msg, index) =>
                index === prevMessages.length - 1 ? { ...msg, text: aiResponseText.trim() } : msg
              );
            }
            return prevMessages; // Should not happen in normal flow if processedChunk is not empty
          });
        }
      }
    } catch (error) {
      console.error('Error during chat streaming (frontend):', error);
      // Ensure the error message is added only once if streaming fails
      if (!messages.some(msg => msg.sender === 'ai' && msg.text.includes('Sorry, I encountered an error.'))) {
        setMessages((prevMessages) => [
          ...prevMessages,
          {
            id: prevMessages.length,
            text: 'Sorry, I encountered an error. Please try again.',
            sender: 'ai',
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    } finally {
      setLoading(false);
      // Optionally, show lead form after a successful conversation
      // setShowLeadForm(true);
    }
  };

  // Main chat UI rendered if authenticated
  const chatUI = (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="flex-shrink-0 bg-white dark:bg-gray-800 shadow-md p-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">AI Mortgage Advisor</h1>
        <div className="flex space-x-4">
          {token && (
            <a href="/profile" className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-600">
              Profile
            </a>
          )}
          {!token && (
            <a href="/login" className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-600">
              Login
            </a>
          )}
          {user && (
            <a href="/" onClick={useAuth().logout} className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-600">
              Logout
            </a>
          )}
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 && (
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

          {messages.map((message) => (
            <ChatMessage key={message.id} message={message.text} sender={message.sender} timestamp={message.timestamp} />
          ))}

          {loading && <LoadingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Chat Input */}
      <div className="flex-shrink-0 p-4 bg-white dark:bg-gray-800 shadow-md">
        <ChatInput onSendMessage={sendMessage} input={input} setInput={setInput} isLoading={loading} />
      </div>

      {/* Lead Capture Form */}
      {showLeadForm && conversationId && (
        <LeadCaptureForm
          conversationId={conversationId}
          onClose={() => setShowLeadForm(false)}
          onLeadCaptured={() => console.log('Lead captured!')}
        />
      )}
    </div>
  );

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            {chatUI}
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/chat" replace />} /> {/* Default redirect to chat */}
      <Route path="*" element={<Navigate to="/chat" replace />} /> {/* Catch-all redirect */}
    </Routes>
  );
}

export default App;

