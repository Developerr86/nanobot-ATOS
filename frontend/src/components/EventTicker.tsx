import { useEffect, useRef, useState } from 'react'

interface PipelineEvent {
  agent: string
  type: string
  message: string
}

const AGENT_LABELS: Record<string, string> = {
  '@architect': 'arch',
  '@coder':     'code',
  '@qa':        'qa  ',
  'orchestrator': 'orch',
}

export default function EventTicker() {
  const [events, setEvents]     = useState<(PipelineEvent & { ts: string })[]>([])
  const [connected, setConnected] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/ws/events`)
    ws.onopen  = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data) as PipelineEvent & { type: string }
      if (data.type === 'ping') return
      setEvents(prev => [
        ...prev.slice(-150),
        {
          ...data,
          ts: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        },
      ])
    }
    return () => ws.close()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  return (
    <div style={{
      width: 260,
      minWidth: 200,
      borderLeft: '2px solid var(--black)',
      background: 'var(--white)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: 'var(--space-xs) var(--space-sm)',
        borderBottom: '1.5px solid var(--black)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-sm)',
        background: 'var(--grey-100)',
      }}>
        <span style={{
          fontFamily: 'var(--font-display)',
          fontSize: '0.85rem',
          fontWeight: 600,
          letterSpacing: '0.02em',
        }}>
          Live Events
        </span>
        <span
          className="chip chip--muted"
          style={{ marginLeft: 'auto', fontSize: '0.7rem', fontStyle: 'italic' }}
        >
          {connected ? 'live' : 'offline'}
        </span>
      </div>

      {/* Event stream */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: 'var(--space-xs) 0',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.72rem',
        lineHeight: 1.5,
      }}>
        {events.length === 0 && (
          <p style={{
            padding: 'var(--space-sm)',
            color: 'var(--grey-400)',
            fontStyle: 'italic',
            fontFamily: 'var(--font-serif)',
            fontSize: '0.85rem',
          }}>
            Awaiting pipeline activity…
          </p>
        )}
        {events.map((e, i) => {
          const label = AGENT_LABELS[e.agent] ?? e.agent
          const isBold = e.type === 'approved' || e.type === 'rejected'
          return (
            <div
              key={i}
              style={{
                padding: '0.15rem var(--space-sm)',
                borderBottom: '1px solid var(--grey-200)',
                color: e.type === 'rejected' ? 'var(--black)' : 'var(--grey-800)',
                background: e.type === 'approved'
                  ? 'var(--grey-100)'
                  : e.type === 'rejected'
                  ? 'var(--black)'
                  : 'transparent',
              }}
            >
              <span style={{ color: 'var(--grey-400)' }}>{e.ts} </span>
              <span style={{
                fontWeight: isBold ? 700 : 400,
                color: e.type === 'rejected' ? 'var(--white)' : 'var(--black)',
              }}>
                [{label}]
              </span>{' '}
              <span style={{
                color: e.type === 'rejected' ? 'var(--white)' : 'inherit',
              }}>
                {e.message.slice(0, 72)}{e.message.length > 72 ? '…' : ''}
              </span>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
