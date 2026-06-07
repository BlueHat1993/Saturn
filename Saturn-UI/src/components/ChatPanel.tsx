import { useEffect, useRef, useState, type FormEvent } from 'react';
import { MessageContent } from './MessageContent';
import type { ChatMessage } from '../types';

interface ChatPanelProps {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (query: string) => void;
}

export function ChatPanel({ messages, loading, onSend }: ChatPanelProps) {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setInput('');
  }

  return (
    <section className="panel chat-panel">
      <header className="panel-header">
        <h2>Ask Saturn</h2>
        <p>Search your knowledge base</p>
      </header>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Try a question like:</p>
            <button
              type="button"
              className="suggestion"
              onClick={() => onSend('Why are we declaring independence from the British Empire?')}
            >
              why are we declaring independence from the british empire?
            </button>
          </div>
        )}

        {messages.map((message) => (
          <article key={message.id} className={`chat-bubble ${message.role}`}>
            <span className="chat-role">{message.role === 'user' ? 'You' : 'Saturn'}</span>
            <p>
              <MessageContent content={message.content} />
            </p>
          </article>
        ))}

        {loading && (
          <article className="chat-bubble assistant loading">
            <span className="chat-role">Saturn</span>
            <p className="typing">Searching knowledge base…</p>
          </article>
        )}

        <div ref={bottomRef} />
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question…"
          disabled={loading}
          aria-label="Chat message"
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </section>
  );
}
