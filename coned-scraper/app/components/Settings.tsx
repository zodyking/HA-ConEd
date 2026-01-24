'use client'

import { useState, useEffect } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api'

interface Credentials {
  username: string
  password: string
  totp_secret: string
}

interface TOTPResponse {
  code: string
  time_remaining: number
}

interface ScrapeHistoryEntry {
  id: number
  timestamp: string
  success: boolean
  error_message?: string
  failure_step?: string
  duration_seconds?: number
}

export default function Settings() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [totpSecret, setTotpSecret] = useState('')
  const [currentTOTP, setCurrentTOTP] = useState<string>('')
  const [timeRemaining, setTimeRemaining] = useState<number>(30)
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [activeTab, setActiveTab] = useState<'credentials' | 'automated' | 'webhooks' | 'mqtt' | 'app-settings'>('credentials')
  
  // Password protection
  const [isUnlocked, setIsUnlocked] = useState(false)
  const [passwordInput, setPasswordInput] = useState('')
  const [passwordError, setPasswordError] = useState('')
  
  // Show/hide password states
  const [showUsername, setShowUsername] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showTotpSecret, setShowTotpSecret] = useState(false)
  
  // Helper function to mask text
  const maskText = (text: string) => {
    if (!text) return ''
    return '•'.repeat(text.length)
  }

  // Check password on mount
  useEffect(() => {
    // For now, check if settings page should be locked
    // In production, you might want to check session/local storage
    const unlocked = sessionStorage.getItem('settings_unlocked')
    if (unlocked === 'true') {
      setIsUnlocked(true)
      loadSettings()
    }
  }, [])

  // Load saved credentials on mount
  useEffect(() => {
    if (isUnlocked) {
      loadSettings()
    }
  }, [isUnlocked])

  // Update TOTP code every second
  useEffect(() => {
    if (!isUnlocked) return
    
    if (!totpSecret || totpSecret.trim() === '') {
      setCurrentTOTP('')
      setTimeRemaining(30)
      return
    }

    const updateTOTP = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/totp`)
        if (response.ok) {
          const data: TOTPResponse = await response.json()
          setCurrentTOTP(data.code)
          setTimeRemaining(data.time_remaining)
        } else {
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
            errorMessage = response.status === 404 ? 'No credentials saved' : 'Error'
          }
          setCurrentTOTP(errorMessage)
        }
      } catch (error) {
        console.error('Failed to fetch TOTP:', error)
        setCurrentTOTP('Connection Error')
      }
    }

    updateTOTP()
    const interval = setInterval(updateTOTP, 1000)
    return () => clearInterval(interval)
  }, [totpSecret, isUnlocked])

  const verifyPassword = async (pwd: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/app-settings/verify-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pwd })
      })
      
      if (response.ok) {
        const data = await response.json()
        if (data.valid) {
          setIsUnlocked(true)
          sessionStorage.setItem('settings_unlocked', 'true')
          setPasswordError('')
          return true
        } else {
          setPasswordError('Incorrect password')
          return false
        }
      } else {
        setPasswordError('Failed to verify password')
        return false
      }
    } catch (error) {
      setPasswordError('Connection error')
      return false
    }
  }

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await verifyPassword(passwordInput)
  }

  const loadSettings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/settings`)
      if (response.ok) {
        const data: Credentials = await response.json()
        setUsername(data.username || '')
        setPassword('')
        setTotpSecret(data.totp_secret || '')
        setShowUsername(false)
        setShowPassword(false)
        setShowTotpSecret(false)
      } else {
        console.error('Failed to load settings:', await response.text())
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
      setMessage({ type: 'error', text: 'Failed to connect to API. Make sure the Python service is running.' })
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage(null)

    try {
      const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password: password || null,
          totp_secret: totpSecret,
        }),
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Settings saved successfully!' })
        if (totpSecret) {
          const totpResponse = await fetch(`${API_BASE_URL}/totp`)
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

  // Password protection modal
  if (!isUnlocked) {
    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000
      }}>
        <div className="ha-card" style={{ maxWidth: '400px', margin: '1rem' }}>
          <div className="ha-card-header">
            <span className="ha-card-icon">🔒</span>
            <span>Settings Password Required</span>
          </div>
          <div className="ha-card-content">
            <form onSubmit={handlePasswordSubmit}>
              <div className="ha-form-group">
                <label htmlFor="settings-password" className="ha-form-label">
                  Enter Settings Password
                </label>
                <input
                  type="password"
                  id="settings-password"
                  className="ha-form-input"
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  placeholder="Default: 0000"
                  autoFocus
                  required
                />
                {passwordError && (
                  <div style={{ color: '#d32f2f', fontSize: '0.85rem', marginTop: '0.5rem' }}>
                    {passwordError}
                  </div>
                )}
                <div className="info-text" style={{ marginTop: '0.5rem' }}>
                  Default password is <strong>0000</strong>. Change it in App Settings after unlocking.
                </div>
              </div>
              <button type="submit" className="ha-button ha-button-primary">
                Unlock Settings
              </button>
            </form>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="ha-settings">
      <div className="ha-tabs" style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
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
        <button
          type="button"
          className={`ha-tab ${activeTab === 'webhooks' ? 'active' : ''}`}
          onClick={() => setActiveTab('webhooks')}
        >
          🔗 Webhooks
        </button>
        <button
          type="button"
          className={`ha-tab ${activeTab === 'mqtt' ? 'active' : ''}`}
          onClick={() => setActiveTab('mqtt')}
        >
          📡 MQTT
        </button>
        <button
          type="button"
          className={`ha-tab ${activeTab === 'app-settings' ? 'active' : ''}`}
          onClick={() => setActiveTab('app-settings')}
        >
          ⚙️ App Settings
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
                    onBlur={() => setShowUsername(false)}
                    required
                    autoComplete="off"
                  />
                </div>
              </div>

              <div className="ha-form-group">
                <label htmlFor="password" className="ha-form-label">
                  Password
                  <span style={{ fontSize: '0.85rem', fontWeight: 'normal', marginLeft: '0.5rem', color: '#666' }}>
                    (leave empty to keep existing)
                  </span>
                </label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    className="ha-form-input"
                    value={showPassword ? password : (password ? maskText(password) : '')}
                    onChange={(e) => setPassword(e.target.value)}
                    onFocus={() => setShowPassword(true)}
                    onBlur={() => setShowPassword(false)}
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <div className="ha-form-group">
                <label htmlFor="totp-secret" className="ha-form-label">TOTP Secret</label>
                <div className="password-input-wrapper">
                  <input
                    type={showTotpSecret ? "text" : "password"}
                    id="totp-secret"
                    className="ha-form-input"
                    value={showTotpSecret ? totpSecret : (totpSecret ? maskText(totpSecret) : '')}
                    onChange={(e) => setTotpSecret(e.target.value.trim().toUpperCase())}
                    onFocus={() => setShowTotpSecret(true)}
                    onBlur={() => setShowTotpSecret(false)}
                    required
                    autoComplete="off"
                    style={{ fontFamily: 'monospace', letterSpacing: showTotpSecret ? '0.1em' : 'normal' }}
                  />
                </div>
                <div className="info-text">
                  Your 2FA secret key (usually 16-32 characters)
                </div>
              </div>

              <button type="submit" className="ha-button ha-button-primary" disabled={isLoading}>
                {isLoading ? 'Saving...' : 'Save Credentials'}
              </button>
            </form>

            {currentTOTP && currentTOTP !== 'Connection Error' && currentTOTP !== 'No credentials saved' && (
              <div className="ha-card ha-card-status" style={{ marginTop: '1.5rem' }}>
                <div className="ha-card-content">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>Current TOTP Code</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', fontFamily: 'monospace', letterSpacing: '0.15em' }}>
                        {currentTOTP}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '0.25rem' }}>Time Remaining</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: timeRemaining < 10 ? '#d32f2f' : '#4caf50' }}>
                        {timeRemaining}s
                      </div>
                    </div>
                  </div>
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

      {activeTab === 'webhooks' && (
        <WebhooksTab />
      )}

      {activeTab === 'mqtt' && (
        <MQTTTab />
      )}

      {activeTab === 'app-settings' && (
        <AppSettingsTab />
      )}
    </div>
  )
}

