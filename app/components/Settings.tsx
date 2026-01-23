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
    if (!totpSecret) {
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
          const errorData = await response.json().catch(() => ({}))
          console.error('Failed to fetch TOTP:', errorData)
          setCurrentTOTP('Error')
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
        if (data.totp_secret) {
          try {
            const totpResponse = await fetch(`${API_BASE_URL}/api/totp`)
            if (totpResponse.ok) {
              const totpData: TOTPResponse = await totpResponse.json()
              setCurrentTOTP(totpData.code)
              setTimeRemaining(totpData.time_remaining)
            }
          } catch (error) {
            console.error('Failed to fetch initial TOTP:', error)
          }
        }
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
    <div>
      <h2>Settings</h2>
      <form onSubmit={handleSave}>
        <div className="form-group">
          <label htmlFor="username">Username / Email</label>
          <div className="password-input-wrapper">
            <input
              type={showUsername ? "text" : "password"}
              id="username"
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

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <div className="password-input-wrapper">
            <input
              type={showPassword ? "text" : "password"}
              id="password"
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

        <div className="form-group">
          <label htmlFor="totp_secret">TOTP Secret</label>
          <div className="password-input-wrapper">
            <input
              type={showTotpSecret ? "text" : "password"}
              id="totp_secret"
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

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Settings'}
        </button>
      </form>

      {totpSecret && (
        <div className="totp-display">
          <h3>Current TOTP Code</h3>
          <div className="totp-code">{currentTOTP || 'Loading...'}</div>
          <div className="totp-time">
            Expires in {timeRemaining} seconds
          </div>
        </div>
      )}

      {message && (
        <div className={`status-message status-${message.type}`}>
          {message.text}
        </div>
      )}

    </div>
  )
}
