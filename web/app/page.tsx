// web/app/page.tsx
"use client"; // required for Next.js App Router to make this a client component

import { useEffect, useRef, useState } from "react";

/**
 * Chat UI with history, auto-scroll, Enter-to-send, and follow-up auto-submit.
 *
 * Assumes backend at process.env.NEXT_PUBLIC_API_URL + '/chat/'.
 */

type ChatResponse = {
  answer: string | null;
  confidence: number;
  sources: string[];
  cached: boolean;
  follow_up: string | null;
  redacted?: boolean;
};

type Message = {
  id: string; // unique id
  from: "user" | "bot" | "system";
  text: string;
  time: string;
  meta?: Partial<ChatResponse>;
};

export default function Page() {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  
  // Log API URL on component mount
  useEffect(() => {
    console.log('Environment:', {
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
      API_BASE: API_BASE
    });
  }, [API_BASE]);

  const [question, setQuestion] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);

  // ref to container for auto-scrolling
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

    // Fetch welcome message on mount
  useEffect(() => {
    async function fetchWelcome() {
      try {
        console.log('Fetching welcome from:', `${API_BASE}/chat/`);
        
        const resp = await fetch(`${API_BASE}/chat/`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Origin': window.location.origin
          },
          credentials: 'omit'  // Don't send credentials for GET
        });
        
        // Log full response details
        console.log('Welcome response:', {
          status: resp.status,
          statusText: resp.statusText,
          headers: Object.fromEntries(resp.headers.entries())
        });

        if (!resp.ok) {
          const errorText = await resp.text();
          console.error('Error response body:', errorText);
          throw new Error(`Failed to fetch welcome: ${resp.status}`);
        }

        const data = await resp.json() as ChatResponse;
        console.log('Welcome data:', data);
        
        pushMessage({
          id: makeId('b_'),
          from: 'bot',
          text: data.answer || 'Hi there!',
          time: nowLabel(),
          meta: data
        });
      } catch (err) {
        console.error('Error fetching welcome:', err);
        // Show fallback welcome even if API fails
        pushMessage({
          id: makeId('b_'),
          from: 'bot',
          text: 'Hi there! I'm Chatty, how can I assist you today?',
          time: nowLabel(),
          meta: {
            answer: 'Hi there! I'm Chatty, how can I assist you today?',
            confidence: 1.0,
            sources: [],
            cached: false,
            follow_up: null
          }
        });
      }
    }
    fetchWelcome();
  }, [API_BASE]); // include API_BASE in deps

  // ensure latest message is visible
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [messages, loading]);

  // helper to add a message to history
  function pushMessage(msg: Message) {
    setMessages((prev) => [...prev, msg]);
  }

  // create a little unique id (not crypto-safe, fine for UI)
  function makeId(prefix = "") {
    return prefix + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  // Format current ISO time for display
  function nowLabel() {
    return new Date().toLocaleTimeString();
  }

  // Main send function (call to backend)
  async function sendQuestion(q?: string) {
    const questionText = (q ?? question).trim();
    if (!questionText) {
      setError("Please enter a question.");
      return;
    }

    setError(null);
    setLoading(true);

    // Add user's message to history
    const userMsg: Message = {
      id: makeId("u_"),
      from: "user",
      text: questionText,
      time: nowLabel(),
    };
    pushMessage(userMsg);

    // clear input quickly for UX
    setQuestion("");

    try {
      console.log('Sending question to:', `${API_BASE}/chat/`);
      const resp = await fetch(`${API_BASE}/chat/`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Accept": "application/json"
        },
        body: JSON.stringify({ user_id: "web_user", question: questionText }),
        credentials: 'omit',  // Don't send credentials
        mode: 'cors'  // Explicitly request CORS mode
      });
      
      console.log('Response details:', {
        status: resp.status,
        statusText: resp.statusText,
        headers: Object.fromEntries(resp.headers.entries())
      });

      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(`Server ${resp.status}: ${txt}`);
      }

      const data = (await resp.json()) as ChatResponse;

      const botText = data.answer ?? data.follow_up ?? "I don't know.";

      const botMsg: Message = {
        id: makeId("b_"),
        from: "bot",
        text: botText,
        time: nowLabel(),
        meta: data,
      };

      pushMessage(botMsg);

      // If the response includes a follow_up but no answer, we might want to show it distinctly.
      // We already include follow_up inside botMsg.meta for later UI affordances.
    } catch (err: any) {
      setError(err?.message ?? "Unknown error");
      // push a system message to indicate failure (optional)
      pushMessage({
        id: makeId("s_"),
        from: "system",
        text: `Error: ${err?.message ?? "Unknown error"}`,
        time: nowLabel(),
      });
    } finally {
      setLoading(false);
    }
  }

  // Handle Enter key to send (Shift+Enter for newline)
  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!loading) sendQuestion();
    }
  }

  // Clicking a follow-up will auto-send it immediately
  function handleFollowUpClick(follow: string) {
    sendQuestion(follow);
  }

  // small UI renderer for message bubble
  function renderMessage(m: Message) {
    const isUser = m.from === "user";
    const isBot = m.from === "bot";
    const isSystem = m.from === "system";

    const containerStyle: React.CSSProperties = {
      display: "flex",
      marginBottom: 10,
      justifyContent: isUser ? "flex-end" : "flex-start",
    };

    const bubbleStyle: React.CSSProperties = {
      maxWidth: "80%",
      padding: "10px 12px",
      borderRadius: 12,
      background: isUser ? "#111827" : isSystem ? "#fef3c7" : "#f3f4f6",
      color: isUser ? "white" : "#111827",
      whiteSpace: "pre-wrap",
    };

    return (
      <div key={m.id} style={containerStyle}>
        <div>
          <div style={{ fontSize: 11, color: "#666", marginBottom: 4, textAlign: isUser ? "right" : "left" }}>
            {isUser ? "You" : isSystem ? "System" : "Assistant"} • {m.time}
          </div>
          <div style={bubbleStyle}>
            <div>{m.text}</div>
            {/* If this is a bot message and has meta.follow_up (and no explicit answer), show quick follow button */}
            {isBot && m.meta?.follow_up && (
              <div style={{ marginTop: 8 }}>
                <button
                  onClick={() => handleFollowUpClick(m.meta!.follow_up!)}
                  style={{
                    background: "#eef2ff",
                    border: "1px solid #c7d2fe",
                    padding: "6px 10px",
                    borderRadius: 6,
                    cursor: "pointer",
                  }}
                >
                  {m.meta.follow_up}
                </button>
              </div>
            )}

            {/* Show sources and confidence inline when available */}
            {isBot && m.meta && (
              <div style={{ marginTop: 8, fontSize: 12, color: "#555" }}>
                <div>Confidence: {m.meta.confidence?.toFixed(2)} {m.meta.cached ? "(cached)" : ""}</div>
                {m.meta.sources && m.meta.sources.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    <strong>Sources</strong>
                    <ul style={{ marginTop: 6 }}>
                      {m.meta.sources.map((s, i) => (
                        <li key={i} style={{ fontSize: 12 }}>
                          <code style={{ background: "#ece8e8ff", padding: "2px 6px", borderRadius: 4 }}>{s}</code>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <main style={styles.container}>
      <h1 style={styles.title}>Simple RAG Chat — Conversation View</h1>

      <div style={styles.chatBox}>
        {/* messages list */}
        <div style={styles.messages}>
          {messages.length === 0 ? (
            <div style={{ color: "#666" }}>No messages yet — ask a question below.</div>
          ) : (
            messages.map((m) => renderMessage(m))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* composer */}
        <div style={styles.composer}>
          <textarea
            placeholder="Type your question. Shift+Enter for newline. Press Enter to send."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={onKeyDown}
            rows={3}
            style={styles.textarea}
            disabled={loading}
          />

          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button onClick={() => sendQuestion()} disabled={loading} style={styles.primaryBtn}>
              {loading ? "Sending…" : "Send"}
            </button>

            <button
              onClick={() => {
                setQuestion("");
              }}
              disabled={loading}
              style={styles.secondaryBtn}
            >
              Clear
            </button>
          </div>

          {error && <div style={{ color: "#a00", marginTop: 8 }}>{error}</div>}
        </div>
      </div>

      <footer style={{ marginTop: 20, color: "#888" }}>
        Backend: <code>{API_BASE}</code>
      </footer>
    </main>
  );
}

/* Minimal inline styles */
const styles: Record<string, React.CSSProperties> = {
  container: {
    fontFamily: "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial",
    padding: 24,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  title: { margin: 0, marginBottom: 12 },
  chatBox: {
    width: "100%",
    maxWidth: 900,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  messages: {
    minHeight: 300,
    maxHeight: "60vh",
    overflowY: "auto",
    padding: 12,
    borderRadius: 8,
    background: "#130404ff",
    border: "1px solid #e5e7eb",
  },
  composer: {
    padding: 12,
    borderRadius: 8,
    background: "white",
    border: "1px solid #e5e7eb",
  },
  textarea: {
    width: "100%",
    padding: 10,
    resize: "vertical",
    backgroundColor: "#1f2937",
    color: "white",
    fontSize: 14,
  },
  primaryBtn: {
    background: "#111827",
    color: "white",
    padding: "8px 12px",
    borderRadius: 6,
    border: "none",
    cursor: "pointer",
  },
  secondaryBtn: {
    background: "#f3f4f6",
    color: "#111827",
    padding: "8px 12px",
    borderRadius: 6,
    border: "1px solid #e5e7eb",
    cursor: "pointer",
  },
};
