import { Routes, Route, Navigate, NavLink } from 'react-router-dom'
import OnboardingPage from './pages/OnboardingPage'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* ── Navigation ── */}
      <nav className="nav">
        <span className="nav__logo">🐈 nanobot</span>
        <NavLink to="/onboarding" className={({ isActive }) => 'nav__link' + (isActive ? ' active' : '')}>
          Setup
        </NavLink>
        <NavLink to="/chat" className={({ isActive }) => 'nav__link' + (isActive ? ' active' : '')}>
          Architect Chat
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => 'nav__link' + (isActive ? ' active' : '')}>
          Settings
        </NavLink>
      </nav>

      {/* ── Views ── */}
      <main style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/onboarding" replace />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
