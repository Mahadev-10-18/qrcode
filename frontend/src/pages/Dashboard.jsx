import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { authFetch, API_BASE } from '../utils/api';
import { useAuth } from '../contexts/AuthContext';
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
  X,
  LayoutDashboard,
  MessageSquare
} from 'lucide-react';

export default function Dashboard() {
  const { user, setUser, loading: authLoading } = useAuth();
  const [profile, setProfile] = useState(null);
  const [tags, setTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [newLabel, setNewLabel] = useState('');
  const [creating, setCreating] = useState(false);

  const [selectedTags, setSelectedTags] = useState([]);
  const [layout, setLayout] = useState(6);
  const [jobStatus, setJobStatus] = useState(null);

  const [previewTag, setPreviewTag] = useState(null);
  const [qrPreviewUrl, setQrPreviewUrl] = useState(null);

  const [activeTab, setActiveTab] = useState('dashboard');
  const [messages, setMessages] = useState([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  const pollIntervalRef = useRef(null);

  const navigate = useNavigate();

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await authFetch('/auth/logout', { method: 'POST' });
    } catch {
      // ignore
    }
    setUser(null);
    navigate('/login');
  }, [setUser, navigate]);

  useEffect(() => {
    if (authLoading) return;

    if (!user) {
      navigate('/login');
      return;
    }

    const fetchData = async () => {
      try {
        const profData = await authFetch('/auth/me', { method: 'GET' });
        setProfile(profData);

        const tagsResult = await authFetch('/tags/?page=1&per_page=50', { method: 'GET' });
        setTags(tagsResult.items || tagsResult);
      } catch (err) {
        if (err.status === 401) {
          handleLogout();
          return;
        }
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [user, authLoading, navigate, handleLogout]);

  useEffect(() => {
    let currentUrl = null;

    const loadQrPreview = async () => {
      if (!previewTag) {
        setQrPreviewUrl(null);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/tags/${previewTag.id}/qr`, {
          credentials: 'include'
        });
        if (!res.ok) {
          throw new Error('Unable to load QR preview');
        }
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        currentUrl = url;
        setQrPreviewUrl(url);
      } catch (err) {
        setError(err.message);
      }
    };

    loadQrPreview();

    return () => {
      if (currentUrl) {
        URL.revokeObjectURL(currentUrl);
      }
    };
  }, [previewTag]);

  const handleCreateTag = async (e) => {
    e.preventDefault();
    if (!newLabel.trim()) return;
    setCreating(true);
    setError(null);
    setSuccess(null);

    try {
      const data = await authFetch('/tags/', {
        method: 'POST',
        body: JSON.stringify({ label: newLabel })
      });

      setTags([data, ...tags]);
      setNewLabel('');
      setSuccess('Tag created successfully!');

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
      const updated = await authFetch(`/tags/${tagId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      });
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
      const data = await authFetch('/tags/sheet', {
        method: 'POST',
        body: JSON.stringify({ tag_ids: selectedTags, layout })
      });

      pollJob(data.job_id);
    } catch (err) {
      setError(err.message);
      setJobStatus(null);
    }
  };

  const fetchMessages = useCallback(async () => {
    try {
      setMessagesLoading(true);
      const data = await authFetch('/tags/messages', { method: 'GET' });
      setMessages(data.messages || []);
    } catch {
      // silent
    } finally {
      setMessagesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'inbox') fetchMessages();
  }, [activeTab, fetchMessages]);

  const pollJob = useCallback(async (id) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/jobs/${id}`, {
          credentials: 'include'
        });

        const contentType = res.headers.get('content-type');
        if (res.ok && contentType === 'application/pdf') {
          setJobStatus('completed');
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `sheet_${id}.pdf`;
          document.body.appendChild(a);
          a.click();
          a.remove();
          setSelectedTags([]);
          return true;
        }

        if (!res.ok) {
          throw new Error('Failed to get job status');
        }

        const data = await res.json();
        if (data.status === 'processing') {
          setJobStatus('processing');
        } else if (data.status === 'failed') {
          setJobStatus('failed');
          return true;
        }

        return false;
      } catch (err) {
        setError(err.message);
        setJobStatus('failed');
        return true;
      }
    };

    const interval = setInterval(async () => {
      const stop = await checkStatus();
      if (stop) clearInterval(interval);
    }, 1000);
    pollIntervalRef.current = interval;
  }, []);

  const handleDownloadSinglePdf = (tagId) => {
    fetch(`${API_BASE}/tags/${tagId}/pdf`, {
      credentials: 'include'
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error('Failed to download PDF');
        }
        return res.blob();
      })
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

  if (authLoading || loading) {
    return (
      <div className="loading-container">
        <Loader2 className="spinner" size={48} color="#df71f7" />
        <p style={{ color: 'var(--text-secondary)' }}>Loading Workspace...</p>
      </div>
    );
  }

  const activeCount = tags.filter(t => t.status === 'active').length;
  const isFree = profile?.plan === 'free';
  const tagLimit = isFree ? 2 : '∞';
  const tagLimitPercent = isFree ? Math.min((activeCount / 2) * 100, 100) : 50;

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={20} />
          </div>
          <div className="brand-text">
            <h1>TagMaster Pro</h1>
            <span>Workspace</span>
          </div>
        </div>

        <nav className="nav-menu">
          <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <LayoutDashboard size={18} />
            Dashboard
          </div>
          <div className={`nav-item ${activeTab === 'inbox' ? 'active' : ''}`} onClick={() => setActiveTab('inbox')}>
            <MessageSquare size={18} />
            Inbox {messages.length > 0 && <span className="badge-count">{messages.length}</span>}
          </div>
        </nav>

        <div className="sidebar-bottom">
          <div className="upgrade-card">
            <h4>Storage</h4>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${tagLimitPercent}%` }}></div>
            </div>
            <p>{activeCount} / {tagLimit} active tags used</p>
          </div>

          <div className="utility-nav">
            <div className="nav-item" onClick={handleLogout}>
              <LogOut size={16} />
              Logout
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        {/* Header */}
        <header className="top-header">
          <div className="page-title">
            <h2>{activeTab === 'inbox' ? 'Inbox' : 'Dashboard'}</h2>
            <p>{activeTab === 'inbox' ? 'Messages from people who found your items' : 'Manage your registered items and tags'}</p>
          </div>

          <div className="user-controls">
            <div className="user-profile">
              <div className="user-info">
                <div className="user-email">{profile?.email}</div>
                <span className="plan-badge">{profile?.plan}</span>
              </div>
              <div className="avatar" style={{
                background: `linear-gradient(135deg, var(--accent-magenta-light), var(--accent-magenta))`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '14px',
                fontWeight: 600
              }}>
                {profile?.email?.charAt(0).toUpperCase() || <User size={18} />}
              </div>
            </div>
          </div>
        </header>

        {/* Notifications */}
        {error && (
          <div className="alert alert-error">
            <AlertTriangle size={18} />
            <p>{error}</p>
          </div>
        )}

        {success && (
          <div className="alert alert-success">
            <ShieldCheck size={18} />
            <p>{success}</p>
          </div>
        )}

        {activeTab === 'inbox' ? (
          <div className="panel">
            <div className="panel-header">
              <h3>Messages from Finders</h3>
              <button className="btn-primary" style={{width:'auto',padding:'8px 16px',fontSize:'13px'}} onClick={fetchMessages} disabled={messagesLoading}>
                {messagesLoading ? <Loader2 className="spinner" size={16} /> : null} Refresh
              </button>
            </div>
            {messages.length === 0 ? (
              <div className="empty-slot">
                <MessageSquare size={36} />
                <p>No messages yet.</p>
                <p style={{fontSize:'12px'}}>When someone finds your item and sends a message, it will appear here.</p>
              </div>
            ) : (
              <div className="item-list">
                {messages.map((msg) => (
                  <div key={msg.id} className="list-item" style={{flexDirection:'column',alignItems:'stretch',gap:'8px'}}>
                    <div className="item-details">
                      <div className="item-title-row">
                        <h4>{msg.tag_label}</h4>
                        <span className="badge active">New</span>
                      </div>
                    </div>
                    <div style={{background:'var(--bg-tertiary)',padding:'12px',borderRadius:'8px',fontSize:'14px'}}>
                      {msg.message || <em style={{color:'var(--text-secondary)'}}>No message</em>}
                    </div>
                    <div className="item-controls" style={{justifyContent:'space-between'}}>
                      <a href={`tel:${msg.finder_phone}`} className="btn-primary" style={{width:'auto',padding:'8px 16px',fontSize:'13px',textDecoration:'none'}}>
                        Call {msg.finder_phone}
                      </a>
                      <span style={{fontSize:'12px',color:'var(--text-secondary)'}}>
                        {new Date(msg.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
        <>
        {/* Stats Row */}
        <div className="stats-row">
          <div className="stat-card">
            <h3>Total Tags</h3>
            <div className="stat-value">{tags.length}</div>
          </div>
          <div className="stat-card">
            <h3>Active / Limit</h3>
            <div className="stat-value">
              {activeCount}
              <span className="stat-sub">/ {tagLimit}</span>
            </div>
          </div>
          <div className="stat-card">
            <h3>Status Check</h3>
            <div className="status-check">
              <ShieldCheck size={20} />
              All Secure
            </div>
          </div>
        </div>

        {/* Main Grid */}
        <div className="dashboard-grid">
          {/* Left Column */}
          <div className="left-column">
            <div className="panel">
              <div className="panel-header">
                <h3>Your Registered Items</h3>
                {selectedTags.length > 0 && (
                  <div className="bulk-actions">
                    <select
                      value={layout}
                      onChange={(e) => setLayout(parseInt(e.target.value))}
                      className="status-dropdown"
                    >
                      <option value={6}>6 per page</option>
                      <option value={12}>12 per page</option>
                    </select>
                    <button
                      onClick={handleGenerateSheet}
                      className="btn-primary"
                      style={{ width: 'auto', padding: '8px 16px', fontSize: '13px' }}
                      disabled={jobStatus === 'pending' || jobStatus === 'processing'}
                    >
                      {jobStatus === 'pending' || jobStatus === 'processing' ? (
                        <><Loader2 className="spinner" size={16} /> Printing...</>
                      ) : (
                        <><Download size={16} /> Print Sheet ({selectedTags.length})</>
                      )}
                    </button>
                  </div>
                )}
              </div>

              {tags.length === 0 ? (
                <div className="empty-slot">
                  <TagIcon size={36} />
                  <p>No items registered yet.</p>
                  <p style={{ fontSize: '12px' }}>Register a tag on the right to get started.</p>
                </div>
              ) : (
                <div className="item-list">
                  {tags.map((tag) => (
                    <div key={tag.id} className="list-item">
                      <input
                        type="checkbox"
                        className="item-checkbox"
                        checked={selectedTags.includes(tag.id)}
                        onChange={() => handleToggleSelect(tag.id)}
                      />
                      <div className="item-details">
                        <div className="item-title-row">
                          <h4>{tag.label}</h4>
                          <span className={`badge ${tag.status}`}>
                            {tag.status.replace('_', ' ')}
                          </span>
                        </div>
                        <span className="item-meta">ID: {tag.id.slice(0, 8)}...</span>
                      </div>

                      <div className="item-controls">
                        <select
                          value={tag.status}
                          onChange={(e) => handleStatusChange(tag.id, e.target.value)}
                          className="status-dropdown"
                        >
                          <option value="active">Active</option>
                          <option value="paused">Paused</option>
                          <option value="lost_confirmed">Lost</option>
                        </select>

                        <button
                          onClick={() => setPreviewTag(tag)}
                          className="icon-btn-secondary"
                          title="View QR Code"
                        >
                          <QrCode size={18} />
                        </button>

                        <button
                          onClick={() => handleDownloadSinglePdf(tag.id)}
                          className="icon-btn-secondary"
                          title="Download PDF"
                        >
                          <Download size={18} />
                        </button>

                        <a
                          href={`/t/${tag.id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="icon-btn-secondary"
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
          </div>

          {/* Right Column */}
          <div className="right-column">
            <div className="panel">
              <div className="panel-header">
                <h3>Register New Tag</h3>
              </div>

              {isFree && activeCount >= 2 && (
                <div className="limit-banner">
                  <p>Free Tier Limit Reached</p>
                  <p>You have reached the maximum of 2 active tags. Pause an item to free up a slot, or upgrade.</p>
                </div>
              )}

              <form onSubmit={handleCreateTag}>
                <div className="form-group">
                  <label>Item Label</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Backpack, Work Keys"
                    value={newLabel}
                    onChange={(e) => setNewLabel(e.target.value)}
                    className="form-control"
                  />
                </div>

                <button
                  type="submit"
                  className="btn-primary"
                  disabled={creating || (isFree && activeCount >= 2)}
                >
                  {creating ? (
                    <><Loader2 className="spinner" size={18} /> Registering...</>
                  ) : (
                    <><Plus size={18} /> Register Tag</>
                  )}
                </button>
              </form>

              <p className="disclaimer">
                Each QR code is uniquely generated and encrypted. Your personal data remains private.
              </p>
            </div>

            <div className="insights-panel">
              <div className="insights-header">
                <ShieldCheck size={18} color="var(--accent-magenta-light)" />
                Pro Tip
              </div>
              <p>
                Print your QR tags and attach them to valuables. When someone scans the code,
                they&apos;ll be able to contact you <strong>without seeing your phone number</strong>.
              </p>

            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="app-footer">
          <p>&copy; {new Date().getFullYear()} TagMaster Pro. All rights reserved.</p>
        </footer>
        </>)}
      </main>

      {/* QR Preview Modal */}
      {previewTag && (
        <div className="modal-overlay" onClick={() => setPreviewTag(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>QR Code: {previewTag.label}</h2>
              <button onClick={() => setPreviewTag(null)} className="modal-close">
                <X size={18} />
              </button>
            </div>

            <div style={{
              background: '#fff',
              padding: '16px',
              borderRadius: '12px',
              display: 'inline-block',
              margin: '16px 0'
            }}>
              <img
                src={qrPreviewUrl || ''}
                alt="QR Code"
                style={{ width: '220px', height: '220px', display: 'block' }}
              />
            </div>

            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
              Anyone who scans this QR code will see a form to contact you securely without revealing your phone number.
            </p>

            <button
              onClick={() => handleDownloadSinglePdf(previewTag.id)}
              className="btn-primary"
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
