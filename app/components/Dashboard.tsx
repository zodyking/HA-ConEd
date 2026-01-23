'use client'

import { useState, useEffect, useCallback } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface LogEntry {
  id: number
  timestamp: string
  level: string
  message: string
}

interface ScrapedData {
  id: number
  timestamp: string
  data: any
  status: string
  error_message?: string
}

export default function Dashboard() {
  const [isRunning, setIsRunning] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [scrapedData, setScrapedData] = useState<ScrapedData[]>([])
  const [activeView, setActiveView] = useState<'logs' | 'data'>('logs')
  const [status, setStatus] = useState<'stopped' | 'running' | 'error'>('stopped')
  const [screenshotUrl, setScreenshotUrl] = useState<string>('')
  const [lastLogCount, setLastLogCount] = useState(0)
  const [screenshotKey, setScreenshotKey] = useState(0)

  const loadScreenshot = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/screenshot/latest?t=${Date.now()}`, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      })
      if (response.ok) {
        const blob = await response.blob()
        // Always create new URL to force reload
        setScreenshotUrl(prev => {
          if (prev) {
            URL.revokeObjectURL(prev)
          }
          const newUrl = URL.createObjectURL(blob)
          setScreenshotKey(prev => prev + 1) // Increment key to force image reload
          return newUrl
        })
      } else if (response.status === 404) {
        // Screenshot not available yet, but don't clear existing one
      }
    } catch (error) {
      // Screenshot not available yet, ignore
    }
  }, [])

  const loadLogs = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/logs?limit=100`)
      if (response.ok) {
        const data = await response.json()
        setLogs(data.logs.reverse()) // Show newest at bottom
      }
    } catch (error) {
      console.error('Failed to load logs:', error)
    }
  }, [])

  const loadScrapedData = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/scraped-data?limit=50`)
      if (response.ok) {
        const data = await response.json()
        setScrapedData(data.data)
      }
    } catch (error) {
      console.error('Failed to load scraped data:', error)
    }
  }

  useEffect(() => {
    loadLogs()
    loadScrapedData()
    
    // Refresh logs every 1 second for faster updates
    const logInterval = setInterval(loadLogs, 1000)
    
    // Cleanup screenshot URL on unmount
    return () => {
      clearInterval(logInterval)
      if (screenshotUrl) {
        URL.revokeObjectURL(screenshotUrl)
      }
    }
  }, [loadLogs, screenshotUrl])

  // Reload screenshot when logs change (new step happened)
  useEffect(() => {
    if (logs.length > lastLogCount) {
      setLastLogCount(logs.length)
      // New log entry detected - reload screenshot immediately
      loadScreenshot()
    }
  }, [logs.length, lastLogCount, loadScreenshot])

  // Poll for screenshots continuously while scraper is running
  useEffect(() => {
    if (isRunning || status === 'running') {
      loadScreenshot()
      const screenshotInterval = setInterval(loadScreenshot, 500) // Update every 500ms
      return () => clearInterval(screenshotInterval)
    }
  }, [isRunning, status, loadScreenshot])

  const handleStartScraper = async () => {
    setIsRunning(true)
    setStatus('running')
    // Clear previous screenshot URL
    if (screenshotUrl) {
      URL.revokeObjectURL(screenshotUrl)
      setScreenshotUrl('')
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/scrape`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (response.ok) {
        const result = await response.json()
        setStatus(result.success ? 'stopped' : 'error')
        // Load final screenshot
        await loadScreenshot()
        // Refresh data after scraping
        setTimeout(() => {
          loadScrapedData()
          loadLogs()
        }, 1000)
      } else {
        let errorMessage = 'Unknown error occurred'
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorData.error || errorData.message || 'Unknown error occurred'
        } catch {
          // If response is not JSON, try to get text
          try {
            const text = await response.text()
            errorMessage = text || `HTTP ${response.status}: ${response.statusText}`
          } catch {
            errorMessage = `HTTP ${response.status}: ${response.statusText}`
          }
        }
        setStatus('error')
        console.error('Scraper error:', errorMessage)
        // Still try to load screenshot in case there's a partial result
        await loadScreenshot()
      }
    } catch (error) {
      setStatus('error')
      console.error('Failed to start scraper:', error)
      // Still try to load screenshot
      await loadScreenshot()
    } finally {
      setIsRunning(false)
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleString()
    } catch {
      return timestamp
    }
  }

  const getLogLevelClass = (level: string) => {
    switch (level.toLowerCase()) {
      case 'error':
        return 'log-level-error'
      case 'success':
        return 'log-level-success'
      case 'warning':
        return 'log-level-warning'
      default:
        return 'log-level-info'
    }
  }

  return (
    <div>
      <div className="control-panel">
        <div>
          <span className={`status-indicator ${status}`}></span>
          <span>
            Status: {status === 'running' ? 'Running' : status === 'error' ? 'Error' : 'Stopped'}
          </span>
        </div>
        <button
          className="primary"
          onClick={handleStartScraper}
          disabled={isRunning}
        >
          {isRunning ? 'Running...' : 'Start Scraper'}
        </button>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeView === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveView('logs')}
        >
          Logs
        </button>
        <button
          className={`tab ${activeView === 'data' ? 'active' : ''}`}
          onClick={() => setActiveView('data')}
        >
          Scraped Data
        </button>
      </div>

      {activeView === 'logs' && (
        <div className="tab-content active">
          <div className="log-panel">
            {logs.length === 0 ? (
              <div>No logs yet. Start the scraper to see activity.</div>
            ) : (
              logs.map((log) => (
                <div key={log.id} className="log-entry">
                  <span className="log-time">{formatTimestamp(log.timestamp)}</span>
                  <span className={getLogLevelClass(log.level)}>[{log.level.toUpperCase()}]</span>
                  <span>{log.message}</span>
                </div>
              ))
            )}
          </div>
          
          {/* Live Browser Preview */}
          <div style={{ marginTop: '1rem' }}>
            <h3 style={{ marginBottom: '0.5rem', fontSize: '0.9rem', fontWeight: 500 }}>Live Browser Preview</h3>
            <div style={{ 
              border: '1px solid #e0e0e0', 
              borderRadius: '4px', 
              overflow: 'hidden',
              background: '#f9f9f9',
              maxHeight: '400px',
              overflowY: 'auto',
              minHeight: '200px'
            }}>
              {screenshotUrl ? (
                <img 
                  key={`screenshot-${screenshotKey}`}
                  src={screenshotUrl} 
                  alt="Browser preview" 
                  style={{ 
                    width: '100%', 
                    height: 'auto',
                    display: 'block'
                  }} 
                />
              ) : (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
                  {isRunning ? 'Waiting for browser screenshot...' : 'No screenshot available. Start the scraper to see live preview.'}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {activeView === 'data' && (
        <div className="tab-content active">
          {scrapedData.length === 0 ? (
            <div>No scraped data yet. Start the scraper to collect data.</div>
          ) : (
            <div>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Status</th>
                    <th>Data Preview</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {scrapedData.map((item) => (
                    <tr key={item.id}>
                      <td>{formatTimestamp(item.timestamp)}</td>
                      <td>
                        <span className={`status-indicator ${item.status === 'success' ? 'running' : 'error'}`}></span>
                        {item.status}
                      </td>
                      <td>
                        <pre style={{ fontSize: '0.8rem', maxWidth: '400px', overflow: 'auto' }}>
                          {JSON.stringify(item.data, null, 2).substring(0, 200)}
                          {JSON.stringify(item.data, null, 2).length > 200 ? '...' : ''}
                        </pre>
                      </td>
                      <td>{item.error_message || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
