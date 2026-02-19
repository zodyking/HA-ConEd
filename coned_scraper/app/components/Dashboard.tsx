'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { formatDate, formatTime, formatTimestamp } from '../lib/timezone'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api'

interface LogEntry {
  id: number
  timestamp: string
  level: string
  message: string
}

export default function Dashboard() {
  const [isRunning, setIsRunning] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [status, setStatus] = useState<'stopped' | 'running' | 'error'>('stopped')
  const logContainerRef = useRef<HTMLDivElement>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const previewRefreshIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const loadLogs = useCallback(async () => {
    try {
      let response: Response | null = null
      
      try {
        response = await fetch(`${API_BASE_URL}/logs?limit=100`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      } catch (fetchError) {
        // Network error - service might not be running
        console.error('Network error loading logs:', fetchError)
        // Don't set error state for logs, just keep existing logs
        return
      }
      
      if (response && response.ok) {
        try {
          const data = await response.json()
          setLogs((data.logs || []).reverse()) // Show newest at bottom
        } catch (jsonError) {
          console.error('Failed to parse logs JSON:', jsonError)
          setLogs([])
        }
      } else if (response) {
        // HTTP error response
        console.error('Failed to load logs:', response.status, response.statusText)
      }
      // If response is null (network error), keep existing logs
    } catch (error) {
      console.error('Failed to load logs:', error)
      // Keep existing logs on error
    }
  }, [])

  const loadLivePreview = useCallback(async () => {
    try {
      const timestamp = new Date().getTime()
      const url = `${API_BASE_URL}/live-preview?t=${timestamp}`
      const response = await fetch(url)
      
      if (response.ok && response.headers.get('content-type')?.startsWith('image/')) {
        const blob = await response.blob()
        const imageUrl = URL.createObjectURL(blob)
        // Revoke old URL to prevent memory leaks
        setPreviewUrl((prevUrl) => {
          if (prevUrl && prevUrl.startsWith('blob:')) {
            URL.revokeObjectURL(prevUrl)
          }
          return imageUrl
        })
      } else {
        // Preview not available yet (404 or other error)
        setPreviewUrl((prevUrl) => {
          if (prevUrl && prevUrl.startsWith('blob:')) {
            URL.revokeObjectURL(prevUrl)
          }
          return null
        })
      }
    } catch (error) {
      // Silently fail - preview might not be available
      setPreviewUrl((prevUrl) => {
        if (prevUrl && prevUrl.startsWith('blob:')) {
          URL.revokeObjectURL(prevUrl)
        }
        return null
      })
    }
  }, [])

  const loadScrapedData = useCallback(async () => {
    // Removed - scraped data is now in AccountLedger component
  }, [])

  useEffect(() => {
    loadLogs()
    loadLivePreview()
    
    // Refresh logs every 1 second for faster updates
    const logInterval = setInterval(loadLogs, 1000)
    
    // Refresh preview every 500ms when running, 2s when stopped
    const previewInterval = setInterval(loadLivePreview, isRunning ? 500 : 2000)
    previewRefreshIntervalRef.current = previewInterval
    
    return () => {
      clearInterval(logInterval)
      if (previewRefreshIntervalRef.current) {
        clearInterval(previewRefreshIntervalRef.current)
      }
    }
  }, [loadLogs, loadLivePreview, isRunning])

  // Cleanup blob URL on unmount
  useEffect(() => {
    return () => {
      if (previewUrl && previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  // Auto-scroll logs to bottom when new logs are added
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  const handleStartScraper = async () => {
    setIsRunning(true)
    setStatus('running')
    
    // Clear logs when starting a new scrape
    setLogs([])
    
    try {
      // Clear logs on the backend as well
      await fetch(`${API_BASE_URL}/logs`, {
        method: 'DELETE',
      }).catch(() => {
        // Ignore errors if endpoint doesn't exist or fails
      })
      
      // Use safeFetch helper to handle network errors
      const safeFetch = async (url: string, options?: RequestInit): Promise<Response | null> => {
        try {
          const controller = new AbortController()
          const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout
          
          const response = await fetch(url, {
            ...options,
            signal: controller.signal,
          })
          
          clearTimeout(timeoutId)
          return response
        } catch (error) {
          // Silently catch network errors
          return null
        }
      }
      
      const response = await safeFetch(`${API_BASE_URL}/scrape`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (response && response.ok) {
        const result = await response.json()
        setStatus(result.success ? 'stopped' : 'error')
        // Refresh logs after scraping
        setTimeout(() => {
          loadLogs()
        }, 1000)
      } else if (response) {
        // HTTP error response
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
        setApiError(`Scraper error: ${errorMessage}`)
        console.error('Scraper error:', errorMessage)
      } else {
        // No response (network error)
        setStatus('error')
        setApiError('Cannot connect to Python service. Make sure it\'s running on port 8000.')
        // Don't log to console - error is already shown to user via setApiError
      }
    } catch (error) {
      setStatus('error')
      setApiError('Failed to start scraper. Check console for details.')
      console.error('Failed to start scraper:', error)
    } finally {
      setIsRunning(false)
    }
  }

  const [formattedTimestamps, setFormattedTimestamps] = useState<Map<number, string>>(new Map())

  // Format timestamps when logs change
  useEffect(() => {
    const newMap = new Map<number, string>()
    for (const log of logs) {
      try {
        const formatted = formatTimestamp(log.timestamp)
        newMap.set(log.id, formatted)
      } catch {
        newMap.set(log.id, log.timestamp)
      }
    }
    setFormattedTimestamps(newMap)
  }, [logs])

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
    <div className="ha-dashboard">
      {apiError && (
        <div className="ha-card ha-card-error">
          <div className="ha-card-header">
            <span className="ha-card-icon">⚠️</span>
            <strong>API Connection Error</strong>
          </div>
          <div className="ha-card-content">{apiError}</div>
        </div>
      )}
      
      <div className="ha-card ha-card-status">
        <div className="ha-card-header">
          <span className="ha-card-icon">🔌</span>
          <span>Service Status</span>
        </div>
        <div className="ha-card-content" style={{ padding: '0.5rem 0.75rem' }}>
          <div className="ha-status-controls">
            <div className="ha-status-info">
              <span className={`ha-status-indicator ${status}`}></span>
              <span className="ha-status-text">
                {status === 'running' ? 'Running' : status === 'error' ? 'Error' : 'Stopped'}
              </span>
            </div>
            <button
              className="ha-button ha-button-primary"
              onClick={handleStartScraper}
              disabled={isRunning}
            >
              {isRunning ? (
                <>
                  <img src="images/ajax-loader.gif" alt="Loading" className="ha-loader-inline" />
                  Running...
                </>
              ) : (
                'Start Scraper'
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="ha-panels-grid">
        <div className="ha-card ha-card-logs">
          <div className="ha-card-header">
            <span className="ha-card-icon">📝</span>
            <span>Console Logs</span>
          </div>
          <div className="ha-card-content ha-log-container" ref={logContainerRef}>
            {logs.length === 0 ? (
              <div className="ha-empty-state">No logs yet. Start the scraper to see activity.</div>
            ) : (
              logs.map((log) => (
                <div key={log.id} className={`ha-log-entry ha-log-${log.level.toLowerCase()}`}>
                  <span className="ha-log-time">{formattedTimestamps.get(log.id) || log.timestamp}</span>
                  <span className={getLogLevelClass(log.level)}>[{log.level.toUpperCase()}]</span>
                  <span className="ha-log-message">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="ha-card ha-card-preview">
          <div className="ha-card-header">
            <span className="ha-card-icon">🖥️</span>
            <span>Browser Preview</span>
          </div>
          <div className="ha-card-content ha-preview-container">
            {previewUrl ? (
              <img 
                src={previewUrl} 
                alt="Browser preview" 
                style={{ 
                  maxWidth: '100%', 
                  maxHeight: '100%', 
                  objectFit: 'contain',
                  border: '1px solid #333',
                  borderRadius: '4px'
                }} 
              />
            ) : (
              <div className="ha-empty-state" style={{ textAlign: 'center', color: '#888' }}>
                {isRunning ? (
                  <>
                    <img 
                      src="images/ajax-loader.gif" 
                      alt="Loading" 
                      style={{ width: '40px', height: '40px', marginBottom: '1rem' }} 
                    />
                    <div>Waiting for browser preview...</div>
                  </>
                ) : (
                  <div>No preview available. Start the scraper to see browser activity.</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
