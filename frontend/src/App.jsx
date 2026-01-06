import React from 'react';
import { Routes, Route } from 'react-router-dom';
import BiomarkerTablePage from './pages/BiomarkerTablePage';
import PaperDetailPage from './pages/PaperDetailPage';
import BiomarkerPage from './pages/BiomarkerPage';

import ScrollToTop from './components/ScrollToTop';

function App() {
  return (
    <>
      <ScrollToTop />
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'radial-gradient(circle at 0% 0%, #fff1f2 0%, transparent 50%), radial-gradient(circle at 100% 0%, #fdf4ff 0%, transparent 50%), radial-gradient(circle at 100% 100%, #f0f9ff 0%, transparent 50%), radial-gradient(circle at 0% 100%, #f5f3ff 0%, transparent 50%)',
        backgroundAttachment: 'fixed'
      }}>


        <main style={{ flex: 1, width: '100%' }}>
          <Routes>
            <Route path="/" element={<BiomarkerTablePage />} />
            <Route path="/paper/:id" element={<PaperDetailPage />} />
            <Route path="/biomarker/:name" element={<BiomarkerPage />} />
          </Routes>
        </main>
      </div>
    </>
  );
}

export default App;
