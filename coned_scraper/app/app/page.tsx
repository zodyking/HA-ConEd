'use client'

import { useState, useEffect } from 'react'
import Settings from '../components/Settings'
import AccountLedger from '../components/AccountLedger'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'account-ledger' | 'settings'>('account-ledger')
  
  // Listen for custom events from Settings password modal
  useEffect(() => {
    const handleNavigateToLedger = () => {
      setActiveTab('account-ledger')
    }
    
    window.addEventListener('navigateToLedger', handleNavigateToLedger)
    
    return () => {
      window.removeEventListener('navigateToLedger', handleNavigateToLedger)
    }
  }, [])

  return (
    <div className="ha-container">
      <div className="ha-header">
        <div className="ha-header-content">
          <div className="ha-logo-container">
            <img 
              src="images/logo.svg" 
              alt="ConEd Logo" 
              width={100}
              height={20}
              style={{ filter: 'brightness(0) invert(1)' }}
            />
          </div>
          <nav className="ha-nav">
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
        {activeTab === 'account-ledger' && <AccountLedger onNavigate={(tab) => setActiveTab(tab === 'console' ? 'settings' : tab)} />}
        {activeTab === 'settings' && <Settings />}
      </div>
    </div>
  )
}
