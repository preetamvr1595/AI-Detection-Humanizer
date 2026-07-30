import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import Layout from '../components/Layout'

export default function DashboardPage() {
  const [jobs, setJobs] = useState([])
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const fileInput = useRef(null)
  const navigate = useNavigate()

  async function loadJobs() {
    const { data } = await api.get('/documents/jobs')
    setJobs(data)
  }

  useEffect(() => {
    loadJobs()
  }, [])

  async function handleFile(file) {
    if (!file) return
    setError('')
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const { data } = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await loadJobs()
      navigate(`/reports/${data.job_id}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try a different file.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <Layout>
      <div className="page-header">
        <h1>Document verification</h1>
        <p>Upload a document to run it through the real ClamAV + YARA security gateway, then every analysis module at once, with a signed and encrypted PDF report.</p>
      </div>

      <div
        className={`dropzone ${dragOver ? 'drag-over' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          handleFile(e.dataTransfer.files[0])
        }}
        onClick={() => fileInput.current?.click()}
      >
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.docx,.txt"
          hidden
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {uploading ? (
          <p>Scanning and analyzing your document…</p>
        ) : (
          <>
            <p className="dropzone-title">Drag &amp; drop a file here, or click to browse</p>
            <p className="dropzone-sub">PDF, DOCX, or TXT — scanned for malware before analysis</p>
          </>
        )}
      </div>

      {error && <div className="form-error">{error}</div>}

      <h2 className="section-title">Recent submissions</h2>
      <div className="job-list">
        {jobs.length === 0 && <p className="empty-state">No submissions yet — upload a document above to get started.</p>}
        {jobs.map((job) => (
          <div className="job-row" key={job.job_id} onClick={() => navigate(`/reports/${job.job_id}`)}>
            <div className="job-name">{job.file_name || 'Document'}</div>
            <div className={`status-pill status-${job.status.toLowerCase()}`}>{job.status}</div>
            {job.status === 'COMPLETE' && (
              <div className="job-scores">
                <span className="score ai">AI {job.ai_score}%</span>
                <span className="score plag">Plagiarism {job.plagiarism_score}%</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </Layout>
  )
}
