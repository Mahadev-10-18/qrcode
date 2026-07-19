import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, SearchX, Loader2, Send, Shield } from 'lucide-react';
import { API_BASE } from '../utils/api';

export default function PublicTagView() {
  const { id } = useParams();
  const [tagData, setTagData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [contactStatus, setContactStatus] = useState(null);
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const fetchTag = async () => {
      try {
        const response = await fetch(`${API_BASE}/t/${id}`);
        if (!response.ok) {
          if (response.status === 404) throw new Error('NOT_FOUND');
          throw new Error('SERVER_ERROR');
        }
        const data = await response.json();
        setTagData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchTag();
  }, [id]);

  const handleContact = async () => {
    if (!phone.trim()) return;
    setContactStatus('loading');
    try {
      const response = await fetch(`${API_BASE}/t/${id}/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ finder_phone: phone, message })
      });
      if (!response.ok) throw new Error('Failed');
      setContactStatus('success');
    } catch {
      setContactStatus('error');
    }
  };

  if (loading) {
    return (
      <div className="loading-container">
        <Loader2 className="spinner" size={48} color="#df71f7" />
        <p style={{ color: 'var(--text-secondary)' }}>Locating item...</p>
      </div>
    );
  }

  if (error === 'NOT_FOUND') {
    return (
      <div className="error-view">
        <SearchX size={64} color="var(--text-secondary)" />
        <h1>Item Not Found</h1>
        <p>This tag is either invalid, paused, or no longer active.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-view">
        <Shield size={64} color="var(--text-secondary)" />
        <h1>Oops!</h1>
        <p>Something went wrong verifying this tag.</p>
      </div>
    );
  }

  return (
    <div className="relay-view">
      <nav className="relay-nav">
        <ShieldCheck size={22} color="var(--accent-magenta-light)" />
        <span>Secure Relay</span>
      </nav>

      <div className="relay-card">
        <div className="relay-icon-wrapper">
          <CheckCircle2 size={32} />
        </div>

        <h1 className="relay-title">You found a lost item</h1>
        <p className="relay-subtitle">
          Thank you for being a Good Samaritan.<br/>
          Leave your contact info so the owner can reach you.
        </p>

        <div className="relay-item-badge">Identified Item</div>
        <h2 className="relay-item-name">{tagData.label.toUpperCase()}</h2>

        <div className="relay-contact-section">
          <input
            type="tel"
            placeholder="Your phone number"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            disabled={contactStatus === 'loading' || contactStatus === 'success'}
            className="relay-phone-input"
          />

          <textarea
            placeholder="Optional message (e.g. where you found it)"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={contactStatus === 'loading' || contactStatus === 'success'}
            className="relay-message-input"
            rows={3}
            maxLength={500}
          />

          <button
            className="relay-btn btn-primary-action"
            onClick={handleContact}
            disabled={contactStatus === 'loading' || contactStatus === 'success' || !phone.trim()}
          >
            {contactStatus === 'loading' ? (
              <><Loader2 className="spinner-small" size={18} /> Sending...</>
            ) : (
              <><Send size={18} /> Send to Owner</>
            )}
          </button>

          {contactStatus === 'success' && (
            <div className="relay-status-box success">
              <CheckCircle2 size={20} />
              <p>Message sent! The owner can now reach out to you.</p>
            </div>
          )}
          {contactStatus === 'error' && (
            <p className="relay-status error">Failed to send. Try again.</p>
          )}
        </div>

        <div className="relay-privacy-box">
          <ShieldCheck size={20} className="privacy-icon" />
          <div>
            <strong>Your privacy is protected</strong>
            <p>The owner will see your phone number only after you choose to send it. Your contact info is never shared publicly.</p>
          </div>
        </div>
      </div>

      <footer className="relay-footer">
        <strong>Secure Relay</strong>
        <p>&copy; {new Date().getFullYear()} Secure Relay. Your phone number stays hidden. Thank you for making the world a safer place.</p>
      </footer>
    </div>
  );
}
