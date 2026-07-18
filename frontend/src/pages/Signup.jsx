import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, UserPlus, AlertCircle, Phone, Mail, Loader2 } from 'lucide-react';

export default function Signup() {
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, phone_number: phone }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Signup failed');
      }

      // Auto login: save user id and redirect to dashboard
      localStorage.setItem('x_user_id', data.id);
      localStorage.setItem('user_email', data.email);
      navigate('/');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="view-container">
      <div className="glass-card" style={{ maxWidth: '440px' }}>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1.5rem' }}>
          <div style={{
            background: 'var(--accent-gradient)',
            padding: '1rem',
            borderRadius: '1rem',
            boxShadow: '0 8px 16px rgba(139, 92, 246, 0.3)'
          }}>
            <ShieldCheck size={40} color="#fff" />
          </div>
        </div>

        <h1 className="gradient-text" style={{ marginBottom: '0.5rem', fontSize: '2rem' }}>Get Started</h1>
        <p style={{ color: 'var(--color-muted)', marginBottom: '2rem' }}>
          Create secure digital profiles for your items
        </p>

        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            padding: '1rem',
            borderRadius: '0.75rem',
            color: 'var(--error)',
            marginBottom: '1.5rem',
            fontSize: '0.875rem',
            textAlign: 'left'
          }}>
            <AlertCircle size={20} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSignup}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <div style={{ position: 'relative' }}>
              <Mail size={18} color="rgba(255,255,255,0.3)" style={{
                position: 'absolute',
                left: '1.25rem',
                top: '50%',
                transform: 'translateY(-50%)'
              }} />
              <input
                type="email"
                required
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                style={{ paddingLeft: '3rem' }}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Phone Number (E.164 format)</label>
            <div style={{ position: 'relative' }}>
              <Phone size={18} color="rgba(255,255,255,0.3)" style={{
                position: 'absolute',
                left: '1.25rem',
                top: '50%',
                transform: 'translateY(-50%)'
              }} />
              <input
                type="tel"
                required
                placeholder="+15551234567"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="input-field"
                style={{ paddingLeft: '3rem' }}
              />
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)', marginTop: '0.25rem', display: 'block' }}>
              Used to route private finder voice calls and SMS.
            </span>
          </div>

          <button type="submit" disabled={loading} className="btn btn-primary" style={{ marginTop: '1.5rem' }}>
            {loading ? (
              <>
                <Loader2 className="spinner" size={20} />
                Creating Profile...
              </>
            ) : (
              <>
                <UserPlus size={20} />
                Sign Up
              </>
            )}
          </button>
        </form>

        <p style={{ marginTop: '2rem', fontSize: '0.875rem', color: 'var(--color-muted)' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 600 }}>
            Log In
          </Link>
        </p>
      </div>
    </div>
  );
}
