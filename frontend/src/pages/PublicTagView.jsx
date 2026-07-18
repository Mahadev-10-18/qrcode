import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldAlert, CheckCircle2, SearchX, Loader2 } from 'lucide-react';

export default function PublicTagView() {
  const { id } = useParams();
  const [tagData, setTagData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [contactStatus, setContactStatus] = useState(null);
  const [phone, setPhone] = useState('');

  useEffect(() => {
    const fetchTag = async () => {
      try {
        const response = await fetch(`/api/t/${id}`);
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('NOT_FOUND');
          }
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
      const response = await fetch(`/api/t/${id}/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ method: 'text', finder_phone: phone })
      });
      if (!response.ok) throw new Error('Failed to contact');
      setContactStatus('success');
    } catch {
      setContactStatus('error');
    }
  };

  if (loading) {
    return (
      <div className="view-container loading-container">
        <Loader2 className="spinner" size={48} />
        <p>Locating item...</p>
      </div>
    );
  }

  if (error === 'NOT_FOUND') {
    return (
      <div className="view-container not-found-container">
        <div className="glass-card">
          <SearchX size={64} className="icon-error" />
          <h1>Item Not Found</h1>
          <p>This tag is either invalid, paused, or no longer active.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="view-container error-container">
        <div className="glass-card">
          <ShieldAlert size={64} className="icon-warning" />
          <h1>Oops!</h1>
          <p>Something went wrong verifying this tag.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="view-container active-container">
      <div className="glass-card">
        <CheckCircle2 size={64} className="icon-success" />
        <p className="subtitle">You have found</p>
        <h1 className="tag-label">{tagData.label}</h1>
        
        <div className="action-section">
          <p>{tagData.cta || "Please contact the owner to return it."}</p>
          
          <div className="phone-input-group">
            <input
              type="tel"
              placeholder="Your phone number (e.g. +15551234567)"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={contactStatus === 'loading' || contactStatus === 'success'}
              className="phone-input"
            />
            <button 
              className={`contact-btn ${contactStatus}`} 
              onClick={handleContact}
              disabled={contactStatus === 'loading' || contactStatus === 'success' || !phone.trim()}
            >
              {contactStatus === 'loading' && <Loader2 className="spinner-small" />}
              {contactStatus === 'success' ? 'Owner Notified!' : 'Notify Owner'}
            </button>
          </div>
          
          {contactStatus === 'error' && (
            <p className="error-text">Failed to send notification. Please try again.</p>
          )}
        </div>
      </div>
    </div>
  );
}
