import { useCallback, useState } from 'react';
import { Icon } from '@mdi/react';
import { mdiHexagon } from '@mdi/js';
import { querySearch } from './lib/api';
import { ChatPanel } from './components/ChatPanel';import { ConstellationModal } from './components/ConstellationModal';import { GraphPanel } from './components/GraphPanel';
import { Sidebar } from './components/Sidebar';
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
  const [isConstellationOpen, setIsConstellationOpen] = useState(false);

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

  const handleSidebarItemClick = useCallback((item: string) => {
    if (item === 'Constellations') {
      setIsConstellationOpen(true);
    }
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1 className="app-title">
            <Icon path={mdiHexagon} size={1.2} className="app-title-icon" />
            Saturn
          </h1>
          <p>Knowledge search</p>
        </div>
        {error && <span className="app-error">{error}</span>}
      </header>

      <main className="app-main">
        <Sidebar onItemClick={handleSidebarItemClick} />
        <ChatPanel messages={messages} loading={loading} onSend={handleSend} />
        <GraphPanel toolResponse={toolResponse} query={lastQuery} />
      </main>

      <ConstellationModal open={isConstellationOpen} onClose={() => setIsConstellationOpen(false)} />
    </div>
  );
}
