import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

const styles = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2rem',
  },
  card: {
    width: '100%',
    maxWidth: '400px',
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    padding: '2.5rem',
    boxShadow: 'var(--glow-blue)',
  },
  header: {
    marginBottom: '2rem',
  },
  label: {
    display: 'block',
    fontSize: '0.7rem',
    fontFamily: 'var(--mono)',
    color: 'var(--accent-blue)',
    letterSpacing: '0.15em',
    textTransform: 'uppercase',
    marginBottom: '2rem',
  },
  title: {
    fontSize: '1.8rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
    lineHeight: 1.1,
  },
  tabs: {
    display: 'flex',
    borderBottom: '1px solid var(--border)',
    marginBottom: '1.75rem',
    gap: '0',
  },
  tab: (active) => ({
    flex: 1,
    padding: '0.6rem',
    background: 'none',
    border: 'none',
    borderBottom: active ? '2px solid var(--accent-blue)' : '2px solid transparent',
    color: active ? 'var(--accent-blue)' : 'var(--text-muted)',
    fontSize: '0.8rem',
    fontFamily: 'var(--mono)',
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    transition: 'all 0.2s',
    marginBottom: '-1px',
  }),
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
    marginBottom: '1.5rem',
  },
  fieldLabel: {
    display: 'block',
    fontSize: '0.7rem',
    fontFamily: 'var(--mono)',
    color: 'var(--text-muted)',
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    marginBottom: '0.4rem',
  },
  input: {
    width: '100%',
    padding: '0.65rem 0.9rem',
    background: 'var(--bg)',
    border: '1px solid var(--border)',
    borderRadius: '3px',
    color: 'var(--text-primary)',
    fontSize: '0.95rem',
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  submitBtn: {
    width: '100%',
    padding: '0.8rem',
    background: 'var(--accent-blue)',
    color: '#080c10',
    border: 'none',
    borderRadius: '3px',
    fontWeight: 700,
    fontSize: '0.85rem',
    fontFamily: 'var(--mono)',
    letterSpacing: '0.12em',
    textTransform: 'uppercase',
    transition: 'opacity 0.2s, box-shadow 0.2s',
  },
  error: {
    marginTop: '1rem',
    padding: '0.7rem 0.9rem',
    background: 'rgba(248,113,113,0.08)',
    border: '1px solid rgba(248,113,113,0.3)',
    borderRadius: '3px',
    color: 'var(--accent-red)',
    fontSize: '0.82rem',
    fontFamily: 'var(--mono)',
  },
  success: {
    marginTop: '1rem',
    padding: '0.7rem 0.9rem',
    background: 'rgba(74,222,128,0.08)',
    border: '1px solid rgba(74,222,128,0.3)',
    borderRadius: '3px',
    color: 'var(--accent-green)',
    fontSize: '0.82rem',
    fontFamily: 'var(--mono)',
  },
};

export default function Auth() {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setError('');
    setSuccess('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      if (mode === 'login') {
        await api.post('/accounts/login/', {
          username: form.username,
          password: form.password,
        });
        navigate('/dashboard');
      } else {
        await api.post('/accounts/register/', {
          username: form.username,
          email: form.email,
          password: form.password,
        });
        setSuccess('Account created! You can now log in.');
        setMode('login');
        setForm({ username: '', email: '', password: '' });
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.header}>
          <span style={styles.label}>// Virtual Chemistry Lab</span>
          <h1 style={styles.title}>
            {mode === 'login' ? 'Sign In' : 'Create Account'}
          </h1>
        </div>

        <div style={styles.tabs}>
          <button style={styles.tab(mode === 'login')} onClick={() => { setMode('login'); setError(''); setSuccess(''); }}>
            Login
          </button>
          <button style={styles.tab(mode === 'register')} onClick={() => { setMode('register'); setError(''); setSuccess(''); }}>
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={styles.fieldGroup}>
            <div>
              <label style={styles.fieldLabel}>Username</label>
              <input
                style={styles.input}
                type="text"
                name="username"
                value={form.username}
                onChange={handleChange}
                required
                autoComplete="username"
                placeholder="your_username"
              />
            </div>

            {mode === 'register' && (
              <div>
                <label style={styles.fieldLabel}>Email</label>
                <input
                  style={styles.input}
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                />
              </div>
            )}

            <div>
              <label style={styles.fieldLabel}>Password</label>
              <input
                style={styles.input}
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            style={{ ...styles.submitBtn, opacity: loading ? 0.6 : 1 }}
            disabled={loading}
          >
            {loading ? 'Please wait...' : mode === 'login' ? 'Enter Lab →' : 'Create Account →'}
          </button>
        </form>

        {error && <div style={styles.error}>⚠ {error}</div>}
        {success && <div style={styles.success}>✓ {success}</div>}
      </div>
    </div>
  );
}