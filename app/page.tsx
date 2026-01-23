'use client'

import { useState } from 'react'
import Dashboard from './components/Dashboard'
import Settings from './components/Settings'
import AccountLedger from './components/AccountLedger'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'account-ledger' | 'settings'>('dashboard')

  return (
    <div className="ha-container">
      <div className="ha-header">
        <div className="ha-header-content">
          <div className="ha-logo-container">
            <img 
              src="/images/logo.svg" 
              alt="ConEd Logo" 
              width={100}
              height={20}
              style={{ filter: 'brightness(0) invert(1)' }}
            />
            <h1 className="ha-title">ConEd Scraper</h1>
          </div>
          <nav className="ha-nav">
            <button
              className={`ha-nav-button ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setActiveTab('dashboard')}
              aria-label="Dashboard"
            >
              <span className="ha-nav-icon">📊</span>
              <span>Dashboard</span>
            </button>
            <button
              className={`ha-nav-button ${activeTab === 'account-ledger' ? 'active' : ''}`}
              onClick={() => setActiveTab('account-ledger')}
              aria-label="Account Ledger"
            >
              <span className="ha-nav-icon">📋</span>
              <span>Account Ledger</span>
            </button>
            <button
              className={`ha-nav-button ${activeTab === 'settings' ? 'active' : ''}`}
              onClick={() => setActiveTab('settings')}
              aria-label="Settings"
            >
              <span className="ha-nav-icon">⚙️</span>
              <span>Settings</span>
            </button>
          </nav>
        </div>
      </div>

      <div className="ha-content">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'account-ledger' && <AccountLedger />}
        {activeTab === 'settings' && <Settings />}
      </div>
    </div>
  )
}
