import { useState, useEffect, useRef } from 'react'

type Step = 'system-check' | 'config'

interface SystemStatus {
  available: boolean
  version: string
}

export default function OnboardingPage() {
  const [step, setStep]         = useState<Step>('system-check')
  const [status, setStatus]     = useState<SystemStatus | null>(null)
  const [checking, setChecking] = useState(true)
  const [installing, setInstalling] = useState(false)
  const [installLog, setInstallLog] = useState('')
  const logRef = useRef<HTMLDivElement>(null)

  const [config, setConfig]   = useState<Record<string, unknown>>({})
  const [apiKey, setApiKey]   = useState('')
  const [model, setModel]     = useState('anthropic/claude-opus-4-5')
  const [provider, setProvider] = useState('openrouter')
  const [tgToken, setTgToken] = useState('')
  const [dcToken, setDcToken] = useState('')
  const [saving, setSaving]   = useState(false)
  const [saved, setSaved]     = useState(false)

  useEffect(() => {
    fetch('/api/system/check-opencode')
      .then(r => r.json())
      .then((d: SystemStatus) => { setStatus(d); setChecking(false) })
      .catch(() => { setStatus({ available: false, version: '' }); setChecking(false) })
  }, [])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [installLog])

  async function handleInstall() {
    setInstalling(true)
    setInstallLog('')
    const resp = await fetch('/api/system/install-opencode', { method: 'POST' })
    const reader = resp.body!.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      setInstallLog(prev => prev + decoder.decode(value))
    }
    setInstalling(false)
    const check = await fetch('/api/system/check-opencode').then(r => r.json()) as SystemStatus
    setStatus(check)
  }

  useEffect(() => {
    if (step !== 'config') return
    fetch('/api/config')
      .then(r => r.json())
      .then((d: Record<string, unknown>) => {
        setConfig(d)
        const provs = d.providers as Record<string, Record<string, string>> | undefined
        if (provs) setApiKey(provs[provider]?.apiKey ?? '')
        const agents = d.agents as Record<string, Record<string, string>> | undefined
        if (agents?.defaults?.model) setModel(agents.defaults.model)
        if (agents?.defaults?.provider) setProvider(agents.defaults.provider)
        const ch = d.channels as Record<string, Record<string, string>> | undefined
        if (ch?.telegram?.token) setTgToken(ch.telegram.token)
        if (ch?.discord?.token) setDcToken(ch.discord.token)
      })
  }, [step, provider])

  async function handleSave() {
    setSaving(true)
    const merged = {
      ...config,
      providers: { ...(config.providers as Record<string, unknown> ?? {}), [provider]: { apiKey } },
      agents: { defaults: { model, provider } },
      channels: {
        ...(config.channels as Record<string, unknown> ?? {}),
        ...(tgToken ? { telegram: { enabled: true, token: tgToken, allowFrom: ['*'] } } : {}),
        ...(dcToken ? { discord: { enabled: true, token: dcToken, allowFrom: ['*'], groupPolicy: 'mention' } } : {}),
      },
    }
    await fetch('/api/config/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config: merged }),
    })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="page">
      <h1 style={{ marginBottom: '0.25rem' }}>Pipeline Setup</h1>
      <p style={{ color: 'var(--grey-600)', marginBottom: 'var(--space-lg)', fontStyle: 'italic' }}>
        Configure the system before starting a build session.
      </p>

      {/* Step tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 'var(--space-lg)', borderBottom: '2px solid var(--black)' }}>
        {(['system-check', 'config'] as Step[]).map((s, i) => (
          <button
            key={s}
            className="btn"
            onClick={() => setStep(s)}
            style={{
              borderBottom: step === s ? '3px solid var(--black)' : '3px solid transparent',
              borderTop: 'none', borderLeft: 'none', borderRight: 'none',
              fontStyle: step === s ? 'italic' : 'normal',
              background: 'transparent',
              color: step === s ? 'var(--black)' : 'var(--grey-600)',
              paddingBottom: '0.5rem',
            }}
          >
            {i + 1}. {s === 'system-check' ? 'System Check' : 'Configure'}
          </button>
        ))}
      </div>

      {/* ── Step 1 ── */}
      {step === 'system-check' && (
        <div className="box">
          <h2 style={{ marginBottom: 'var(--space-md)' }}>System Check</h2>

          {checking && (
            <p style={{ color: 'var(--grey-600)', fontStyle: 'italic' }}>Checking for opencode CLI…</p>
          )}

          {!checking && status && (
            <div style={{ marginBottom: 'var(--space-md)' }}>
              {status.available
                ? <span className="chip chip--ok">opencode {status.version} — ready</span>
                : <span className="chip chip--error">opencode not found on PATH</span>
              }
            </div>
          )}

          {!checking && !status?.available && (
            <>
              <p style={{ marginBottom: 'var(--space-md)', color: 'var(--grey-600)' }}>
                The <code>opencode</code> CLI is required by the <code>@coder</code> agent.
              </p>
              <button className="btn btn--filled" onClick={handleInstall} disabled={installing}>
                {installing ? 'Installing…' : 'Install via npm'}
              </button>
              {installLog && (
                <div
                  ref={logRef}
                  className="terminal"
                  style={{ marginTop: 'var(--space-md)', height: 200 }}
                >
                  {installLog}
                </div>
              )}
            </>
          )}

          {!checking && status?.available && (
            <button className="btn" style={{ marginTop: 'var(--space-sm)' }} onClick={() => setStep('config')}>
              Next: Configure →
            </button>
          )}
        </div>
      )}

      {/* ── Step 2 ── */}
      {step === 'config' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-lg)' }}>

          <div className="box">
            <h2 style={{ marginBottom: 'var(--space-md)' }}>LLM Provider</h2>
            <div style={{ display: 'grid', gap: 'var(--space-md)' }}>
              <div className="field">
                <span className="label">Provider</span>
                <select className="input" value={provider} onChange={e => setProvider(e.target.value)}>
                  <option value="openrouter">OpenRouter</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="openai">OpenAI</option>
                  <option value="gemini">Gemini</option>
                  <option value="groq">Groq</option>
                </select>
              </div>
              <div className="field">
                <span className="label">API Key</span>
                <input className="input" type="password" placeholder="sk-…" value={apiKey} onChange={e => setApiKey(e.target.value)} />
              </div>
              <div className="field">
                <span className="label">Model</span>
                <input className="input" placeholder="anthropic/claude-opus-4-5" value={model} onChange={e => setModel(e.target.value)} />
              </div>
            </div>
          </div>

          <div className="box">
            <h2 style={{ marginBottom: 'var(--space-md)' }}>Chat Channels <span style={{ color: 'var(--grey-400)', fontWeight: 400, fontSize: '0.85rem' }}>— optional</span></h2>
            <div style={{ display: 'grid', gap: 'var(--space-md)' }}>
              <div className="field">
                <span className="label">Telegram Bot Token</span>
                <input className="input" placeholder="Leave blank to skip" value={tgToken} onChange={e => setTgToken(e.target.value)} />
              </div>
              <div className="field">
                <span className="label">Discord Bot Token</span>
                <input className="input" placeholder="Leave blank to skip" value={dcToken} onChange={e => setDcToken(e.target.value)} />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
            <button className="btn btn--filled" onClick={handleSave} disabled={saving || !apiKey}>
              {saving ? 'Saving…' : 'Save Configuration'}
            </button>
            {saved && <span className="chip chip--ok">Saved.</span>}
          </div>
        </div>
      )}
    </div>
  )
}
