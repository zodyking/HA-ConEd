'use client'

import { useState, useEffect } from 'react'
import { formatTimestamp as formatTZ } from '../lib/timezone'
import Dashboard from './Dashboard'

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
  const [activeTab, setActiveTab] = useState<'console' | 'credentials' | 'automated' | 'webhooks' | 'mqtt' | 'app-settings' | 'payees'>('console')
  
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

  // Password lock always shows on mount (removed session persistence)
  useEffect(() => {
    // No automatic unlock - user must enter password every time
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
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  className="ha-button"
                  onClick={() => {
                    if (typeof window !== 'undefined') {
                      const event = new CustomEvent('navigateToLedger')
                      window.dispatchEvent(event)
                    }
                  }}
                  style={{
                    flex: 1,
                    backgroundColor: '#757575',
                    color: 'white'
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="ha-button ha-button-primary" style={{ flex: 1 }}>
                  Unlock Settings
                </button>
              </div>
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
          className={`ha-tab ${activeTab === 'console' ? 'active' : ''}`}
          onClick={() => setActiveTab('console')}
        >
          📊 Console
        </button>
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
        <button
          type="button"
          className={`ha-tab ${activeTab === 'payees' ? 'active' : ''}`}
          onClick={() => setActiveTab('payees')}
        >
          👥 Payees
        </button>
      </div>

      {activeTab === 'console' && (
        <Dashboard />
      )}

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

      {activeTab === 'payees' && (
        <PayeesTab />
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
  const [currentTime, setCurrentTime] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  
  // PDF management
  const [pdfUrl, setPdfUrl] = useState('')
  const [pdfStatus, setPdfStatus] = useState<{ exists: boolean, size_kb: number } | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfMessage, setPdfMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  
  // App Base URL for MQTT
  const [appBaseUrl, setAppBaseUrl] = useState('')

  useEffect(() => {
    // Load app base URL
    fetch(`${API_BASE_URL}/app-settings`)
      .then(res => res.json())
      .then(data => {
        setAppBaseUrl(data.app_base_url || '')
      })
      .catch(() => {})
    
    // Check PDF status
    checkPdfStatus()
  }, [])
  
  const checkPdfStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/latest-bill-pdf/status`)
      if (res.ok) {
        const data = await res.json()
        setPdfStatus(data)
      }
    } catch (e) {
      console.error('Failed to check PDF status:', e)
    }
  }
  
  const handleDownloadPdf = async () => {
    if (!pdfUrl.trim()) {
      setPdfMessage({ type: 'error', text: 'Please enter a PDF URL' })
      return
    }
    
    setPdfLoading(true)
    setPdfMessage(null)
    
    try {
      const res = await fetch(`${API_BASE_URL}/latest-bill-pdf/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: pdfUrl.trim() })
      })
      
      const data = await res.json()
      
      if (res.ok) {
        setPdfMessage({ type: 'success', text: data.message })
        setPdfUrl('')
        await checkPdfStatus()
      } else {
        setPdfMessage({ type: 'error', text: data.detail || 'Failed to download PDF' })
      }
    } catch (e) {
      setPdfMessage({ type: 'error', text: 'Failed to connect to API' })
    } finally {
      setPdfLoading(false)
    }
  }
  
  const handleDeletePdf = async () => {
    setPdfLoading(true)
    setPdfMessage(null)
    
    try {
      const res = await fetch(`${API_BASE_URL}/latest-bill-pdf`, { method: 'DELETE' })
      if (res.ok) {
        setPdfMessage({ type: 'success', text: 'PDF deleted' })
        await checkPdfStatus()
      }
    } catch (e) {
      setPdfMessage({ type: 'error', text: 'Failed to delete PDF' })
    } finally {
      setPdfLoading(false)
    }
  }
  
  const handleSendMqtt = async () => {
    setPdfLoading(true)
    setPdfMessage(null)
    
    try {
      const res = await fetch(`${API_BASE_URL}/latest-bill-pdf/send-mqtt`, { method: 'POST' })
      const data = await res.json()
      if (res.ok) {
        setPdfMessage({ type: 'success', text: data.message || 'PDF URL sent to MQTT' })
      } else {
        setPdfMessage({ type: 'error', text: data.detail || 'Failed to send MQTT' })
      }
    } catch (e) {
      setPdfMessage({ type: 'error', text: 'Failed to send PDF URL via MQTT' })
    } finally {
      setPdfLoading(false)
    }
  }
  
  const handleSaveBaseUrl = async () => {
    setIsLoading(true)
    setMessage(null)
    
    try {
      const currentSettings = await fetch(`${API_BASE_URL}/app-settings`)
      const currentData = await currentSettings.json()
      
      const res = await fetch(`${API_BASE_URL}/app-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          time_offset_hours: currentData.time_offset_hours || 0,
          settings_password: currentData.settings_password || '0000',
          app_base_url: appBaseUrl.trim()
        })
      })
      
      if (res.ok) {
        setMessage({ type: 'success', text: 'App Base URL saved!' })
      } else {
        setMessage({ type: 'error', text: 'Failed to save' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to connect' })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    // Update current time display every second using browser's local time
    const interval = setInterval(() => {
      const now = new Date()
      setCurrentTime(now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }))
    }, 1000)
    return () => clearInterval(interval)
  }, [])

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
      // First, get current settings to preserve time_offset_hours
      const currentSettings = await fetch(`${API_BASE_URL}/app-settings`)
      const currentData = await currentSettings.json()
      
      const response = await fetch(`${API_BASE_URL}/app-settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          time_offset_hours: currentData.time_offset_hours || 0,
          settings_password: newPassword || currentData.settings_password || '0000'
        }),
      })

      if (response.ok) {
        setMessage({ type: 'success', text: 'Password changed successfully!' })
        setNewPassword('')
        setConfirmPassword('')
        if (newPassword) {
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
        <div style={{ marginBottom: '2rem' }}>
          <div className="ha-form-group">
            <label className="ha-form-label">Your Local Time</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <div style={{ 
                padding: '0.75rem 1.25rem',
                background: '#1a1a2e',
                borderRadius: '8px',
                fontFamily: 'monospace',
                fontSize: '1.5rem',
                fontWeight: 'bold',
                color: '#4ade80',
                minWidth: '150px',
                textAlign: 'center',
                border: '1px solid #333'
              }}>
                {currentTime || '--:--:--'}
              </div>
              <span style={{ fontSize: '0.8rem', color: '#666' }}>
                {Intl.DateTimeFormat().resolvedOptions().timeZone}
              </span>
            </div>
            <div className="info-text" style={{ marginTop: '0.5rem' }}>
              All timestamps in the app use your browser&apos;s local timezone
            </div>
          </div>
        </div>

        {/* Bill PDF Section */}
        <div style={{ marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid #e0e0e0' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: '#333' }}>
            📄 Bill PDF
          </div>
          
          {/* PDF Status */}
          <div style={{ 
            padding: '1rem', 
            backgroundColor: pdfStatus?.exists ? '#e8f5e9' : '#fff3e0',
            borderRadius: '8px',
            marginBottom: '1rem',
            border: `1px solid ${pdfStatus?.exists ? '#4caf50' : '#ff9800'}`
          }}>
            {pdfStatus?.exists ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                <span style={{ color: '#2e7d32', fontWeight: 500 }}>
                  ✅ PDF available ({pdfStatus.size_kb} KB)
                </span>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <a
                    href={`${API_BASE_URL}/bill-document`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      padding: '0.4rem 0.75rem',
                      backgroundColor: '#03a9f4',
                      color: 'white',
                      textDecoration: 'none',
                      borderRadius: '4px',
                      fontSize: '0.8rem'
                    }}
                  >
                    View
                  </a>
                  <button
                    type="button"
                    onClick={handleSendMqtt}
                    disabled={pdfLoading}
                    style={{
                      padding: '0.4rem 0.75rem',
                      backgroundColor: '#9c27b0',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '0.8rem',
                      cursor: 'pointer'
                    }}
                  >
                    Send MQTT
                  </button>
                  <button
                    type="button"
                    onClick={handleDeletePdf}
                    disabled={pdfLoading}
                    style={{
                      padding: '0.4rem 0.75rem',
                      backgroundColor: '#f44336',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      fontSize: '0.8rem',
                      cursor: 'pointer'
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ) : (
              <span style={{ color: '#e65100' }}>
                ⚠️ No PDF available - add a link below
              </span>
            )}
          </div>
          
          {/* PDF URL Input */}
          <div className="ha-form-group">
            <label className="ha-form-label">PDF Link</label>
            <textarea
              className="ha-form-input"
              value={pdfUrl}
              onChange={(e) => setPdfUrl(e.target.value)}
              placeholder="Paste the ConEd bill PDF link here (from View Current Bill button)"
              rows={3}
              style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}
            />
            <div className="info-text">
              Get this link by clicking &quot;View Current Bill&quot; on ConEd website, then copy the URL from the new tab
            </div>
          </div>
          
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={pdfLoading || !pdfUrl.trim()}
            className="ha-button ha-button-primary"
            style={{ width: '100%', padding: '0.75rem', backgroundColor: '#4caf50' }}
          >
            {pdfLoading ? 'Downloading...' : '⬇️ Download & Save PDF'}
          </button>
          
          {pdfMessage && (
            <div style={{
              marginTop: '0.75rem',
              padding: '0.75rem',
              borderRadius: '4px',
              backgroundColor: pdfMessage.type === 'error' ? '#ffebee' : '#e8f5e9',
              color: pdfMessage.type === 'error' ? '#c62828' : '#2e7d32',
              fontSize: '0.85rem'
            }}>
              {pdfMessage.text}
            </div>
          )}
        </div>

        {/* App Base URL Section */}
        <div style={{ marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid #e0e0e0' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: '#333' }}>
            🌐 App Base URL (for MQTT)
          </div>
          
          <div className="ha-form-group">
            <label className="ha-form-label">Base URL</label>
            <input
              type="text"
              className="ha-form-input"
              value={appBaseUrl}
              onChange={(e) => setAppBaseUrl(e.target.value)}
              placeholder="https://coned.your-domain.com"
            />
            <div className="info-text">
              Used to publish full PDF URL to MQTT for Home Assistant
            </div>
          </div>
          
          <button
            type="button"
            onClick={handleSaveBaseUrl}
            disabled={isLoading}
            className="ha-button ha-button-primary"
            style={{ width: '100%', padding: '0.75rem' }}
          >
            {isLoading ? 'Saving...' : 'Save Base URL'}
          </button>
        </div>

        <form onSubmit={handleSave} style={{ marginTop: '2rem', paddingTop: '2rem', borderTop: '1px solid #e0e0e0' }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '1rem', color: '#333' }}>
            Change Settings Password
          </div>

          <div className="ha-form-group">
            <label htmlFor="new-password" className="ha-form-label">
              New Password
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
            {isLoading ? 'Saving...' : 'Change Password'}
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
  const [formattedTimestamps, setFormattedTimestamps] = useState<Map<number, string>>(new Map())

  useEffect(() => {
    loadSchedule()
    loadScrapeHistory()
    const interval = setInterval(loadScrapeHistory, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  // Format timestamps when history changes
  useEffect(() => {
    const newMap = new Map<number, string>()
    for (const entry of scrapeHistory) {
      try {
        const formatted = formatTZ(entry.timestamp)
        newMap.set(entry.id, formatted)
      } catch {
        newMap.set(entry.id, entry.timestamp)
      }
    }
    setFormattedTimestamps(newMap)
  }, [scrapeHistory])

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
                <strong>Next scheduled run:</strong> <NextRunTime timestamp={status.nextRun} />
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
                        {formattedTimestamps.get(entry.id) || entry.timestamp}
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

function NextRunTime({ timestamp }: { timestamp: string }) {
  return <span>{formatTZ(timestamp)}</span>
}

// ==========================================
// PAYEES TAB - User & Card Management
// ==========================================

interface PayeeUser {
  id: number
  name: string
  is_default: boolean
  cards: string[]
  created_at: string
}

interface UnverifiedPayment {
  id: number
  payment_date: string
  amount: string
  description: string
  bill_month?: string
}

function PayeesTab() {
  const [users, setUsers] = useState<PayeeUser[]>([])
  const [unverifiedPayments, setUnverifiedPayments] = useState<UnverifiedPayment[]>([])
  const [newUserName, setNewUserName] = useState('')
  const [newCardInput, setNewCardInput] = useState<{ [key: number]: string }>({})
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    loadUsers()
    loadUnverifiedPayments()
  }, [])

  const loadUsers = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/payee-users`)
      if (res.ok) {
        const data = await res.json()
        setUsers(data.users || [])
      }
    } catch (e) {
      console.error('Failed to load users:', e)
    }
  }

  const loadUnverifiedPayments = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/payments/unverified`)
      if (res.ok) {
        const data = await res.json()
        setUnverifiedPayments(data.payments || [])
      }
    } catch (e) {
      console.error('Failed to load unverified payments:', e)
    }
  }

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newUserName.trim()) return
    
    setIsLoading(true)
    setMessage(null)
    
    try {
      const res = await fetch(`${API_BASE_URL}/payee-users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newUserName.trim(), is_default: users.length === 0 })
      })
      
      if (res.ok) {
        setNewUserName('')
        await loadUsers()
        setMessage({ type: 'success', text: `Added user: ${newUserName}` })
      } else {
        const err = await res.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to add user' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to connect' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteUser = async (userId: number, userName: string) => {
    if (!confirm(`Delete user "${userName}"? This will unlink all their payments.`)) return
    
    try {
      const res = await fetch(`${API_BASE_URL}/payee-users/${userId}`, { method: 'DELETE' })
      if (res.ok) {
        await loadUsers()
        setMessage({ type: 'success', text: `Deleted user: ${userName}` })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to delete user' })
    }
  }

  const handleSetDefault = async (userId: number) => {
    try {
      await fetch(`${API_BASE_URL}/payee-users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_default: true })
      })
      await loadUsers()
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to set default' })
    }
  }

  const handleAddCard = async (userId: number) => {
    const cardNum = newCardInput[userId]?.trim()
    if (!cardNum || cardNum.length < 4) {
      setMessage({ type: 'error', text: 'Enter last 4 digits of card' })
      return
    }
    
    try {
      const res = await fetch(`${API_BASE_URL}/user-cards`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, card_last_four: cardNum.slice(-4) })
      })
      
      if (res.ok) {
        setNewCardInput({ ...newCardInput, [userId]: '' })
        await loadUsers()
        setMessage({ type: 'success', text: `Added card *${cardNum.slice(-4)}` })
      } else {
        const err = await res.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to add card' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to add card' })
    }
  }

  const handleAttributePayment = async (paymentId: number, userId: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/payments/attribute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_id: paymentId, user_id: userId, method: 'manual' })
      })
      
      if (res.ok) {
        await loadUnverifiedPayments()
        setMessage({ type: 'success', text: 'Payment attributed' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to attribute payment' })
    }
  }

  return (
    <div className="ha-settings-content">
      <div className="ha-card">
        <div className="ha-card-header">
          <span className="ha-card-icon">👥</span>
          <span>Payee Users & Cards</span>
        </div>
        <div className="ha-card-content">
          <div className="info-text" style={{ marginBottom: '1rem' }}>
            Add users who make payments. Link their card endings (last 4 digits) to automatically identify who made each payment from email confirmations.
          </div>

          {/* Add New User */}
          <form onSubmit={handleAddUser} style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                className="ha-form-input"
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                placeholder="Enter user name"
                style={{ flex: 1 }}
              />
              <button
                type="submit"
                disabled={isLoading || !newUserName.trim()}
                className="ha-button ha-button-primary"
              >
                Add User
              </button>
            </div>
          </form>

          {/* User List */}
          {users.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
              No users added yet. Add a user to start tracking payments.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {users.map((user) => (
                <div 
                  key={user.id} 
                  style={{ 
                    padding: '1rem', 
                    backgroundColor: user.is_default ? '#e3f2fd' : '#f5f5f5', 
                    borderRadius: '8px',
                    border: user.is_default ? '2px solid #03a9f4' : '1px solid #e0e0e0'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontWeight: 600, fontSize: '1rem' }}>{user.name}</span>
                      {user.is_default && (
                        <span style={{ 
                          fontSize: '0.65rem', 
                          backgroundColor: '#03a9f4', 
                          color: 'white',
                          padding: '0.15rem 0.4rem',
                          borderRadius: '3px'
                        }}>
                          DEFAULT
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {!user.is_default && (
                        <button
                          onClick={() => handleSetDefault(user.id)}
                          style={{
                            padding: '0.3rem 0.6rem',
                            fontSize: '0.7rem',
                            backgroundColor: '#4caf50',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer'
                          }}
                        >
                          Set Default
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteUser(user.id, user.name)}
                        style={{
                          padding: '0.3rem 0.6rem',
                          fontSize: '0.7rem',
                          backgroundColor: '#f44336',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  {/* Cards */}
                  <div style={{ marginBottom: '0.5rem' }}>
                    <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.3rem' }}>Cards:</div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                      {user.cards.length > 0 ? (
                        user.cards.map((card, idx) => (
                          <span 
                            key={idx}
                            style={{
                              padding: '0.2rem 0.5rem',
                              backgroundColor: '#e0e0e0',
                              borderRadius: '4px',
                              fontSize: '0.8rem',
                              fontFamily: 'monospace'
                            }}
                          >
                            *{card}
                          </span>
                        ))
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: '#999' }}>No cards linked</span>
                      )}
                    </div>
                  </div>

                  {/* Add Card */}
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                    <input
                      type="text"
                      className="ha-form-input"
                      value={newCardInput[user.id] || ''}
                      onChange={(e) => setNewCardInput({ ...newCardInput, [user.id]: e.target.value })}
                      placeholder="Last 4 digits"
                      maxLength={4}
                      style={{ width: '100px', fontSize: '0.85rem' }}
                    />
                    <button
                      onClick={() => handleAddCard(user.id)}
                      style={{
                        padding: '0.3rem 0.6rem',
                        fontSize: '0.75rem',
                        backgroundColor: '#03a9f4',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      + Add Card
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {message && (
            <div style={{
              marginTop: '1rem',
              padding: '0.75rem',
              borderRadius: '4px',
              backgroundColor: message.type === 'error' ? '#ffebee' : '#e8f5e9',
              color: message.type === 'error' ? '#c62828' : '#2e7d32',
              fontSize: '0.85rem'
            }}>
              {message.text}
            </div>
          )}
        </div>
      </div>

      {/* Unverified Payments */}
      {unverifiedPayments.length > 0 && users.length > 0 && (
        <div className="ha-card" style={{ marginTop: '1rem' }}>
          <div className="ha-card-header">
            <span className="ha-card-icon">❓</span>
            <span>Unverified Payments ({unverifiedPayments.length})</span>
          </div>
          <div className="ha-card-content">
            <div className="info-text" style={{ marginBottom: '1rem' }}>
              These payments couldn&apos;t be automatically attributed. Assign them to a user manually.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {unverifiedPayments.slice(0, 10).map((payment) => (
                <div 
                  key={payment.id}
                  style={{
                    padding: '0.75rem',
                    backgroundColor: '#fff3e0',
                    borderRadius: '6px',
                    border: '1px solid #ffcc80',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '0.5rem'
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{payment.amount}</div>
                    <div style={{ fontSize: '0.75rem', color: '#666' }}>
                      {payment.payment_date} • {payment.description}
                    </div>
                  </div>
                  <select
                    onChange={(e) => {
                      if (e.target.value) {
                        handleAttributePayment(payment.id, parseInt(e.target.value))
                      }
                    }}
                    defaultValue=""
                    style={{
                      padding: '0.4rem',
                      borderRadius: '4px',
                      border: '1px solid #ccc',
                      fontSize: '0.8rem'
                    }}
                  >
                    <option value="">Assign to...</option>
                    {users.map((user) => (
                      <option key={user.id} value={user.id}>{user.name}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* IMAP Email Configuration */}
      <div className="ha-card" style={{ marginTop: '1rem' }}>
        <div className="ha-card-header">
          <span className="ha-card-icon">📧</span>
          <span>Email Integration (IMAP)</span>
        </div>
        <div className="ha-card-content">
          <IMAPSettingsSection />
        </div>
      </div>
    </div>
  )
}

// ==========================================
// IMAP SETTINGS SECTION
// ==========================================

function IMAPSettingsSection() {
  const [config, setConfig] = useState({
    enabled: false,
    server: '',
    port: 993,
    email: '',
    password: '',
    use_ssl: true,
    days_back: 30
  })
  const [isLoading, setIsLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)
  const [lastSync, setLastSync] = useState<string | null>(null)
  const [previewEmails, setPreviewEmails] = useState<any[]>([])
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/imap-config`)
      if (res.ok) {
        const data = await res.json()
        setConfig({
          enabled: data.enabled || false,
          server: data.server || '',
          port: data.port || 993,
          email: data.email || '',
          password: data.password || '',
          use_ssl: data.use_ssl !== false,
          days_back: data.days_back || 30
        })
        setLastSync(data.last_sync || null)
      }
    } catch (e) {
      console.error('Failed to load IMAP config:', e)
    }
  }

  const handleSave = async () => {
    setIsLoading(true)
    setMessage(null)
    
    try {
      const res = await fetch(`${API_BASE_URL}/imap-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      
      if (res.ok) {
        setMessage({ type: 'success', text: 'IMAP configuration saved!' })
      } else {
        const err = await res.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to save' })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to connect' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleTest = async () => {
    setIsLoading(true)
    setMessage(null)
    
    try {
      const res = await fetch(`${API_BASE_URL}/imap-config/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      })
      
      const data = await res.json()
      if (data.success) {
        setMessage({ type: 'success', text: data.message })
      } else {
        setMessage({ type: 'error', text: data.message })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Connection test failed' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSync = async () => {
    setIsLoading(true)
    setMessage(null)
    
    try {
      const res = await fetch(`${API_BASE_URL}/imap-config/sync`, {
        method: 'POST'
      })
      
      const data = await res.json()
      if (data.success) {
        setMessage({ type: 'success', text: data.message })
        await loadConfig()
      } else {
        setMessage({ type: 'error', text: data.message })
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Sync failed' })
    } finally {
      setIsLoading(false)
    }
  }

  const handlePreview = async () => {
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/imap-config/preview`)
      if (res.ok) {
        const data = await res.json()
        setPreviewEmails(data.emails || [])
        setShowPreview(true)
      }
    } catch (e) {
      setMessage({ type: 'error', text: 'Failed to preview emails' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div>
      <div className="info-text" style={{ marginBottom: '1rem' }}>
        Connect to your email to automatically identify who made each payment by matching card numbers in ConEd payment confirmation emails.
      </div>

      {/* Enable Toggle */}
      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <input
          type="checkbox"
          id="imap-enabled"
          checked={config.enabled}
          onChange={(e) => setConfig({ ...config, enabled: e.target.checked })}
        />
        <label htmlFor="imap-enabled" style={{ fontWeight: 500 }}>Enable Email Integration</label>
      </div>

      {/* IMAP Server */}
      <div className="ha-form-group">
        <label className="ha-form-label">IMAP Server</label>
        <input
          type="text"
          className="ha-form-input"
          value={config.server}
          onChange={(e) => setConfig({ ...config, server: e.target.value })}
          placeholder="imap.gmail.com"
        />
        <div className="info-text">
          Gmail: imap.gmail.com | Outlook: outlook.office365.com | Yahoo: imap.mail.yahoo.com
        </div>
      </div>

      {/* Port & SSL */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
        <div className="ha-form-group">
          <label className="ha-form-label">Port</label>
          <input
            type="number"
            className="ha-form-input"
            value={config.port}
            onChange={(e) => setConfig({ ...config, port: parseInt(e.target.value) || 993 })}
          />
        </div>
        <div className="ha-form-group">
          <label className="ha-form-label">Days to Search</label>
          <input
            type="number"
            className="ha-form-input"
            value={config.days_back}
            onChange={(e) => setConfig({ ...config, days_back: parseInt(e.target.value) || 30 })}
          />
        </div>
      </div>

      {/* Email & Password */}
      <div className="ha-form-group">
        <label className="ha-form-label">Email Address</label>
        <input
          type="email"
          className="ha-form-input"
          value={config.email}
          onChange={(e) => setConfig({ ...config, email: e.target.value })}
          placeholder="your@email.com"
        />
      </div>

      <div className="ha-form-group">
        <label className="ha-form-label">Password / App Password</label>
        <input
          type="password"
          className="ha-form-input"
          value={config.password}
          onChange={(e) => setConfig({ ...config, password: e.target.value })}
          placeholder="••••••••"
        />
        <div className="info-text">
          For Gmail, use an App Password (not your regular password). Enable 2FA first, then generate at: Google Account → Security → App passwords
        </div>
      </div>

      {/* SSL Toggle */}
      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <input
          type="checkbox"
          id="imap-ssl"
          checked={config.use_ssl}
          onChange={(e) => setConfig({ ...config, use_ssl: e.target.checked })}
        />
        <label htmlFor="imap-ssl">Use SSL/TLS</label>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="ha-button ha-button-primary"
        >
          {isLoading ? 'Saving...' : 'Save Configuration'}
        </button>
        <button
          onClick={handleTest}
          disabled={isLoading || !config.server}
          className="ha-button"
          style={{ backgroundColor: '#ff9800', color: 'white' }}
        >
          Test Connection
        </button>
        <button
          onClick={handleSync}
          disabled={isLoading || !config.enabled || !config.server}
          className="ha-button"
          style={{ backgroundColor: '#4caf50', color: 'white' }}
        >
          Sync Emails Now
        </button>
        <button
          onClick={handlePreview}
          disabled={isLoading || !config.server}
          className="ha-button"
          style={{ backgroundColor: '#9c27b0', color: 'white' }}
        >
          Preview Emails
        </button>
      </div>

      {/* Last Sync */}
      {lastSync && (
        <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '1rem' }}>
          Last sync: {formatTZ(lastSync)}
        </div>
      )}

      {/* Message */}
      {message && (
        <div style={{
          padding: '0.75rem',
          borderRadius: '4px',
          backgroundColor: message.type === 'error' ? '#ffebee' : '#e8f5e9',
          color: message.type === 'error' ? '#c62828' : '#2e7d32',
          fontSize: '0.85rem',
          marginBottom: '1rem'
        }}>
          {message.text}
        </div>
      )}

      {/* Email Preview */}
      {showPreview && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <strong>Found {previewEmails.length} payment emails</strong>
            <button onClick={() => setShowPreview(false)} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
          </div>
          <div style={{ maxHeight: '200px', overflow: 'auto', fontSize: '0.8rem', backgroundColor: '#f5f5f5', padding: '0.5rem', borderRadius: '4px' }}>
            {previewEmails.length === 0 ? (
              <div style={{ color: '#666' }}>No ConEd payment emails found in the last {config.days_back} days</div>
            ) : (
              previewEmails.map((email, idx) => (
                <div key={idx} style={{ padding: '0.5rem', borderBottom: '1px solid #e0e0e0' }}>
                  <div><strong>{email.amount || 'Unknown amount'}</strong> - Card: *{email.card_last_four || 'N/A'}</div>
                  <div style={{ color: '#666' }}>{email.date} • {email.subject}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
