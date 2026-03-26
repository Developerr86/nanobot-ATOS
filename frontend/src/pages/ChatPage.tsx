import { useState, useEffect, useRef } from 'react'
import EventTicker from '../components/EventTicker'

interface Message {
  role: 'user' | 'architect'
  content: string
  ts: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'architect',
      content: "Hello. I'm your Lead Architect — describe what you want to build and I'll help you design it.",
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])
  const [input, setInput]     = useState('')
  const [connected, setConnected] = useState(false)
  const [wsReady, setWsReady] = useState(false)
  const wsRef     = useRef<WebSocket | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/ws/chat`)
    wsRef.current = ws
    ws.onopen  = () => { setConnected(true);  setWsReady(true) }
    ws.onclose = () => { setConnected(false); setWsReady(false) }
    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data) as { role: string; content: string }
      if (data.role === 'architect') {
        setMessages(prev => [...prev, {
          role: 'architect',
          content: data.content,
          ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }])
      }
    }
    return () => ws.close()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function send() {
    const text = input.trim()
    if (!text || !wsRef.current || !wsReady) return
    setMessages(prev => [...prev, {
      role: 'user',
      content: text,
      ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }])
    wsRef.current.send(JSON.stringify({ content: text }))
    setInput('')
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 47px)', overflow: 'hidden' }}>

      {/* ── Chat panel ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Header strip */}
        <div style={{
          padding: 'var(--space-xs) var(--space-lg)',
          borderBottom: '1.5px solid var(--black)',
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-md)',
        }}>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.95rem' }}>
            Architect Chat
          </span>
          <span className={`chip chip--sm ${connected ? 'chip--ok' : 'chip--muted'}`}
            style={{ marginLeft: 'auto', fontStyle: 'italic' }}>
            {connected ? 'connected' : 'disconnected'}
          </span>
        </div>

        {/* Message list */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: 'var(--space-lg)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--space-md)',
        }}>
          {messages.map((m, i) => (
            <div key={i} style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: m.role === 'user' ? 'flex-end' : 'flex-start',
            }}>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--grey-400)',
                marginBottom: '0.25rem',
                fontFamily: 'var(--font-mono)',
              }}>
                {m.role === 'user' ? 'you' : 'architect'} · {m.ts}
              </div>
              <div className={`bubble bubble--${m.role}`}>{m.content}</div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div style={{
          padding: 'var(--space-sm) var(--space-lg)',
          borderTop: '2px solid var(--black)',
          display: 'flex',
          gap: 'var(--space-sm)',
          alignItems: 'flex-end',
          background: 'var(--grey-100)',
        }}>
          <textarea
            className="input"
            rows={2}
            placeholder="Describe your project, ask questions, or say 'Approved' to start the build…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            style={{ resize: 'none', flex: 1 }}
            disabled={!wsReady}
          />
          <button
            className="btn btn--filled"
            onClick={send}
            disabled={!wsReady || !input.trim()}
            style={{ height: 'fit-content' }}
          >
            Send
          </button>
        </div>
      </div>

      {/* ── Event Ticker ── */}
      <EventTicker />
    </div>
  )
}
