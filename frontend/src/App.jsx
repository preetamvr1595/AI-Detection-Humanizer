import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import ToolsHubPage from './pages/ToolsHubPage'
import AIDetectorPage from './pages/tools/AIDetectorPage'
import HumanizerPage from './pages/tools/HumanizerPage'
import PlagiarismCheckerPage from './pages/tools/PlagiarismCheckerPage'
import GrammarCheckerPage from './pages/tools/GrammarCheckerPage'
import DashboardPage from './pages/DashboardPage'
import ReportPage from './pages/ReportPage'
import AdminPage from './pages/AdminPage'
import SecurityPage from './pages/SecurityPage'
import './App.css'

function Protected({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return children
}

function AdminOnly({ children }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'Admin') return <Navigate to="/" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Protected><ToolsHubPage /></Protected>} />
          <Route path="/tools/ai-detector" element={<Protected><AIDetectorPage /></Protected>} />
          <Route path="/tools/humanizer" element={<Protected><HumanizerPage /></Protected>} />
          <Route path="/tools/plagiarism" element={<Protected><PlagiarismCheckerPage /></Protected>} />
          <Route path="/tools/grammar" element={<Protected><GrammarCheckerPage /></Protected>} />
          <Route path="/documents" element={<Protected><DashboardPage /></Protected>} />
          <Route path="/security" element={<Protected><SecurityPage /></Protected>} />
          <Route path="/reports/:jobId" element={<Protected><ReportPage /></Protected>} />
          <Route path="/admin" element={<AdminOnly><AdminPage /></AdminOnly>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
