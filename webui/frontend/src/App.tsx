import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Header from './components/Header'
import HomePage from './pages/HomePage'
import ScanView from './pages/ScanView'
import ResultsBrowser from './pages/ResultsBrowser'
import BatchProgressPage from './pages/BatchProgressPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Header />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/scan" element={<ScanView />} />
          <Route path="/results" element={<ResultsBrowser />} />
          <Route path="/bulk" element={<BatchProgressPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
