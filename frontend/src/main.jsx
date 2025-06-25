import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
// === YENİ KOD BAŞLANGICI ===
import { AuthProvider } from './context/AuthContext.jsx'
// === YENİ KOD SONU ===

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/* DEĞİŞTİRİLDİ */}
    <AuthProvider>
      <App />
    </AuthProvider>
    {/* DEĞİŞTİRİLDİ */}
  </StrictMode>,
)