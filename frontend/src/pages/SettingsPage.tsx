import { useState, useEffect } from 'react'

// ── Types ────────────────────────────────────────────────────────────────────

interface AppConfig {
  providers?: {
    openrouter?: { apiKey?: string }
    anthropic?:  { apiKey?: string }
    openai?:     { apiKey?: string }
    gemini?:     { apiKey?: string }
    groq?:       { apiKey?: string }
    ollama?:     { apiBase?: string }
  }
  agents?: {
    defaults?: {
      model?:                string
      provider?:             string
      max_tool_iterations?:  number
      context_window_tokens?:number
    }
  }
  channels?: {
    telegram?: { enabled?: boolean; token?: string; allowFrom?: string[] }
    discord?:  { enabled?: boolean; token?: string; allowFrom?: string[]; groupPolicy?: string }
    whatsapp?: { enabled?: boolean; allowFrom?: string[] }
  }
  tools?: {
    exec?:             { timeout?: number }
    restrict_to_workspace?: boolean
    web?: { search?: { enable?: boolean } }
  }
}

// ── Helper components ────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={{ marginBottom: 'var(--space-xl)' }}>
      <h2 style={{
        fontFamily: 'var(--font-display)',
        fontSize: '1.15rem',
        marginBottom: 'var(--space-md)',
        paddingBottom: 'var(--space-xs)',
        borderBottom: '2px solid var(--black)',
      }}>
        {title}
      </h2>
      <div style={{ display: 'grid', gap: 'var(--space-md)' }}>
        {children}
      </div>
    </section>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="field">
      <span className="label">{label}</span>
      {children}
      {hint && (
        <span style={{ fontSize: '0.78rem', color: 'var(--grey-400)', fontStyle: 'italic' }}>
          {hint}
        </span>
      )}
    </div>
  )
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string
  hint?: string
  checked: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-md)' }}>
      <div>
        <div style={{ fontFamily: 'var(--font-serif)', fontSize: '0.95rem' }}>{label}</div>
        {hint && <div style={{ fontSize: '0.78rem', color: 'var(--grey-400)', fontStyle: 'italic' }}>{hint}</div>}
      </div>
      <button
        className={`btn btn--sm ${checked ? 'btn--filled' : ''}`}
        onClick={() => onChange(!checked)}
        style={{ minWidth: 64, textAlign: 'center' }}
      >
        {checked ? 'On' : 'Off'}
      </button>
    </div>
  )
}

function ApiKeyField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}) {
  const [show, setShow] = useState(false)
  return (
    <Field label={label}>
      <div style={{ display: 'flex', gap: 0 }}>
        <input
          className="input"
          type={show ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder ?? 'sk-…'}
          style={{ flex: 1, borderRight: 'none' }}
        />
        <button
          className="btn btn--sm"
          onClick={() => setShow(s => !s)}
          style={{ borderLeft: '1.5px solid var(--black)', whiteSpace: 'nowrap' }}
        >
          {show ? 'Hide' : 'Show'}
        </button>
      </div>
    </Field>
  )
}

