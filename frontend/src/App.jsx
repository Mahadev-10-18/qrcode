import { Routes, Route } from 'react-router-dom';
import PublicTagView from './pages/PublicTagView';
import Dashboard from './pages/Dashboard';
import Login from './pages/Login';
import Signup from './pages/Signup';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/t/:id" element={<PublicTagView />} />
    </Routes>
  );
}

export default App;
