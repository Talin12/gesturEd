// src/components/Dashboard.jsx
// Place in: frontend/src/components/Dashboard.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const REACTIONS = [
  {
    id: 'red_litmus',
    label: 'Red Litmus Test',
    description: 'Tests for alkaline (base) substances.',
    accent: '#f87171',
    glow: '0 0 40px rgba(248,113,113,0.25)',
    border: 'rgba(248,113,113,0.25)',
    icon: '🔴',
  },
  {
    id: 'blue_litmus',
    label: 'Blue Litmus Test',
    description: 'Tests for acidic substances.',
    accent: '#38bdf8',
    glow: '0 0 40px rgba(56,189,248,0.25)',
    border: 'rgba(56,189,248,0.25)',
    icon: '🔵',
  },
];

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem',
    gap: '2.5rem',
  },
  header: {
    textAlign: 'center',
  },
  eyebrow: {
    display: 'block',
    fontSize: '0.7rem',
    fontFamily: 'var(--mono)',
    color: 'var(--accent-blue)',
    letterSpacing: '0.2em',
    textTransform: 'uppercase',
    marginBottom: '0.75rem',
  },
  title: {
    fontSize: '2.2rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
    lineHeight: 1.1,
    marginBottom: '0.5rem',
  },
  subtitle: {
    color: 'var(--text-muted)',
    fontSize: '0.9rem',
    fontFamily: 'var(--mono)',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
    gap: '1.25rem',
    width: '100%',
    maxWidth: '600px',
  },
  card: (accent, border, glow, hover) => ({
    background: 'var(--surface)',
    border: `1px solid ${hover ? accent : border}`,
    borderRadius: '6px',
    padding: '2rem 1.5rem',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '0.75rem',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: hover ? glow : 'none',
    transform: hover ? 'translateY(-3px)' : 'none',
    textAlign: 'left',
    width: '100%',
    fontFamily: 'var(--sans)',
  }),
  icon: {
    fontSize: '2rem',
  },
  cardTitle: (accent) => ({
    fontSize: '1.1rem',
    fontWeight: 700,
    color: accent,
    lineHeight: 1.2,
  }),
  cardDesc: {
    fontSize: '0.82rem',
    color: 'var(--text-muted)',
    lineHeight: 1.5,
  },
  arrow: (accent) => ({
    marginTop: '0.5rem',
    fontFamily: 'var(--mono)',
    fontSize: '0.8rem',
    color: accent,
    letterSpacing: '0.05em',
  }),
  logoutBtn: {
    background: 'none',
    border: '1px solid var(--border)',
    color: 'var(--text-muted)',
    padding: '0.5rem 1.2rem',
    borderRadius: '3px',
    fontSize: '0.75rem',
    fontFamily: 'var(--mono)',
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    transition: 'color 0.2s, border-color 0.2s',
  },
  error: {
    padding: '0.7rem 0.9rem',
    background: 'rgba(248,113,113,0.08)',
    border: '1px solid rgba(248,113,113,0.3)',
    borderRadius: '3px',
    color: 'var(--accent-red)',
    fontSize: '0.82rem',
    fontFamily: 'var(--mono)',
  },
};

export default function Dashboard() {
  const [hoveredId, setHoveredId] = useState(null);
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleReactionSelect = async (reactionId) => {
    setLoading(reactionId);
    setError('');
    try {
      await api.post('/reactions/start/', { reaction_type: reactionId });
      // Only navigate AFTER confirmed success
      navigate('/lab');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to start reaction. Are you logged in?');
    } finally {
      setLoading(null);
    }
  };

  const handleLogout = async () => {
    try {
      await api.post('/accounts/logout/');
    } finally {
      navigate('/');
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <span style={styles.eyebrow}>// Select Experiment</span>
        <h1 style={styles.title}>GesturEd</h1>
        <p style={styles.subtitle}>Choose a reaction to begin your virtual chemistry lab</p>
      </div>

      <div style={styles.grid}>
        {REACTIONS.map((r) => {
          const isHovered = hoveredId === r.id;
          const isLoading = loading === r.id;
          return (
            <button
              key={r.id}
              style={styles.card(r.accent, r.border, r.glow, isHovered)}
              onMouseEnter={() => setHoveredId(r.id)}
              onMouseLeave={() => setHoveredId(null)}
              onClick={() => handleReactionSelect(r.id)}
              disabled={!!loading}
            >
              <span style={styles.icon}>{r.icon}</span>
              <span style={styles.cardTitle(r.accent)}>{r.label}</span>
              <span style={styles.cardDesc}>{r.description}</span>
              <span style={styles.arrow(r.accent)}>
                {isLoading ? 'Starting...' : '→ Begin test'}
              </span>
            </button>
          );
        })}
      </div>

      {error && <div style={styles.error}>⚠ {error}</div>}

      <button style={styles.logoutBtn} onClick={handleLogout}>
        ← Logout
      </button>
    </div>
  );
}