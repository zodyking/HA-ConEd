'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

  const loadLogs = useCallback(async () => {
    try {
      let response: Response | null = null
      
      try {
        response = await fetch(`${API_BASE_URL}/api/logs?limit=100`, {
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

  const loadScrapedData = useCallback(async () => {
    // Removed - scraped data is now in AccountLedger component
  }, [])

  useEffect(() => {
    loadLogs()
    
    // Refresh logs every 1 second for faster updates
    const logInterval = setInterval(loadLogs, 1000)
    
    return () => {
      clearInterval(logInterval)
    }
  }, [loadLogs])

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
      await fetch(`${API_BASE_URL}/api/logs`, {
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
      
      const response = await safeFetch(`${API_BASE_URL}/api/scrape`, {
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

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      const dateStr = date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      })
      const timeStr = date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit',
        hour12: true
      })
      return { date: dateStr, time: timeStr }
    } catch {
      return { date: timestamp, time: '' }
    }
  }

  const formatTimestampForLogs = (timestamp: string) => {
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
                  <img src="/images/ajax-loader.gif" alt="Loading" className="ha-loader-inline" />
                  Running...
                </>
              ) : (
                'Start Scraper'
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="ha-card ha-card-logs">
        <div className="ha-card-header">
          <span className="ha-card-icon">📝</span>
          <span>Console Logs</span>
        </div>
        <div className="ha-card-content ha-log-container" ref={logContainerRef} style={{ flex: 1, minHeight: 0 }}>
          {logs.length === 0 ? (
            <div className="ha-empty-state">No logs yet. Start the scraper to see activity.</div>
          ) : (
            logs.map((log) => (
              <div key={log.id} className={`ha-log-entry ha-log-${log.level.toLowerCase()}`}>
                <span className="ha-log-time">{formatTimestampForLogs(log.timestamp)}</span>
                <span className={getLogLevelClass(log.level)}>[{log.level.toUpperCase()}]</span>
                <span className="ha-log-message">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
