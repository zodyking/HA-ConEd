'use client'

import { useState, useEffect } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Credentials {
  username: string
  password: string
  totp_secret: string
}

interface TOTPResponse {
  code: string
  time_remaining: number
}

export default function Settings() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [totpSecret, setTotpSecret] = useState('')
  const [currentTOTP, setCurrentTOTP] = useState<string>('')
  const [timeRemaining, setTimeRemaining] = useState<number>(30)
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'credentials' | 'automated'>('credentials')
  
  // Show/hide password states
  const [showUsername, setShowUsername] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showTotpSecret, setShowTotpSecret] = useState(false)
  
  // Helper function to mask text
  const maskText = (text: string) => {
    if (!text) return ''
    return '•'.repeat(text.length)
  }

  // Load saved credentials on mount
  useEffect(() => {
    loadSettings()
  }, [])

  // Update TOTP code every second
  useEffect(() => {
    if (!totpSecret || totpSecret.trim() === '') {
      setCurrentTOTP('')
      setTimeRemaining(30)
      return
    }

    const updateTOTP = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/totp`)
        if (response.ok) {
          const data: TOTPResponse = await response.json()
          setCurrentTOTP(data.code)
          setTimeRemaining(data.time_remaining)
        } else {
          // Handle different error status codes
          let errorMessage = 'Error'
          try {
            const errorData = await response.json()
            if (response.status === 404) {
              errorMessage = 'No credentials saved'
            } else if (response.status === 400) {
              errorMessage = errorData.detail || 'Invalid TOTP secret'
            } else {
              errorMessage = errorData.detail || 'Failed to fetch TOTP'
            }
          } catch {
            // If response is not JSON, use status text
            errorMessage = response.status === 404 ? 'No credentials saved' : 'Error'
          }
          setCurrentTOTP(errorMessage)
        }
      } catch (error) {
        console.error('Failed to fetch TOTP:', error)
        setCurrentTOTP('Connection Error')
      }
    }

    // Initial fetch immediately
    updateTOTP()

    // Update every second
    const interval = setInterval(updateTOTP, 1000)

    return () => clearInterval(interval)
  }, [totpSecret])

  const loadSettings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings`)
      if (response.ok) {
        const data: Credentials = await response.json()
        setUsername(data.username || '')
        setPassword('') // Don't show saved password
        setTotpSecret(data.totp_secret || '')
        
        // Reset show states when loading
        setShowUsername(false)
        setShowPassword(false)
        setShowTotpSecret(false)
        
        // If TOTP secret exists, trigger TOTP fetch immediately
        // Note: The useEffect will handle TOTP updates automatically
        // so we don't need to fetch here
      } else {
        console.error('Failed to load settings:', await response.text())
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
      setMessage({ type: 'error', text: 'Failed to connect to API. Make sure the Python service is running on port 8000.' })
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage(null)

    try {
      const response = await fetch(`${API_BASE_URL}/api/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password: password || null, // Send null if empty to keep existing password
          totp_secret: totpSecret,
        }),
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Settings saved successfully!' })
        // Reload to get updated TOTP
        if (totpSecret) {
          const totpResponse = await fetch(`${API_BASE_URL}/api/totp`)
          if (totpResponse.ok) {
            const totpData: TOTPResponse = await totpResponse.json()
            setCurrentTOTP(totpData.code)
            setTimeRemaining(totpData.time_remaining)
          }
        }
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to save settings' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to connect to API. Make sure the Python service is running.' })
    } finally {
      setIsLoading(false)
    }
  }


  return (
    <div className="ha-settings">
      <div className="ha-tabs">
        <button
          type="button"
          className={`ha-tab ${activeTab === 'credentials' ? 'active' : ''}`}
          onClick={() => setActiveTab('credentials')}
        >
          🔐 Credentials
        </button>
        <button
          type="button"
          className={`ha-tab ${activeTab === 'automated' ? 'active' : ''}`}
          onClick={() => setActiveTab('automated')}
        >
          ⏰ Automated Scrape
        </button>
      </div>

      {activeTab === 'credentials' && (
        <div className="ha-card">
          <div className="ha-card-header">
            <span className="ha-card-icon">🔐</span>
            <span>Credentials</span>
          </div>
          <div className="ha-card-content">
            <form onSubmit={handleSave}>
              <div className="ha-form-group">
                <label htmlFor="username" className="ha-form-label">Username / Email</label>
                <div className="password-input-wrapper">
                  <input
                    type={showUsername ? "text" : "password"}
                    id="username"
                    className="ha-form-input"
                    value={showUsername ? username : (username ? maskText(username) : '')}
                    onChange={(e) => setUsername(e.target.value)}
                    onFocus={() => setShowUsername(true)}
                    placeholder="your.email@example.com"
                    required
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowUsername(!showUsername)}
                    tabIndex={-1}
                    aria-label={showUsername ? "Hide username" : "Show username"}
                  >
                    {showUsername ? '👁️' : '👁️‍🗨️'}
                  </button>
                </div>
              </div>

              <div className="ha-form-group">
                <label htmlFor="password" className="ha-form-label">Password</label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    className="ha-form-input"
                    value={showPassword ? password : (password ? maskText(password) : '')}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setShowPassword(true)}
                    placeholder={password ? '' : 'Enter password to update'}
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? '👁️' : '👁️‍🗨️'}
                  </button>
                </div>
                <div className="info-text">
                  Leave empty to keep existing password
                </div>
              </div>

              <div className="ha-form-group">
                <label htmlFor="totp_secret" className="ha-form-label">TOTP Secret</label>
                <div className="password-input-wrapper">
                  <input
                    type={showTotpSecret ? "text" : "password"}
                    id="totp_secret"
                    className="ha-form-input"
                    value={showTotpSecret ? totpSecret : (totpSecret ? maskText(totpSecret) : '')}
                    onChange={(e) => setTotpSecret(e.target.value)}
                    onFocus={() => setShowTotpSecret(true)}
                    placeholder="JBSWY3DPEHPK3PXP"
                    required
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowTotpSecret(!showTotpSecret)}
                    tabIndex={-1}
                    aria-label={showTotpSecret ? "Hide TOTP secret" : "Show TOTP secret"}
                  >
                    {showTotpSecret ? '👁️' : '👁️‍🗨️'}
                  </button>
                </div>
                <div className="info-text">
                  Enter your TOTP secret (base32 encoded string, same as Google Authenticator)
                </div>
              </div>

              <button type="submit" className="ha-button ha-button-primary" disabled={isLoading}>
                {isLoading ? 'Saving...' : 'Save Settings'}
              </button>
            </form>

            {totpSecret && (
              <div className="ha-totp-display">
                <h3>Current TOTP Code</h3>
                <div className="ha-totp-code">{currentTOTP || 'Loading...'}</div>
                <div className="ha-totp-time">
                  Expires in {timeRemaining} seconds
                </div>
              </div>
            )}

            {message && (
              <div className={`ha-card ha-card-${message.type === 'error' ? 'error' : 'status'}`} style={{ marginTop: '1rem' }}>
                <div className="ha-card-content">
                  {message.text}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'automated' && (
        <AutomatedScrapeTab />
      )}
    </div>
  )
}

function AutomatedScrapeTab() {
  const [enabled, setEnabled] = useState(false)
  const [hours, setHours] = useState('0')
  const [minutes, setMinutes] = useState('0')
  const [seconds, setSeconds] = useState('0')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [status, setStatus] = useState<{ enabled: boolean, frequency: number, nextRun?: string } | null>(null)

  useEffect(() => {
    loadSchedule()
  }, [])

  const loadSchedule = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/automated-schedule`)
      if (response.ok) {
        const data = await response.json()
        setStatus(data)
        if (data.enabled) {
          setEnabled(true)
          const totalSeconds = data.frequency || 0
          setHours(Math.floor(totalSeconds / 3600).toString())
          setMinutes(Math.floor((totalSeconds % 3600) / 60).toString())
          setSeconds((totalSeconds % 60).toString())
        }
      }
    } catch (error) {
      console.error('Failed to load schedule:', error)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage(null)

    try {
      const totalSeconds = parseInt(hours) * 3600 + parseInt(minutes) * 60 + parseInt(seconds)
      
      if (totalSeconds <= 0) {
        setMessage({ type: 'error', text: 'Frequency must be greater than 0' })
        setIsLoading(false)
        return
      }

      const response = await fetch(`${API_BASE_URL}/api/automated-schedule`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          enabled,
          frequency: totalSeconds
        }),
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Automated scrape schedule saved successfully!' })
        await loadSchedule()
      } else {
        const errorData = await response.json().catch(() => ({}))
        setMessage({ type: 'error', text: errorData.error || 'Failed to save schedule' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to connect to API. Make sure the Python service is running.' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="ha-card">
      <div className="ha-card-header">
        <span className="ha-card-icon">⏰</span>
        <span>Automated Scrape Schedule</span>
      </div>
      <div className="ha-card-content">
        <form onSubmit={handleSave}>
          <div className="ha-form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
              <span>Enable Automated Scraping</span>
            </label>
          </div>

          {enabled && (
            <>
              <div className="ha-form-group">
                <label className="ha-form-label">Scrape Frequency</label>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <label htmlFor="hours" className="ha-form-label" style={{ fontSize: '0.85rem' }}>Hours</label>
                    <input
                      type="number"
                      id="hours"
                      className="ha-form-input"
                      min="0"
                      max="23"
                      value={hours}
                      onChange={(e) => setHours(e.target.value)}
                      required
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label htmlFor="minutes" className="ha-form-label" style={{ fontSize: '0.85rem' }}>Minutes</label>
                    <input
                      type="number"
                      id="minutes"
                      className="ha-form-input"
                      min="0"
                      max="59"
                      value={minutes}
                      onChange={(e) => setMinutes(e.target.value)}
                      required
                    />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label htmlFor="seconds" className="ha-form-label" style={{ fontSize: '0.85rem' }}>Seconds</label>
                    <input
                      type="number"
                      id="seconds"
                      className="ha-form-input"
                      min="0"
                      max="59"
                      value={seconds}
                      onChange={(e) => setSeconds(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="info-text" style={{ marginTop: '0.5rem' }}>
                  Scraper will run automatically every {hours}:{String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
                </div>
              </div>
            </>
          )}

          <button type="submit" className="ha-button ha-button-primary" disabled={isLoading}>
            {isLoading ? 'Saving...' : 'Save Schedule'}
          </button>
        </form>

        {message && (
          <div className={`ha-card ha-card-${message.type === 'error' ? 'error' : 'status'}`} style={{ marginTop: '1rem' }}>
            <div className="ha-card-content">
              {message.text}
            </div>
          </div>
        )}

        {status && status.enabled && status.nextRun && (
          <div className="ha-card ha-card-status" style={{ marginTop: '1rem' }}>
            <div className="ha-card-content">
              <strong>Next scheduled run:</strong> {new Date(status.nextRun).toLocaleString()}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
