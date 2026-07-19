import { useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { ShieldCheck, AlertCircle, Loader2 } from 'lucide-react';
import { API_BASE } from '../utils/api';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!token) {
      setError('Invalid or missing password reset token.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to reset password.');
      }

      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="landing-layout">
      <nav className="landing-nav">
        <div className="nav-logo">
          <ShieldCheck size={24} color="var(--accent-magenta-light)" />
          <span>TagMaster Pro</span>
        </div>
        <div className="nav-links">
          <Link to="/login">Login</Link>
          <Link to="/signup" className="btn-primary" style={{ width: 'auto', padding: '8px 20px', fontSize: '13px' }}>Get Started</Link>
        </div>
      </nav>

      <div className="landing-content" style={{ justifyContent: 'center', alignItems: 'center', minHeight: '70vh' }}>
        <div className="landing-right" style={{ width: '100%', maxWidth: '440px', margin: '0 auto' }}>
          <div className="auth-card-container">
            <div className="auth-tabs" style={{ justifyContent: 'center' }}>
              <span className="auth-tab active" style={{ cursor: 'default' }}>Choose New Password</span>
            </div>

            <div className="auth-body">
              {error && (
                <div className="auth-error" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', borderRadius: '6px', backgroundColor: 'rgba(244, 67, 54, 0.1)', color: '#F44336', marginBottom: '16px', fontSize: '14px' }}>
                  <AlertCircle size={18} />
                  <span>{error}</span>
                </div>
              )}

              {success ? (
                <div style={{ textAlign: 'center', padding: '24px 0' }}>
                  <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '48px', height: '48px', borderRadius: '50%', backgroundColor: 'rgba(76, 175, 80, 0.1)', color: '#4CAF50', marginBottom: '16px' }}>
                    <ShieldCheck size={24} />
                  </div>
                  <h3 style={{ fontSize: '18px', color: 'var(--text-primary)', marginBottom: '8px' }}>Password Reset Complete</h3>
                  <p style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '24px' }}>
                    Your password has been updated successfully. You can now log in with your new password.
                  </p>
                  <button
                    onClick={() => navigate('/login')}
                    className="btn-primary"
                    style={{ width: '100%' }}
                  >
                    Go to Login
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="auth-form">
                  <div className="form-group">
                    <label className="form-label">New Password</label>
                    <div className="input-wrapper">
                      <ShieldCheck size={16} className="input-icon" />
                      <input
                        type="password"
                        required
                        placeholder="Minimum 8 characters"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="form-control"
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label">Confirm New Password</label>
                    <div className="input-wrapper">
                      <ShieldCheck size={16} className="input-icon" />
                      <input
                        type="password"
                        required
                        placeholder="Re-enter new password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="form-control"
                      />
                    </div>
                  </div>

                  <button type="submit" disabled={loading} className="btn-primary auth-submit">
                    {loading ? (
                      <><Loader2 className="spinner" size={18} /> Processing...</>
                    ) : (
                      'Update Password'
                    )}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      </div>

      <footer className="landing-footer">
        <div className="footer-content">
          <p>&copy; {new Date().getFullYear()} TagMaster Pro. All rights reserved.</p>
          <div className="footer-links">
            <Link to="/how-it-works">How it Works</Link>
            <Link to="/faq">FAQ</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
