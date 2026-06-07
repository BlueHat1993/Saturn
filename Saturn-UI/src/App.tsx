import { useCallback, useState } from 'react';
import { querySearch } from './lib/api';
import { ChatPanel } from './components/ChatPanel';
import { GraphPanel } from './components/GraphPanel';
import type { ChatMessage } from './types';
import './App.css';

function createId(): string {
  return crypto.randomUUID();
}

export default function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolResponse, setToolResponse] = useState<string[]>([]);
  const [lastQuery, setLastQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = useCallback(async (query: string) => {
    setError(null);
    setMessages((prev) => [...prev, { id: createId(), role: 'user', content: query }]);
    setLastQuery(query);
    setLoading(true);

    try {
      const result = await querySearch(query);
      setToolResponse(result.tool_response);
      setMessages((prev) => [
        ...prev,
        { id: createId(), role: 'assistant', content: result.answer },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Something went wrong';
      setError(message);
      setMessages((prev) => [
        ...prev,
        { id: createId(), role: 'assistant', content: `Error: ${message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Saturn</h1>
          <p>Knowledge search</p>
        </div>
        {error && <span className="app-error">{error}</span>}
      </header>

      <main className="app-main">
        <ChatPanel messages={messages} loading={loading} onSend={handleSend} />
        <GraphPanel toolResponse={toolResponse} query={lastQuery} />
      </main>
    </div>
  );
}
