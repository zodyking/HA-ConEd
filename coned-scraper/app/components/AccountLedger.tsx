'use client'

import { useState, useEffect, useCallback } from 'react'
import { formatDate, formatTime, formatTimestamp } from '../lib/timezone'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api'

// Helper component to format dates asynchronously
function FormattedDate({ date, fallback }: { date: string | null | undefined, fallback?: string }) {
  const [formatted, setFormatted] = useState(fallback || date || '')
  
  useEffect(() => {
    if (date) {
      formatDate(date, { year: 'numeric', month: 'short', day: 'numeric' })
        .then(setFormatted)
        .catch(() => setFormatted(fallback || date))
    }
  }, [date, fallback])
  
  return <>{formatted}</>
}

interface ScrapedData {
  id: number
  timestamp: string
  data: {
    account_balance?: string
    pdf_bill_url?: string
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
  const [showScreenshotModal, setShowScreenshotModal] = useState(false)
  const [showPdfModal, setShowPdfModal] = useState(false)
  const [pdfExists, setPdfExists] = useState(false)

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
    checkPdfExists()
    // Refresh every 30 seconds
    const interval = setInterval(loadScrapedData, 30000)
    return () => clearInterval(interval)
  }, [loadScrapedData])
  
  const checkPdfExists = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/latest-bill-pdf/status`)
      if (res.ok) {
        const data = await res.json()
        setPdfExists(data.exists)
      }
    } catch (e) {
      setPdfExists(false)
    }
  }

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
  const pdfBillUrl = latestData.data?.pdf_bill_url
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
  // Logic: bill_cycle_date is the END date of the billing cycle
  // Bills are sorted newest first
  // Payments for a bill occur AFTER that bill's cycle end date and BEFORE the next bill's cycle end date
  // On Con Edison's site, payments appear BEFORE (above) the bill they're for
  // In our UI, we show payments UNDER the bill
  const groupedBills: Array<{ bill: any, payments: Array<any> }> = []
  const assignedPaymentIndices = new Set<number>()

  bills.forEach((bill, billIndex) => {
    try {
      const billDateStr = bill.bill_cycle_date || bill.bill_date || ''
      const billDate = new Date(billDateStr)
      
      // Get the next newer bill's date (since bills are sorted newest first)
      // For the newest bill (index 0), nextNewerBillDate will be null
      const nextNewerBillDate = billIndex > 0
        ? new Date(bills[billIndex - 1].bill_cycle_date || bills[billIndex - 1].bill_date || 0)
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
          // - Payment date is AFTER this bill's cycle end date
          // - AND payment date is BEFORE the next newer bill's cycle end date (if there is one)
          if (nextNewerBillDate === null) {
            // This is the newest bill - take payments that are after this bill's cycle end date
            belongsToThisBill = paymentDate > billDate
          } else {
            // This is an older bill - take payments between this bill and the next newer bill
            // Payment must be AFTER this bill's end date and BEFORE (or equal to) the next bill's end date
            belongsToThisBill = paymentDate > billDate && paymentDate <= nextNewerBillDate
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
    <>
      {/* Screenshot Modal for Mobile */}
      {showScreenshotModal && screenshotPath && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.9)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem'
          }}
          onClick={() => setShowScreenshotModal(false)}
        >
          <button
            onClick={() => setShowScreenshotModal(false)}
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              backgroundColor: 'white',
              border: 'none',
              borderRadius: '50%',
              width: '40px',
              height: '40px',
              fontSize: '1.5rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
              zIndex: 10000
            }}
          >
            ✕
          </button>
          <img
            src={`${API_BASE_URL}/screenshot/${screenshotPath.split('/').pop() || screenshotPath}`}
            alt="Account Balance Screenshot"
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
              borderRadius: '4px'
            }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* PDF Bill Modal */}
      {showPdfModal && pdfExists && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.9)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem'
          }}
          onClick={() => setShowPdfModal(false)}
        >
          <div
            style={{
              width: '95%',
              maxWidth: '900px',
              height: '90vh',
              backgroundColor: '#525659',
              borderRadius: '8px',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              position: 'relative'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{
              padding: '0.75rem 1rem',
              backgroundColor: '#323639',
              color: 'white',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span style={{ fontWeight: 500, fontSize: '0.9rem' }}>📄 Latest Bill</span>
              <button
                onClick={() => setShowPdfModal(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'white',
                  fontSize: '1.25rem',
                  cursor: 'pointer',
                  padding: '0.25rem'
                }}
              >
                ✕
              </button>
            </div>
            <iframe
              src={`${API_BASE_URL}/latest-bill-pdf#toolbar=0&navpanes=0&scrollbar=1`}
              style={{
                flex: 1,
                width: '100%',
                border: 'none',
                backgroundColor: '#525659'
              }}
              title="Bill PDF"
            />
          </div>
        </div>
      )}

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
          </div>
          {/* Action buttons row */}
          {(screenshotPath || pdfBillUrl) && (
            <div style={{ 
              display: 'flex', 
              gap: '0.75rem', 
              marginTop: '1rem', 
              flexWrap: 'wrap' 
            }}>
              {screenshotPath && (
                <button
                  onClick={() => setShowScreenshotModal(true)}
                  className="ha-button ha-button-primary"
                  style={{ 
                    fontSize: '0.75rem', 
                    padding: '0.5rem 1rem', 
                    display: 'inline-flex', 
                    alignItems: 'center', 
                    gap: '0.5rem', 
                    border: 'none', 
                    cursor: 'pointer',
                    borderRadius: '6px',
                    flex: '1 1 auto',
                    maxWidth: '280px',
                    justifyContent: 'center'
                  }}
                >
                  <img src="/images/Coned_snapshot.svg" alt="Screenshot" style={{ width: '18px', height: '18px' }} />
                  View Account Screenshot
                </button>
              )}
              {pdfExists ? (
                <button
                  onClick={() => setShowPdfModal(true)}
                  className="ha-button"
                  style={{ 
                    fontSize: '0.75rem', 
                    padding: '0.5rem 1rem', 
                    display: 'inline-flex', 
                    alignItems: 'center', 
                    gap: '0.5rem', 
                    border: 'none', 
                    cursor: 'pointer', 
                    backgroundColor: '#4caf50',
                    color: 'white',
                    borderRadius: '6px',
                    flex: '1 1 auto',
                    maxWidth: '280px',
                    justifyContent: 'center'
                  }}
                >
                  📄 View Latest Bill PDF
                </button>
              ) : (
                <button
                  onClick={() => onNavigate?.('settings')}
                  className="ha-button"
                  style={{ 
                    fontSize: '0.75rem', 
                    padding: '0.5rem 1rem', 
                    display: 'inline-flex', 
                    alignItems: 'center', 
                    gap: '0.5rem', 
                    border: 'none', 
                    cursor: 'pointer', 
                    backgroundColor: '#ff9800',
                    color: 'white',
                    borderRadius: '6px',
                    flex: '1 1 auto',
                    maxWidth: '280px',
                    justifyContent: 'center'
                  }}
                >
                  📄 Add Bill PDF Link
                </button>
              )}
            </div>
          )}
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
                              {bill.bill_date ? <FormattedDate date={bill.bill_date} fallback={cycleKey} /> : cycleKey}
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
    </>
  )
}