function MQTTTab() {
  const [mqttUrl, setMqttUrl] = useState('')
  const [mqttUsername, setMqttUsername] = useState('')
  const [mqttPassword, setMqttPassword] = useState('')
  const [mqttBaseTopic, setMqttBaseTopic] = useState('coned')
  const [mqttQos, setMqttQos] = useState(1)
  const [mqttRetain, setMqttRetain] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    loadMqttConfig()
  }, [])

  const loadMqttConfig = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/mqtt-config`)
      if (response.ok) {
        const data = await response.json()
        setMqttUrl(data.mqtt_url || '')
        setMqttUsername(data.mqtt_username || '')
        setMqttPassword('')
        setMqttBaseTopic(data.mqtt_base_topic || 'coned')
        setMqttQos(data.mqtt_qos || 1)
        setMqttRetain(data.mqtt_retain !== undefined ? data.mqtt_retain : true)
      }
    } catch (error) {
      console.error('Failed to load MQTT config:', error)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage(null)

    try {
      const response = await fetch(`${API_BASE_URL}/mqtt-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mqtt_url: mqttUrl.trim(),
          mqtt_username: mqttUsername.trim(),
          mqtt_password: mqttPassword || undefined,
          mqtt_base_topic: mqttBaseTopic.trim() || 'coned',
          mqtt_qos: mqttQos,
          mqtt_retain: mqttRetain
        }),
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'MQTT configuration saved successfully!' })
        await loadMqttConfig()
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to save MQTT config' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to connect to API.' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="ha-card">
      <div className="ha-card-header">
        <span className="ha-card-icon">📡</span>
        <span>MQTT Configuration</span>
      </div>
      <div className="ha-card-content">
        <div className="info-text" style={{ marginBottom: '1.5rem' }}>
          Configure MQTT to publish sensor data to Home Assistant. Topics: <code>coned/account_balance</code>, <code>coned/latest_bill</code>, <code>coned/previous_bill</code>, <code>coned/last_payment</code>
        </div>

        <form onSubmit={handleSave}>
          <div className="ha-form-group">
            <label htmlFor="mqtt-url" className="ha-form-label">MQTT Broker URL</label>
            <input
              type="text"
              id="mqtt-url"
              className="ha-form-input"
              value={mqttUrl}
              onChange={(e) => setMqttUrl(e.target.value)}
              placeholder="mqtt://homeassistant.local:1883 or mqtts://..."
              style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
            />
            <div className="info-text">
              Leave empty to disable MQTT publishing
            </div>
          </div>

          <div className="ha-form-group">
            <label htmlFor="mqtt-username" className="ha-form-label">MQTT Username</label>
            <input
              type="text"
              id="mqtt-username"
              className="ha-form-input"
              value={mqttUsername}
              onChange={(e) => setMqttUsername(e.target.value)}
              placeholder="Optional"
            />
          </div>

          <div className="ha-form-group">
            <label htmlFor="mqtt-password" className="ha-form-label">
              MQTT Password
              <span style={{ fontSize: '0.85rem', fontWeight: 'normal', marginLeft: '0.5rem', color: '#666' }}>
                (leave empty to keep existing)
              </span>
            </label>
            <input
              type="password"
              id="mqtt-password"
              className="ha-form-input"
              value={mqttPassword}
              onChange={(e) => setMqttPassword(e.target.value)}
              placeholder="Optional"
              autoComplete="new-password"
            />
          </div>

          <div className="ha-form-group">
            <label htmlFor="mqtt-base-topic" className="ha-form-label">Base Topic</label>
            <input
              type="text"
              id="mqtt-base-topic"
              className="ha-form-input"
              value={mqttBaseTopic}
              onChange={(e) => setMqttBaseTopic(e.target.value)}
              placeholder="coned"
              style={{ fontFamily: 'monospace' }}
            />
            <div className="info-text">
              Topics will be: {mqttBaseTopic || 'coned'}/account_balance, etc.
            </div>
          </div>

          <div className="ha-form-group">
            <label htmlFor="mqtt-qos" className="ha-form-label">Quality of Service (QoS)</label>
            <select
              id="mqtt-qos"
              className="ha-form-input"
              value={mqttQos}
              onChange={(e) => setMqttQos(parseInt(e.target.value))}
            >
              <option value="0">0 - At most once</option>
              <option value="1">1 - At least once</option>
              <option value="2">2 - Exactly once</option>
            </select>
          </div>

          <div className="ha-form-group">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={mqttRetain}
                onChange={(e) => setMqttRetain(e.target.checked)}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
              <span>Retain Messages</span>
            </label>
            <div className="info-text">
              Retained messages persist on the broker and are delivered to new subscribers
            </div>
          </div>

          <button type="submit" className="ha-button ha-button-primary" disabled={isLoading}>
            {isLoading ? 'Saving...' : 'Save MQTT Config'}
          </button>
        </form>

        {message && (
          <div className={`ha-card ha-card-${message.type === 'error' ? 'error' : 'status'}`} style={{ marginTop: '1rem' }}>
            <div className="ha-card-content">
              {message.text}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function AppSettingsTab() {
  const [timezone, setTimezone] = useState('America/New_York')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    loadAppSettings()
  }, [])

  const loadAppSettings = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/app-settings`)
      if (response.ok) {
        const data = await response.json()
        setTimezone(data.timezone || 'America/New_York')
      }
    } catch (error) {
      console.error('Failed to load app settings:', error)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage(null)

    if (newPassword && newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match' })
      setIsLoading(false)
      return
    }

    if (newPassword && newPassword.length < 4) {
      setMessage({ type: 'error', text: 'Password must be at least 4 characters' })
      setIsLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_BASE_URL}/app-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timezone: timezone.trim(),
          settings_password: newPassword || '0000'
        }),
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'App settings saved successfully!' })
        setNewPassword('')
        setConfirmPassword('')
        if (newPassword) {
          sessionStorage.removeItem('settings_unlocked')
          setTimeout(() => {
            window.location.reload()
          }, 2000)
        }
      } else {
        const error = await response.json()
        setMessage({ type: 'error', text: error.detail || 'Failed to save settings' })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to connect to API.' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="ha-card">
      <div className="ha-card-header">
        <span className="ha-card-icon">⚙️</span>
        <span>App Settings</span>
      </div>
      <div className="ha-card-content">
        <form onSubmit={handleSave}>
          <div className="ha-form-group">
            <label htmlFor="timezone" className="ha-form-label">Timezone</label>
            <select
              id="timezone"
              className="ha-form-input"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
            >
              <option value="America/New_York">Eastern Time (ET)</option>
              <option value="America/Chicago">Central Time (CT)</option>
              <option value="America/Denver">Mountain Time (MT)</option>
              <option value="America/Los_Angeles">Pacific Time (PT)</option>
              <option value="America/Phoenix">Arizona Time (No DST)</option>
              <option value="America/Anchorage">Alaska Time (AKT)</option>
              <option value="Pacific/Honolulu">Hawaii Time (HST)</option>
              <option value="UTC">UTC</option>
            </select>
            <div className="info-text">
              Used for displaying timestamps throughout the app
            </div>
          </div>

          <div className="ha-form-group">
            <label htmlFor="new-password" className="ha-form-label">
              Change Settings Password
            </label>
            <input
              type="password"
              id="new-password"
              className="ha-form-input"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Leave empty to keep current password"
              autoComplete="new-password"
            />
            <div className="info-text">
              Minimum 4 characters. You'll need to re-login after changing.
            </div>
          </div>

          {newPassword && (
            <div className="ha-form-group">
              <label htmlFor="confirm-password" className="ha-form-label">
                Confirm New Password
              </label>
              <input
                type="password"
                id="confirm-password"
                className="ha-form-input"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                autoComplete="new-password"
              />
            </div>
          )}

          <button type="submit" className="ha-button ha-button-primary" disabled={isLoading}>
            {isLoading ? 'Saving...' : 'Save App Settings'}
          </button>
        </form>

        {message && (
          <div className={`ha-card ha-card-${message.type === 'error' ? 'error' : 'status'}`} style={{ marginTop: '1rem' }}>
            <div className="ha-card-content">
              {message.text}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function WebhooksTab() {
  const [latestBillUrl, setLatestBillUrl] = useState('')
  const [previousBillUrl, setPreviousBillUrl] = useState('')
  const [accountBalanceUrl, setAccountBalanceUrl] = useState('')
  const [lastPaymentUrl, setLastPaymentUrl] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    loadWebhooks()
  }, [])

  const loadWebhooks = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/webhooks`)
      if (response.ok) {
        const data = await response.json()
        setLatestBillUrl(data.latest_bill || '')
        setPreviousBillUrl(data.previous_bill || '')
        setAccountBalanceUrl(data.account_balance || '')
        setLastPaymentUrl(data.last_payment || '')
      }
    } catch (error) {
      console.error('Failed to load webhooks:', error)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage(null)

    try {
      const payload = {
        latest_bill: latestBillUrl.trim(),
        previous_bill: previousBillUrl.trim(),
        account_balance: accountBalanceUrl.trim(),
        last_payment: lastPaymentUrl.trim()
      }

      const response = await fetch(`${API_BASE_URL}/webhooks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (response.ok) {
        const data = await response.json()
        setMessage({ type: 'success', text: `Webhook URLs saved successfully! (${data.configured_count} configured)` })
        await loadWebhooks()
      } else {
        let errorMessage = 'Failed to save webhook URLs'
        try {
          const errorData = await response.json()
          if (errorData.detail) {
            if (typeof errorData.detail === 'string') {
              errorMessage = errorData.detail
            } else if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail.map((err: any) => 
                `${err.loc.join('.')}: ${err.msg}`
              ).join(', ')
            }
          }
        } catch {
          errorMessage = `HTTP ${response.status}: ${response.statusText}`
        }
        setMessage({ type: 'error', text: errorMessage })
      }
    } catch (error) {
      setMessage({ type: 'error', text: `Failed to connect to API: ${error instanceof Error ? error.message : 'Unknown error'}` })
    } finally {
      setIsLoading(false)
    }
  }

  const handleTest = async () => {
    setIsLoading(true)
    setMessage(null)

    try {
      const response = await fetch(`${API_BASE_URL}/webhooks/test`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        setMessage({ 
          type: 'success', 
          text: `Test webhooks sent! (${data.webhooks_sent?.join(', ') || 'none'})` 
        })
      } else {
        const errorData = await response.json().catch(() => ({}))
        setMessage({ 
          type: 'error', 
          text: errorData.detail || 'Failed to send test webhooks' 
        })
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to connect to API' })
    } finally {
      setIsLoading(false)
    }
  }

  const hasAnyWebhook = latestBillUrl.trim() || previousBillUrl.trim() || accountBalanceUrl.trim() || lastPaymentUrl.trim()

  return (
    <div className="ha-card">
      <div className="ha-card-header">
        <span className="ha-card-icon">🔗</span>
        <span>Home Assistant Webhooks</span>
      </div>
      <div className="ha-card-content">
        <div className="info-text" style={{ marginBottom: '1.5rem' }}>
          Configure separate webhook URLs for each event type. Each scrape will POST JSON data to the configured URLs.
        </div>

        <form onSubmit={handleSave}>
          <div className="ha-form-group">
            <label htmlFor="latest-bill-url" className="ha-form-label">
              📄 Latest Bill Webhook
            </label>
            <input
              type="url"
              id="latest-bill-url"
              className="ha-form-input"
              value={latestBillUrl}
              onChange={(e) => setLatestBillUrl(e.target.value)}
              placeholder="https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID"
              style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
            />
            <div className="info-text">
              Sends latest bill amount, billing cycle date, and month range
            </div>
          </div>

          <div className="ha-form-group">
            <label htmlFor="previous-bill-url" className="ha-form-label">
              📋 Previous Bill Webhook
            </label>
            <input
              type="url"
              id="previous-bill-url"
              className="ha-form-input"
              value={previousBillUrl}
              onChange={(e) => setPreviousBillUrl(e.target.value)}
              placeholder="https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID"
              style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
            />
            <div className="info-text">
              Sends previous bill amount, billing cycle date, and month range
            </div>
          </div>

          <div className="ha-form-group">
            <label htmlFor="account-balance-url" className="ha-form-label">
              💰 Account Balance Webhook
            </label>
            <input
              type="url"
              id="account-balance-url"
              className="ha-form-input"
              value={accountBalanceUrl}
              onChange={(e) => setAccountBalanceUrl(e.target.value)}
              placeholder="https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID"
              style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
            />
            <div className="info-text">
              Sends current account balance
            </div>
          </div>

          <div className="ha-form-group">
            <label htmlFor="last-payment-url" className="ha-form-label">
              💳 Last Payment Webhook
            </label>
            <input
              type="url"
              id="last-payment-url"
              className="ha-form-input"
              value={lastPaymentUrl}
              onChange={(e) => setLastPaymentUrl(e.target.value)}
              placeholder="https://homeassistant.local/api/webhook/YOUR_WEBHOOK_ID"
              style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
            />
            <div className="info-text">
              Sends last payment amount and date
            </div>
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button type="submit" className="ha-button ha-button-primary" disabled={isLoading}>
              {isLoading ? 'Saving...' : 'Save Webhook URLs'}
            </button>
            {hasAnyWebhook && (
              <button 
                type="button" 
                className="ha-button" 
                onClick={handleTest}
                disabled={isLoading}
                style={{ backgroundColor: '#4caf50', color: 'white' }}
              >
                Test Webhooks
              </button>
            )}
          </div>
        </form>

        {message && (
          <div className={`ha-card ha-card-${message.type === 'error' ? 'error' : 'status'}`} style={{ marginTop: '1rem' }}>
            <div className="ha-card-content">
              {message.text}
            </div>
          </div>
        )}
      </div>
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
  const [scrapeHistory, setScrapeHistory] = useState<ScrapeHistoryEntry[]>([])

  useEffect(() => {
    loadSchedule()
    loadScrapeHistory()
    const interval = setInterval(loadScrapeHistory, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const loadSchedule = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/automated-schedule`)
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

  const loadScrapeHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/scrape-history?limit=20`)
      if (response.ok) {
        const data = await response.json()
        setScrapeHistory(data.history || [])
      }
    } catch (error) {
      console.error('Failed to load scrape history:', error)
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

      const response = await fetch(`${API_BASE_URL}/automated-schedule`, {
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

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A'
    return `${seconds.toFixed(1)}s`
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString()
    } catch {
      return timestamp
    }
  }

  return (
    <>
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

      {/* Scrape History */}
      <div className="ha-card" style={{ marginTop: '1.5rem' }}>
        <div className="ha-card-header">
          <span className="ha-card-icon">📊</span>
          <span>Scrape History</span>
        </div>
        <div className="ha-card-content">
          {scrapeHistory.length === 0 ? (
            <div className="info-text">No scrape history available yet.</div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Time</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Status</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Duration</th>
                    <th style={{ padding: '0.75rem 0.5rem' }}>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {scrapeHistory.map((entry) => (
                    <tr key={entry.id} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '0.75rem 0.5rem' }}>
                        {formatTimestamp(entry.timestamp)}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '0.25rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.8rem',
                          fontWeight: 500,
                          backgroundColor: entry.success ? '#4caf50' : '#d32f2f',
                          color: 'white'
                        }}>
                          {entry.success ? '✓ Success' : '✗ Failed'}
                        </span>
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem' }}>
                        {formatDuration(entry.duration_seconds)}
                      </td>
                      <td style={{ padding: '0.75rem 0.5rem', fontSize: '0.85rem', color: '#666' }}>
                        {entry.error_message && (
                          <div style={{ color: '#d32f2f' }}>
                            {entry.failure_step && `[${entry.failure_step}] `}
                            {entry.error_message}
                          </div>
                        )}
                        {!entry.error_message && entry.success && (
                          <span style={{ color: '#4caf50' }}>Completed successfully</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