// ── Main component ───────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [cfg, setCfg]       = useState<AppConfig>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]  = useState(false)
  const [saved, setSaved]    = useState(false)
  const [error, setError]    = useState('')

  // Flat state for every setting
  const [provider, setProvider]    = useState('openrouter')
  const [model, setModel]          = useState('anthropic/claude-opus-4-5')

  // Provider keys
  const [orKey, setOrKey]      = useState('')   // openrouter
  const [antKey, setAntKey]    = useState('')   // anthropic
  const [oaiKey, setOaiKey]    = useState('')   // openai
  const [gemKey, setGemKey]    = useState('')   // gemini
  const [groqKey, setGroqKey]  = useState('')   // groq
  const [ollamaBase, setOllamaBase] = useState('http://localhost:11434')

  // Agent
  const [maxIter, setMaxIter]      = useState(20)
  const [ctxTokens, setCtxTokens]  = useState(100000)

  // Telegram
  const [tgEnabled, setTgEnabled]  = useState(false)
  const [tgToken, setTgToken]      = useState('')
  const [tgAllow, setTgAllow]      = useState('')

  // Discord
  const [dcEnabled, setDcEnabled]  = useState(false)
  const [dcToken, setDcToken]      = useState('')
  const [dcAllow, setDcAllow]      = useState('')
  const [dcPolicy, setDcPolicy]    = useState<'mention' | 'open'>('mention')

  // WhatsApp
  const [waEnabled, setWaEnabled]  = useState(false)
  const [waAllow, setWaAllow]      = useState('')

  // Tools
  const [execTimeout, setExecTimeout]       = useState(60)
  const [restrictWs, setRestrictWs]         = useState(true)
  const [webSearchEnabled, setWebSearch]    = useState(true)

  // ── Load config ────────────────────────────────────────────────────────────
  useEffect(() => {
    fetch('/api/config')
      .then(r => r.json())
      .then((d: AppConfig) => {
        setCfg(d)

        const prov = d.agents?.defaults?.provider ?? 'openrouter'
        setProvider(prov)
        setModel(d.agents?.defaults?.model ?? 'anthropic/claude-opus-4-5')
        setMaxIter(d.agents?.defaults?.max_tool_iterations ?? 20)
        setCtxTokens(d.agents?.defaults?.context_window_tokens ?? 100000)

        setOrKey(d.providers?.openrouter?.apiKey ?? '')
        setAntKey(d.providers?.anthropic?.apiKey  ?? '')
        setOaiKey(d.providers?.openai?.apiKey     ?? '')
        setGemKey(d.providers?.gemini?.apiKey      ?? '')
        setGroqKey(d.providers?.groq?.apiKey       ?? '')
        setOllamaBase(d.providers?.ollama?.apiBase ?? 'http://localhost:11434')

        const tg = d.channels?.telegram
        setTgEnabled(tg?.enabled ?? false)
        setTgToken(tg?.token ?? '')
        setTgAllow((tg?.allowFrom ?? []).join(', '))

        const dc = d.channels?.discord
        setDcEnabled(dc?.enabled ?? false)
        setDcToken(dc?.token ?? '')
        setDcAllow((dc?.allowFrom ?? []).join(', '))
        setDcPolicy((dc?.groupPolicy as 'mention' | 'open') ?? 'mention')

        const wa = d.channels?.whatsapp
        setWaEnabled(wa?.enabled ?? false)
        setWaAllow((wa?.allowFrom ?? []).join(', '))

        setExecTimeout(d.tools?.exec?.timeout ?? 60)
        setRestrictWs(d.tools?.restrict_to_workspace ?? true)
        setWebSearch(d.tools?.web?.search?.enable ?? true)

        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  // ── Save config ────────────────────────────────────────────────────────────
  async function handleSave() {
    setError('')
    setSaving(true)

    const toList = (s: string) =>
      s.split(',').map(x => x.trim()).filter(Boolean)

    const merged: AppConfig = {
      ...cfg,
      providers: {
        openrouter: { apiKey: orKey },
        anthropic:  { apiKey: antKey },
        openai:     { apiKey: oaiKey },
        gemini:     { apiKey: gemKey },
        groq:       { apiKey: groqKey },
        ollama:     { apiBase: ollamaBase },
      },
      agents: {
        defaults: {
          model,
          provider,
          max_tool_iterations:   maxIter,
          context_window_tokens: ctxTokens,
        },
      },
      channels: {
        telegram: { enabled: tgEnabled, token: tgToken, allowFrom: toList(tgAllow) },
        discord:  { enabled: dcEnabled, token: dcToken, allowFrom: toList(dcAllow), groupPolicy: dcPolicy },
        whatsapp: { enabled: waEnabled, allowFrom: toList(waAllow) },
      },
      tools: {
        exec: { timeout: execTimeout },
        restrict_to_workspace: restrictWs,
        web: { search: { enable: webSearchEnabled } },
      },
    }

    try {
      const r = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ config: merged }),
      })
      if (!r.ok) throw new Error('Server error')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
      setError('Failed to save. Is the API server running?')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p style={{ fontStyle: 'italic', color: 'var(--grey-600)' }}>Loading configuration…</p>
      </div>
    )
  }

  return (
    <div className="page">
      {/* ── Page header ── */}
      <div style={{ marginBottom: 'var(--space-xl)' }}>
        <h1 style={{ marginBottom: '0.2rem' }}>Settings</h1>
        <p style={{ color: 'var(--grey-600)', fontStyle: 'italic' }}>
          All changes are written to <code>~/.nanobot/config.json</code>.
        </p>
      </div>

      {/* ── LLM Provider ── */}
      <Section title="LLM Provider">
        <Field label="Active Provider">
          <select className="input" value={provider} onChange={e => setProvider(e.target.value)}>
            <option value="openrouter">OpenRouter</option>
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Google Gemini</option>
            <option value="groq">Groq</option>
            <option value="ollama">Ollama (local)</option>
          </select>
        </Field>
        <Field label="Default Model" hint="e.g. anthropic/claude-opus-4-5 or gpt-4o">
          <input
            className="input"
            value={model}
            onChange={e => setModel(e.target.value)}
            placeholder="anthropic/claude-opus-4-5"
          />
        </Field>
      </Section>

      {/* ── API Keys ── */}
      <Section title="API Keys">
        <ApiKeyField label="OpenRouter" value={orKey} onChange={setOrKey} placeholder="sk-or-v1-…" />
        <ApiKeyField label="Anthropic"  value={antKey} onChange={setAntKey} />
        <ApiKeyField label="OpenAI"     value={oaiKey} onChange={setOaiKey} />
        <ApiKeyField label="Google Gemini" value={gemKey} onChange={setGemKey} placeholder="AI…" />
        <ApiKeyField label="Groq"       value={groqKey} onChange={setGroqKey} />
        <Field label="Ollama Base URL" hint="Only needed for local Ollama deployments">
          <input
            className="input"
            value={ollamaBase}
            onChange={e => setOllamaBase(e.target.value)}
          />
        </Field>
      </Section>

      {/* ── Agent Behaviour ── */}
      <Section title="Agent Behaviour">
        <Field label="Max Tool Iterations" hint="How many tool calls an agent can make per turn">
          <input
            className="input"
            type="number"
            min={1}
            max={100}
            value={maxIter}
            onChange={e => setMaxIter(Number(e.target.value))}
            style={{ maxWidth: 120 }}
          />
        </Field>
        <Field label="Context Window (tokens)" hint="Tokens to keep in the rolling conversation window">
          <input
            className="input"
            type="number"
            min={1000}
            step={1000}
            value={ctxTokens}
            onChange={e => setCtxTokens(Number(e.target.value))}
            style={{ maxWidth: 160 }}
          />
        </Field>
      </Section>

      {/* ── Telegram ── */}
      <Section title="Telegram">
        <ToggleRow
          label="Enable Telegram"
          hint="Requires a bot token from @BotFather"
          checked={tgEnabled}
          onChange={setTgEnabled}
        />
        {tgEnabled && (
          <>
            <ApiKeyField label="Bot Token" value={tgToken} onChange={setTgToken} placeholder="123456:ABC…" />
            <Field label="Allowed User IDs" hint="Comma-separated Telegram user IDs. Leave blank to allow all.">
              <input
                className="input"
                value={tgAllow}
                onChange={e => setTgAllow(e.target.value)}
                placeholder="123456789, 987654321"
              />
            </Field>
          </>
        )}
      </Section>

      {/* ── Discord ── */}
      <Section title="Discord">
        <ToggleRow
          label="Enable Discord"
          hint="Requires a bot token from discord.com/developers"
          checked={dcEnabled}
          onChange={setDcEnabled}
        />
        {dcEnabled && (
          <>
            <ApiKeyField label="Bot Token" value={dcToken} onChange={setDcToken} placeholder="MTI…" />
            <Field label="Allowed User IDs" hint="Comma-separated Discord user IDs.">
              <input
                className="input"
                value={dcAllow}
                onChange={e => setDcAllow(e.target.value)}
                placeholder="123456789012345678"
              />
            </Field>
            <Field label="Response Policy">
              <select
                className="input"
                style={{ maxWidth: 220 }}
                value={dcPolicy}
                onChange={e => setDcPolicy(e.target.value as 'mention' | 'open')}
              >
                <option value="mention">Mention only (respond when @mentioned)</option>
                <option value="open">Open (respond to all messages)</option>
              </select>
            </Field>
          </>
        )}
      </Section>

      {/* ── WhatsApp ── */}
      <Section title="WhatsApp">
        <ToggleRow
          label="Enable WhatsApp"
          hint="Requires Node.js ≥ 18 and a linked device"
          checked={waEnabled}
          onChange={setWaEnabled}
        />
        {waEnabled && (
          <Field label="Allowed Phone Numbers" hint="Comma-separated international numbers, e.g. +1234567890">
            <input
              className="input"
              value={waAllow}
              onChange={e => setWaAllow(e.target.value)}
              placeholder="+1234567890, +9876543210"
            />
          </Field>
        )}
      </Section>

      {/* ── Tools ── */}
      <Section title="Tools">
        <Field label="Exec Timeout (seconds)" hint="Maximum time a shell command is allowed to run">
          <input
            className="input"
            type="number"
            min={5}
            max={600}
            value={execTimeout}
            onChange={e => setExecTimeout(Number(e.target.value))}
            style={{ maxWidth: 120 }}
          />
        </Field>
        <ToggleRow
          label="Restrict agents to workspace"
          hint="Prevents agents from reading or writing files outside their workspace directory"
          checked={restrictWs}
          onChange={setRestrictWs}
        />
        <ToggleRow
          label="Enable web search"
          hint="Allows agents to search the web during planning and analysis"
          checked={webSearchEnabled}
          onChange={setWebSearch}
        />
      </Section>

      {/* ── Save bar ── */}
      <div style={{
        position: 'sticky',
        bottom: 0,
        margin: '0 calc(-1 * var(--space-lg))',
        padding: 'var(--space-sm) var(--space-lg)',
        borderTop: '2px solid var(--black)',
        background: 'var(--white)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-md)',
      }}>
        <button
          className="btn btn--filled"
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
        {saved && (
          <span className="chip chip--ok" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
            Saved.
          </span>
        )}
        {error && (
          <span className="chip chip--error" style={{ fontSize: '0.8rem' }}>
            {error}
          </span>
        )}
      </div>
    </div>
  )
}
