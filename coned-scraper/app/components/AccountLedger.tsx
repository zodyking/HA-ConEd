'use client'

import { useState, useEffect, useCallback } from 'react'
import { formatDate, formatTime } from '../lib/timezone'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api'

interface ScrapedData {
  id: number
  timestamp: string
  data: {
    account_balance?: string
    bill_history?: {
      ledger: Array<{
        type: 'payment' | 'bill'
        bill_cycle_date?: string
        description?: string
        amount?: string
        month_range?: string
        bill_total?: string
        bill_date?: string
      }>
      scraped_at?: string
    }
  }
  status: string
  screenshot_path?: string
}

async function formatTimestampWithTZ(timestamp: string): Promise<{ date: string, time: string }> {
  try {
    const dateStr = await formatDate(timestamp)
    const timeStr = await formatTime(timestamp)
    return { date: dateStr, time: timeStr }
  } catch {
    return { date: timestamp, time: '' }
  }
}

export default function AccountLedger({ onNavigate }: { onNavigate?: (tab: 'console' | 'settings') => void }) {
  const [scrapedData, setScrapedData] = useState<ScrapedData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)
  const [formattedTimestamp, setFormattedTimestamp] = useState<{ date: string, time: string }>({ date: '', time: '' })

  const loadScrapedData = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/scraped-data?limit=50`)
      if (response.ok) {
        const data = await response.json()
        setScrapedData(data.data || [])
        setApiError(null)
      } else {
        setApiError('Failed to load scraped data')
      }
    } catch (error) {
      setApiError('Cannot connect to Python service. Make sure it\'s running on port 8000.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadScrapedData()
    // Refresh every 30 seconds
    const interval = setInterval(loadScrapedData, 30000)
    return () => clearInterval(interval)
  }, [loadScrapedData])

  // Format timestamp when data changes
  useEffect(() => {
    if (scrapedData.length > 0) {
      formatTimestampWithTZ(scrapedData[0].timestamp).then(setFormattedTimestamp)
    }
  }, [scrapedData])

  if (isLoading) {
    return (
      <div style={{ 
        padding: '4rem 2rem', 
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '400px'
      }}>
        <img 
          src="/images/ajax-loader.gif" 
          alt="Loading" 
          style={{ 
            width: '64px', 
            height: '64px',
            marginBottom: '1.5rem'
          }} 
        />
        <div style={{ color: '#666', fontSize: '1rem', marginTop: '1rem' }}>
          Loading account ledger...
        </div>
      </div>
    )
  }

  if (apiError) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: '#d32f2f' }}>
        {apiError}
      </div>
    )
  }

  if (scrapedData.length === 0) {
    return (
      <div style={{ 
        padding: '4rem 2rem', 
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '400px'
      }}>
        <img 
          src="/images/ajax-loader.gif" 
          alt="Setup Required" 
          style={{ 
            width: '80px', 
            height: '80px',
            marginBottom: '2rem',
            opacity: 0.8
          }} 
        />
        <h2 style={{ 
          fontSize: '1.5rem', 
          fontWeight: 600, 
          color: '#333',
          marginBottom: '1rem'
        }}>
          No Account Data Yet
        </h2>
        <p style={{ 
          color: '#666', 
          fontSize: '1rem',
          maxWidth: '500px',
          lineHeight: '1.6',
          marginBottom: '2rem'
        }}>
          To get started, please configure your credentials in Settings and run the scraper from the Console.
        </p>
        <div style={{
          display: 'flex',
          gap: '1rem',
          justifyContent: 'center',
          flexWrap: 'wrap'
        }}>
          <button
            onClick={() => onNavigate?.('settings')}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#03a9f4',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '1rem',
              cursor: 'pointer',
              fontWeight: 500,
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#0288d1'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#03a9f4'}
          >
            ⚙️ Go to Settings
          </button>
          <button
            onClick={() => onNavigate?.('console')}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#4caf50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '1rem',
              cursor: 'pointer',
              fontWeight: 500,
              transition: 'background-color 0.2s'
            }}
            onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#45a049'}
            onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#4caf50'}
          >
            📊 Go to Console
          </button>
        </div>
      </div>
    )
  }

  const latestData = scrapedData[0]
  const accountBalance = latestData.data?.account_balance || '-'
  const screenshotPath = latestData.screenshot_path
  const billHistory = latestData.data?.bill_history

  // Group bills and payments correctly
  const bills: Array<any> = []
  const payments: Array<any> = []

  if (billHistory?.ledger) {
    billHistory.ledger.forEach((entry) => {
      if (entry.type === 'bill') {
        bills.push(entry)
      } else if (entry.type === 'payment') {
        payments.push(entry)
      }
    })
  }

  // Sort bills by date (newest first)
  bills.sort((a, b) => {
    try {
      const dateA = new Date(a.bill_cycle_date || a.bill_date || 0)
      const dateB = new Date(b.bill_cycle_date || b.bill_date || 0)
      return dateB.getTime() - dateA.getTime()
    } catch {
      return 0
    }
  })

  // Sort payments by date (newest first)
  payments.sort((a, b) => {
    try {
      const dateA = new Date(a.bill_cycle_date || 0)
      const dateB = new Date(b.bill_cycle_date || 0)
      return dateB.getTime() - dateA.getTime()
    } catch {
      return 0
    }
  })

  // Group payments under their corresponding bills
  // Logic: bill_cycle_date is the START of the billing cycle
  // Bills are sorted newest first
  // Payments made AFTER a bill is issued belong to that bill
  // On Con Edison's site, payments appear BEFORE (above) the bill they're for
  // In our UI, we show payments UNDER the bill
  const groupedBills: Array<{ bill: any, payments: Array<any> }> = []
  const assignedPaymentIndices = new Set<number>()

  bills.forEach((bill, billIndex) => {
    try {
      const billDateStr = bill.bill_cycle_date || bill.bill_date || ''
      const billDate = new Date(billDateStr)
      
      // Get the next older bill's date (since bills are sorted newest first)
      const nextOlderBillDate = billIndex < bills.length - 1
        ? new Date(bills[billIndex + 1].bill_cycle_date || bills[billIndex + 1].bill_date || 0)
        : null

      const billPayments: Array<any> = []

      payments.forEach((payment, paymentIndex) => {
        if (assignedPaymentIndices.has(paymentIndex)) {
          return
        }

        try {
          const paymentDateStr = payment.bill_cycle_date || ''
          const paymentDate = new Date(paymentDateStr)

          let belongsToThisBill = false

          // Payment belongs to this bill if:
          // - Payment date is AFTER or EQUAL to this bill's date
          // - AND (for newer bills) payment date is BEFORE the next older bill's date
          // - OR (for the oldest bill) payment date is just after the bill date
          if (nextOlderBillDate === null) {
            // This is the oldest bill - take payments that are on or after this bill date
            belongsToThisBill = paymentDate >= billDate
          } else {
            // This is a newer bill - take payments between this bill and the next older bill
            belongsToThisBill = paymentDate >= billDate && paymentDate < nextOlderBillDate
          }

          if (belongsToThisBill) {
            billPayments.push(payment)
            assignedPaymentIndices.add(paymentIndex)
          }
        } catch (e) {
          console.warn('Failed to parse payment date:', payment, e)
        }
      })

      // Sort payments within each bill by date (newest first)
      billPayments.sort((a: any, b: any) => {
        try {
          const dateA = new Date(a.bill_cycle_date || 0)
          const dateB = new Date(b.bill_cycle_date || 0)
          return dateB.getTime() - dateA.getTime()
        } catch {
          return 0
        }
      })

      groupedBills.push({
        bill,
        payments: billPayments
      })
    } catch (e) {
      console.warn('Failed to parse bill date:', bill, e)
      groupedBills.push({
        bill,
        payments: []
      })
    }
  })

  // Remove duplicate bills
  const seenBillDates = new Set<string>()
  const uniqueGroupedBills = groupedBills.filter((group) => {
    const billDate = group.bill.bill_cycle_date || group.bill.bill_date || ''
    if (seenBillDates.has(billDate)) {
      return false
    }
    seenBillDates.add(billDate)
    return true
  })

  return (
    <div className="ha-ledger">
      <div className="ha-card ha-card-summary">
        <div className="ha-card-header">
          <span className="ha-card-icon">💰</span>
          <span>Account Summary</span>
        </div>
        <div className="ha-card-content">
          <div className="ha-summary-grid">
            <strong>Date:</strong> <span>{formattedTimestamp.date}</span>
            <strong>Time:</strong> <span>{formattedTimestamp.time}</span>
            <strong>Account Balance:</strong> <span className="ha-summary-balance">{accountBalance}</span>
            {screenshotPath && (
              <>
                <strong>Screenshot:</strong>
                <a 
                  href={`${API_BASE_URL}/screenshot/${screenshotPath.split('/').pop() || screenshotPath}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ha-button ha-button-primary"
                  style={{ fontSize: '0.7rem', padding: '0.4rem 0.75rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <img src="/images/Coned_snapshot.svg" alt="Screenshot" style={{ width: '16px', height: '16px' }} />
                  View Account Balance Screenshot
                </a>
              </>
            )}
          </div>
        </div>
      </div>

      <div className="ha-card ha-card-ledger">
        <div className="ha-card-header">
          <span className="ha-card-icon">📋</span>
          <span>Bill History Ledger</span>
        </div>
        <div className="ha-card-content">
          {uniqueGroupedBills.length > 0 ? (
            <div>
              {uniqueGroupedBills.map((group, idx) => {
                const bill = group.bill
                const payments = group.payments
                const cycleKey = bill.bill_cycle_date || bill.bill_date || 'Unknown'

                return (
                  <div key={`${cycleKey}-${idx}`} className="ha-bill-card">
                    <div className="ha-bill-header">
                      Bill Cycle: {cycleKey}
                      {bill?.month_range && ` (${bill.month_range})`}
                    </div>

                    <div className="ha-bill-entry">
                      <div className="ha-bill-content">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                          <span className="ha-bill-badge">Bill</span>
                          <div>
                            <div style={{ fontWeight: 600, marginBottom: '0.15rem', fontSize: '0.8rem' }}>
                              {bill.month_range || 'Bill'}
                            </div>
                            <div style={{ fontSize: '0.7rem', color: '#666' }}>
                              {bill.bill_date ? new Date(bill.bill_date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : cycleKey}
                            </div>
                          </div>
                        </div>
                        <div className="ha-bill-amount">
                          {bill.bill_total || '-'}
                        </div>
                      </div>
                    </div>

                    {payments.length > 0 && (
                      <div>
                        {payments.map((payment: any, paymentIdx: number) => (
                          <div key={paymentIdx} className="ha-payment-entry">
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                <span className="ha-payment-badge">Payment</span>
                                <div>
                                  <div style={{ fontWeight: 500, marginBottom: '0.1rem', fontSize: '0.75rem' }}>
                                    {payment.description || 'Payment Received'}
                                  </div>
                                  <div style={{ fontSize: '0.65rem', color: '#666' }}>
                                    {payment.bill_cycle_date || cycleKey}
                                  </div>
                                </div>
                              </div>
                              <div className="ha-payment-amount">
                                {payment.amount || '-'}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ) : (
            <div style={{
              padding: '4rem 2rem',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '300px'
            }}>
              <img 
                src="/images/ajax-loader.gif" 
                alt="Loading" 
                style={{ 
                  width: '120px', 
                  height: '120px',
                  marginBottom: '2rem'
                }} 
              />
              <h3 style={{
                fontSize: '1.25rem',
                fontWeight: 600,
                color: '#333',
                marginBottom: '1rem'
              }}>
                No Bill History Available
              </h3>
              <p style={{
                color: '#666',
                fontSize: '1rem',
                maxWidth: '500px',
                lineHeight: '1.6',
                marginBottom: '1.5rem'
              }}>
                The account ledger doesn't have any bill history data yet. This happens when:
              </p>
              <ul style={{
                color: '#666',
                fontSize: '0.95rem',
                textAlign: 'left',
                maxWidth: '500px',
                lineHeight: '1.8',
                marginBottom: '1.5rem',
                paddingLeft: '1.5rem'
              }}>
                <li>The scraper hasn't been run yet</li>
                <li>The latest scrape didn't capture bill history data</li>
                <li>Your account may not have any bills in the current view</li>
              </ul>
              <p style={{
                color: '#666',
                fontSize: '0.95rem',
                fontStyle: 'italic'
              }}>
                Go to the Console tab and run the scraper to collect bill history data.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

