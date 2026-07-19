import { Link } from 'react-router-dom';
import { SearchX } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="error-view">
      <SearchX size={64} color="var(--text-secondary)" />
      <h1>404 — Page Not Found</h1>
      <p>The page you are looking for does not exist or has been moved.</p>
      <Link to="/" className="btn-primary" style={{ width: 'auto', padding: '10px 24px', marginTop: '8px' }}>
        Back to Dashboard
      </Link>
    </div>
  );
}
