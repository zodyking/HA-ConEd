'use client'

import { useState, useEffect } from 'react'
import Dashboard from './components/Dashboard'
import Settings from './components/Settings'

export default function Home() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'settings'>('dashboard')

  return (
    <div className="container">
      <div className="header">
        <h1>ConEd Scraper</h1>
        <nav className="nav">
          <button
            className={`nav-button ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            Dashboard
          </button>
          <button
            className={`nav-button ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => setActiveTab('settings')}
          >
            Settings
          </button>
        </nav>
      </div>

      <div className="content">
        {activeTab === 'dashboard' && <Dashboard />}
        {activeTab === 'settings' && <Settings />}
      </div>
    </div>
  )
}
