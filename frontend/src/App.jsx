import { Routes, Route, Navigate } from 'react-router-dom';
import PublicTagView from './pages/PublicTagView';
import Dashboard from './pages/Dashboard';
import AuthLanding from './pages/AuthLanding';
import ResetPassword from './pages/ResetPassword';
import StaticPage from './pages/StaticPage';
import NotFound from './pages/NotFound';
import ErrorBoundary from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/login" element={<AuthLanding />} />
        <Route path="/signup" element={<AuthLanding />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/how-it-works" element={<StaticPage />} />
        <Route path="/faq" element={<StaticPage />} />
        <Route path="/privacy" element={<StaticPage />} />
        <Route path="/terms" element={<StaticPage />} />
        <Route path="/t/:id" element={<PublicTagView />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </ErrorBoundary>
  );
}

export default App;
