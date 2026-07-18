import { Routes, Route } from 'react-router-dom';
import PublicTagView from './pages/PublicTagView';

function App() {
  return (
    <Routes>
      <Route path="/t/:id" element={<PublicTagView />} />
      <Route path="/" element={
        <div style={{ textAlign: 'center', marginTop: '20vh' }}>
          <h1>QR Tag Manager</h1>
          <p>Scan a QR code to view a tag.</p>
        </div>
      } />
    </Routes>
  );
}

export default App;
