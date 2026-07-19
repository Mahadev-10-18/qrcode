import { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ShieldCheck, AlertCircle, Phone, Mail, Loader2, QrCode, Shield, Bell } from 'lucide-react';
import { API_BASE } from '../utils/api';

export default function AuthLanding() {
  const { user, setUser, loading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState('login'); // 'login', 'signup', 'forgot'
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!authLoading && user) {
      navigate('/dashboard');
    }
  }, [user, authLoading, navigate]);

  useEffect(() => {
    setError(null);
    setSuccessMessage(null);
    if (location.pathname === '/signup') {
      setActiveTab('signup');
    } else {
      setActiveTab('login');
    }
  }, [location]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMessage(null);

    if (activeTab === 'forgot') {
      try {
        const response = await fetch(`${API_BASE}/auth/forgot-password`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
          body: JSON.stringify({ email }),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || 'Failed to send reset link');
        }
        setSuccessMessage('Password reset email sent! Please check your inbox.');
        setEmail('');
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
      return;
    }

    const isLogin = activeTab === 'login';
    const endpoint = isLogin ? `${API_BASE}/auth/login` : `${API_BASE}/auth/signup`;
    const body = isLogin
      ? { email, password }
      : { email, phone_number: phone, password };

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'include',
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || `${isLogin ? 'Login' : 'Signup'} failed`);
      }

      if (!isLogin) {
        setSuccessMessage(data.detail || 'Account created. Please verify your email.');
        setActiveTab('login');
        setPassword('');
      } else {
        setUser(data.user);
        navigate('/dashboard');
      }
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
          <Link to="/how-it-works">How it Works</Link>
          <Link to="/faq">FAQ</Link>
          <button className="btn-primary" style={{ width: 'auto', padding: '8px 20px', fontSize: '13px' }} onClick={() => setActiveTab('signup')}>
            Get Started
          </button>
        </div>
      </nav>

      <div className="landing-content">
        <div className="landing-left">
          <h1 className="landing-title">
            TagMaster Pro: <br /><span className="gradient-text">Securely Reunite</span> with Your Valuables.
          </h1>
          <p className="landing-subtitle">
            Create simple, unique QR tags for your belongings. Finders contact you instantly, while we keep your personal phone number completely hidden. Privacy Guaranteed.
          </p>

          <div className="feature-cards">
            <div className="feature-card">
              <div className="feature-icon-wrapper"><QrCode size={22} /></div>
              <h3>Universal QR Tags</h3>
              <p>Generate tags for luggage, keys, pets, or electronics. One scan starts a secure conversation.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon-wrapper"><Shield size={22} /></div>
              <h3>Identity Masking</h3>
              <p>We act as a proxy. Finders message you through our encrypted portal, keeping your contact details private.</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon-wrapper"><Bell size={22} /></div>
              <h3>Instant Alerts</h3>
              <p>Get notified instantly via secure text or phone call the moment a finder tries to contact you.</p>
            </div>
          </div>
        </div>

        <div className="landing-right">
          <div className="auth-card-container">
            {activeTab !== 'forgot' ? (
              <div className="auth-tabs">
                <button
                  className={`auth-tab ${activeTab === 'login' ? 'active' : ''}`}
                  onClick={() => setActiveTab('login')}
                >
                  Login
                </button>
                <button
                  className={`auth-tab ${activeTab === 'signup' ? 'active' : ''}`}
                  onClick={() => setActiveTab('signup')}
                >
                  Get Started (Signup)
                </button>
              </div>
            ) : (
              <div className="auth-tabs" style={{ justifyContent: 'center' }}>
                <span className="auth-tab active" style={{ cursor: 'default' }}>Reset Password</span>
              </div>
            )}

            <div className="auth-body">
              {error && (
                <div className="auth-error">
                  <AlertCircle size={18} />
                  <span>{error}</span>
                </div>
              )}

              {successMessage && (
                <div className="auth-success" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px', borderRadius: '6px', backgroundColor: 'rgba(76, 175, 80, 0.1)', color: '#4CAF50', marginBottom: '16px', fontSize: '14px' }}>
                  <ShieldCheck size={18} />
                  <span>{successMessage}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="auth-form">
                <div className="form-group">
                  <label className="form-label">Email</label>
                  <div className="input-wrapper">
                    <Mail size={16} className="input-icon" />
                    <input
                      type="email"
                      required
                      placeholder="hello@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="form-control"
                    />
                  </div>
                </div>

                {activeTab === 'signup' && (
                  <div className="form-group">
                    <label className="form-label">Phone Number</label>
                    <div className="input-wrapper">
                      <Phone size={16} className="input-icon" />
                      <input
                        type="tel"
                        required
                        placeholder="+15551234567"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        className="form-control"
                      />
                    </div>
                    <span className="input-hint">Required for secure relay calls/texts.</span>
                  </div>
                )}

                {activeTab !== 'forgot' && (
                  <div className="form-group">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <label className="form-label" style={{ margin: 0 }}>Password</label>
                      {activeTab === 'login' && (
                        <button
                          type="button"
                          onClick={() => { setActiveTab('forgot'); setError(null); setSuccessMessage(null); }}
                          style={{ background: 'none', border: 'none', color: 'var(--accent-magenta-light)', cursor: 'pointer', fontSize: '13px', padding: 0 }}
                        >
                          Forgot Password?
                        </button>
                      )}
                    </div>
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
                )}

                <button type="submit" disabled={loading} className="btn-primary auth-submit">
                  {loading ? (
                    <><Loader2 className="spinner" size={18} /> Processing...</>
                  ) : activeTab === 'login' ? (
                    'Login to Dashboard'
                  ) : activeTab === 'signup' ? (
                    'Create Account'
                  ) : (
                    'Send Reset Link'
                  )}
                </button>
              </form>

              {activeTab === 'forgot' && (
                <button
                  type="button"
                  onClick={() => { setActiveTab('login'); setError(null); setSuccessMessage(null); }}
                  className="btn-secondary"
                  style={{ width: '100%', marginTop: '12px', padding: '12px', fontSize: '14px', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'transparent', color: 'var(--text-primary)', cursor: 'pointer' }}
                >
                  Back to Login
                </button>
              )}

              {activeTab !== 'forgot' && (
                <>
                  <div className="auth-divider">
                    <span>or</span>
                  </div>

                  <a href="/api/auth/google/login" className="btn-google">
                    <svg width="18" height="18" viewBox="0 0 48 48" fill="none">
                      <path d="M43.611 20.083H42V20H24v8h11.303c-1.654 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z" fill="#FFC107"/>
                      <path d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z" fill="#FF3D00"/>
                      <path d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z" fill="#4CAF50"/>
                      <path d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002 6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z" fill="#1976D2"/>
                    </svg>
                    Continue with Google
                  </a>
                </>
              )}

              <div className="auth-security-note">
                <ShieldCheck size={18} className="security-icon" />
                <p>
                  <strong>Bank-Level Security:</strong> Your Tag IDs are completely randomized and unguessable, ensuring your personal items stay private.
                </p>
              </div>
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
