'use client'

import { useState, useEffect, useCallback } from 'react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

function formatTimestamp(timestamp: string): { date: string, time: string } {
  try {
    const date = new Date(timestamp)
    const dateStr = date.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })
    const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })
    return { date: dateStr, time: timeStr }
  } catch {
    return { date: timestamp, time: '' }
  }
}

export default function AccountLedger() {
  const [scrapedData, setScrapedData] = useState<ScrapedData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)

  const loadScrapedData = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/scraped-data?limit=50`)
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

  if (isLoading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading account ledger...</div>
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
      <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
        No account ledger data yet. Start the scraper to collect data.
      </div>
    )
  }

  const latestData = scrapedData[0]
  const timestamp = formatTimestamp(latestData.timestamp)
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
  const groupedBills: Array<{ bill: any, payments: Array<any> }> = []
  const assignedPaymentIndices = new Set<number>()

  bills.forEach((bill, billIndex) => {
    try {
      const billCycleDateStr = bill.bill_cycle_date || bill.bill_date || ''
      const billCycleEndDate = new Date(billCycleDateStr)
      const previousBillCycleEndDate = billIndex > 0 
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

          if (previousBillCycleEndDate === null) {
            belongsToThisBill = paymentDate > billCycleEndDate
          } else {
            belongsToThisBill = paymentDate > billCycleEndDate && paymentDate <= previousBillCycleEndDate
          }

          if (belongsToThisBill) {
            billPayments.push(payment)
            assignedPaymentIndices.add(paymentIndex)
          }
        } catch (e) {
          console.warn('Failed to parse payment date:', payment, e)
        }
      })

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
            <strong>Date:</strong> <span>{timestamp.date}</span>
            <strong>Time:</strong> <span>{timestamp.time}</span>
            <strong>Account Balance:</strong> <span className="ha-summary-balance">{accountBalance}</span>
            {screenshotPath && (
              <>
                <strong>Screenshot:</strong>
                <a 
                  href={`${API_BASE_URL}/api/screenshot/${screenshotPath.split('/').pop() || screenshotPath}`}
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
            <div className="ha-empty-state">
              No bill history ledger data available. Run the scraper to collect data.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

