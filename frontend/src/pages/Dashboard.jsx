import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  QrCode,
  Plus,
  LogOut,
  User,
  ShieldCheck,
  Tag as TagIcon,
  Download,
  Loader2,
  AlertTriangle,
  ExternalLink,
  X
} from 'lucide-react';

export default function Dashboard() {
  const [profile, setProfile] = useState(null);
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Tag creation state
  const [newLabel, setNewLabel] = useState('');
  const [creating, setCreating] = useState(false);

  // Selected tags for sheet printing
  const [selectedTags, setSelectedTags] = useState([]);
  const [layout, setLayout] = useState(6);
  const [jobStatus, setJobStatus] = useState(null); // 'pending' | 'processing' | 'completed' | 'failed' | null

  // Active QR preview modal state
  const [previewTag, setPreviewTag] = useState(null);

  const navigate = useNavigate();
  const userId = localStorage.getItem('x_user_id');

  const handleLogout = useCallback(() => {
    localStorage.removeItem('x_user_id');
    localStorage.removeItem('user_email');
    navigate('/login');
  }, [navigate]);

  useEffect(() => {
    if (!userId) {
      navigate('/login');
      return;
    }

    const fetchData = async () => {
      try {
        // Fetch profile
        const profRes = await fetch('/api/auth/me', {
          headers: { 'X-User-Id': userId }
        });
        if (!profRes.ok) {
          if (profRes.status === 401) {
            handleLogout();
            return;
          }
          throw new Error('Failed to load profile');
        }
        const profData = await profRes.json();
        setProfile(profData);

        // Fetch tags
        const tagsRes = await fetch('/api/tags/', {
          headers: { 'X-User-Id': userId }
        });
        if (!tagsRes.ok) throw new Error('Failed to load tags');
        const tagsData = await tagsRes.json();
        setTags(tagsData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [userId, navigate, handleLogout]);


  const handleCreateTag = async (e) => {
    e.preventDefault();
    if (!newLabel.trim()) return;
    setCreating(true);
    setError(null);
    setSuccess(null);

    try {
      const res = await fetch('/api/tags/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': userId
        },
        body: JSON.stringify({ label: newLabel })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create tag');
      }

      setTags([data, ...tags]);
      setNewLabel('');
      setSuccess('Tag created successfully!');
      
      // Auto-clear success message
      setTimeout(() => setSuccess(null), 4000);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleStatusChange = async (tagId, newStatus) => {
    setError(null);
    try {
      const res = await fetch(`/api/tags/${tagId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': userId
        },
        body: JSON.stringify({ status: newStatus })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to update tag status');
      }

      const updated = await res.json();
      setTags(tags.map(t => t.id === tagId ? updated : t));
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleSelect = (tagId) => {
    if (selectedTags.includes(tagId)) {
      setSelectedTags(selectedTags.filter(id => id !== tagId));
    } else {
      setSelectedTags([...selectedTags, tagId]);
    }
  };

  const handleGenerateSheet = async () => {
    if (selectedTags.length === 0) return;
    setJobStatus('pending');
    setError(null);

    try {
      const res = await fetch('/api/tags/sheet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': userId
        },
        body: JSON.stringify({ tag_ids: selectedTags, layout })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to initialize sheet job');
      }

      pollJob(data.job_id);
    } catch (err) {
      setError(err.message);
      setJobStatus(null);
    }
  };

  const pollJob = async (id) => {
    const checkStatus = async () => {
      try {
        const res = await fetch(`/api/jobs/${id}`, {
          headers: { 'X-User-Id': userId }
        });

        // Completed returns the PDF byte file directly, which has application/pdf content type
        const contentType = res.headers.get('content-type');
        if (res.ok && contentType === 'application/pdf') {
          setJobStatus('completed');
          // Download PDF
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `sheet_${id}.pdf`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          setSelectedTags([]);
          return true; // Stop polling
        }

        if (!res.ok) {
          throw new Error('Failed to get job status');
        }

        const data = await res.json();
        if (data.status === 'processing') {
          setJobStatus('processing');
        } else if (data.status === 'failed') {
          setJobStatus('failed');
          return true; // Stop polling
        }

        return false;
      } catch (err) {
        setError(err.message);
        setJobStatus('failed');
        return true; // Stop polling
      }
    };

    // Poll every 1s
    const interval = setInterval(async () => {
      const stop = await checkStatus();
      if (stop) clearInterval(interval);
    }, 1000);
  };

  const handleDownloadSinglePdf = (tagId) => {
    const a = document.createElement('a');
    a.href = `/api/tags/${tagId}/pdf?x-user-id=${userId}`; // Auth via query parameter is not natively supported by auth_stub but let's do fetch blob to attach headers
    
    // Proper download attaching X-User-Id headers:
    fetch(`/api/tags/${tagId}/pdf`, {
      headers: { 'X-User-Id': userId }
    })
    .then(res => res.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `tag_${tagId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
    })
    .catch(() => setError('Failed to download PDF'));
  };

  if (loading) {
    return (
      <div className="view-container loading-container">
        <Loader2 className="spinner" size={48} color="#8b5cf6" />
        <p style={{ marginTop: '1rem', color: 'var(--color-muted)' }}>Loading Workspace...</p>
      </div>
    );
  }

  const activeCount = tags.filter(t => t.status === 'active').length;
  const isFree = profile?.plan === 'free';
  const tagLimit = isFree ? 2 : '∞';

  return (
    <div className="page-container">
      {/* Header */}
      <header className="dashboard-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            background: 'var(--accent-gradient)',
            padding: '0.5rem',
            borderRadius: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <ShieldCheck size={24} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.25rem' }}>QR Tag Manager</h1>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)' }}>Workspace</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div className="user-badge">
            <User size={16} />
            <span>{profile?.email}</span>
            <span className={`badge ${isFree ? 'badge-free' : 'badge-paid'}`}>
              {profile?.plan}
            </span>
          </div>
          <button onClick={handleLogout} className="logout-btn">
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Alert notifications */}
      {error && (
        <div style={{
          background: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.2)',
          padding: '1rem',
          borderRadius: '1rem',
          color: 'var(--error)',
          marginBottom: '2rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <AlertTriangle size={20} />
          <p>{error}</p>
        </div>
      )}

      {success && (
        <div style={{
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.2)',
          padding: '1rem',
          borderRadius: '1rem',
          color: 'var(--success)',
          marginBottom: '2rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <ShieldCheck size={20} />
          <p>{success}</p>
        </div>
      )}

      {/* Stats Summary */}
      <section className="stats-grid">
        <div className="glass-card stat-card">
          <span className="stat-label">Total Tags</span>
          <div className="stat-value">{tags.length}</div>
        </div>
        <div className="glass-card stat-card">
          <span className="stat-label">Active / Limit</span>
          <div className="stat-value">
            {activeCount} <span style={{ color: 'var(--color-muted)', fontSize: '1.5rem', fontWeight: 500 }}>/ {tagLimit}</span>
          </div>
        </div>
        <div className="glass-card stat-card">
          <span className="stat-label">Status Check</span>
          <div className="stat-value" style={{ fontSize: '1.75rem', marginTop: '0.75rem', color: 'var(--success)' }}>
            All Secure
          </div>
        </div>
      </section>

      {/* Main Grid */}
      <div className="dashboard-grid">
        {/* Left Side: Tag List */}
        <div className="glass-card section-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1.5rem' }}>Your Registered Items</h2>
            
            {/* Bulk Printing actions */}
            {selectedTags.length > 0 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <select 
                  value={layout} 
                  onChange={(e) => setLayout(parseInt(e.target.value))}
                  className="status-select"
                >
                  <option value={6}>6 per page</option>
                  <option value={12}>12 per page</option>
                </select>
                <button 
                  onClick={handleGenerateSheet}
                  className="btn btn-primary"
                  style={{ padding: '0.5rem 1rem', width: 'auto', fontSize: '0.875rem' }}
                  disabled={jobStatus === 'pending' || jobStatus === 'processing'}
                >
                  {jobStatus === 'pending' || jobStatus === 'processing' ? (
                    <>
                      <Loader2 className="spinner" size={16} />
                      Printing...
                    </>
                  ) : (
                    <>
                      <Download size={16} />
                      Print Sheet ({selectedTags.length})
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {tags.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--color-muted)' }}>
              <TagIcon size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
              <p>No items registered yet.</p>
              <p style={{ fontSize: '0.875rem' }}>Register a tag on the right side to get started.</p>
            </div>
          ) : (
            <div>
              {tags.map((tag) => (
                <div key={tag.id} className="tag-list-item">
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <div className="checkbox-container">
                      <input
                        type="checkbox"
                        className="custom-checkbox"
                        checked={selectedTags.includes(tag.id)}
                        onChange={() => handleToggleSelect(tag.id)}
                      />
                    </div>
                    <div className="tag-item-info">
                      <h3 style={{ fontSize: '1.1rem' }}>{tag.label}</h3>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className={`badge badge-${tag.status}`}>
                          {tag.status.replace('_', ' ')}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--color-muted)' }}>
                          ID: {tag.id.slice(0, 8)}...
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="tag-item-actions">
                    <select
                      value={tag.status}
                      onChange={(e) => handleStatusChange(tag.id, e.target.value)}
                      className="status-select"
                      style={{ marginRight: '0.5rem' }}
                    >
                      <option value="active">Active</option>
                      <option value="paused">Paused</option>
                      <option value="lost_confirmed">Lost</option>
                    </select>

                    <button 
                      onClick={() => setPreviewTag(tag)}
                      className="icon-btn"
                      title="View QR Code"
                    >
                      <QrCode size={18} />
                    </button>

                    <button 
                      onClick={() => handleDownloadSinglePdf(tag.id)}
                      className="icon-btn"
                      title="Download PDF Tag"
                    >
                      <Download size={18} />
                    </button>
                    
                    <a 
                      href={`/t/${tag.id}`} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="icon-btn"
                      title="Public view page"
                    >
                      <ExternalLink size={18} />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Side: Create Tag Form */}
        <div className="glass-card section-card">
          <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>Register New Tag</h2>

          {isFree && activeCount >= 2 && (
            <div style={{
              background: 'rgba(139, 92, 246, 0.1)',
              border: '1px solid rgba(139, 92, 246, 0.2)',
              padding: '1rem',
              borderRadius: '1rem',
              marginBottom: '1.5rem',
              fontSize: '0.875rem'
            }}>
              <p style={{ fontWeight: 600, color: '#a78bfa', marginBottom: '0.25rem' }}>Free Tier Limit Reached</p>
              <p style={{ color: 'var(--color-muted)' }}>
                You have reached the maximum limit of 2 active tags. Pause an item to free up a slot, or upgrade.
              </p>
            </div>
          )}

          <form onSubmit={handleCreateTag}>
            <div className="form-group">
              <label className="form-label">Item Label</label>
              <input
                type="text"
                required
                placeholder="e.g. Backpack, Work Keys"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                className="input-field"
              />
            </div>

            <button 
              type="submit" 
              className="btn btn-primary" 
              style={{ marginTop: '1rem' }}
              disabled={creating || (isFree && activeCount >= 2)}
            >
              {creating ? (
                <>
                  <Loader2 className="spinner" size={20} />
                  Registering...
                </>
              ) : (
                <>
                  <Plus size={20} />
                  Register Tag
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* QR Preview Modal */}
      {previewTag && (
        <div className="modal-overlay" onClick={() => setPreviewTag(null)}>
          <div className="glass-card modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 style={{ fontSize: '1.25rem' }}>QR Code: {previewTag.label}</h2>
              <button onClick={() => setPreviewTag(null)} className="icon-btn">
                <X size={18} />
              </button>
            </div>
            
            <div style={{
              background: '#fff',
              padding: '1.5rem',
              borderRadius: '1rem',
              display: 'inline-block',
              margin: '1.5rem 0'
            }}>
              <img 
                src={`/api/tags/${previewTag.id}/qr?x-user-id=${userId}`} 
                alt="QR Code"
                style={{ width: '220px', height: '220px', display: 'block' }}
              />
            </div>

            <p style={{ fontSize: '0.875rem', color: 'var(--color-muted)', marginBottom: '1.5rem' }}>
              Anyone who scans this QR code will see a form to contact you securely without revealing your phone number.
            </p>

            <button 
              onClick={() => handleDownloadSinglePdf(previewTag.id)}
              className="btn btn-primary"
            >
              <Download size={18} />
              Download Printable Tag (PDF)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
