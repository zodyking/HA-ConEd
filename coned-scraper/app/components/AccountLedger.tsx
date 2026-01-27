'use client'

import { useState, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { formatDate, formatTimestamp } from '../lib/timezone'

// Dynamically import PDF viewer to avoid SSR issues
const PdfViewer = dynamic(() => import('./PdfViewer'), { ssr: false })

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api'

// Types for database-driven ledger data
interface Payment {
  id: number
  bill_id: number | null
  payment_date: string
  description: string
  amount: string
  amount_numeric: number | null
  first_scraped_at: string
  last_scraped_at: string
  scrape_count: number
  scrape_order: number | null
  payee_status: 'confirmed' | 'pending' | 'unverified'
  payee_user_id: number | null
  payee_name: string | null
  card_last_four: string | null
  verification_method: string | null
}

interface Bill {
  id: number
  bill_cycle_date: string
  bill_date: string | null
  month_range: string
  bill_total: string
  amount_numeric: number | null
  first_scraped_at: string
  last_scraped_at: string
  scrape_count: number
  payments: Payment[]
}

interface LedgerData {
  account_balance: string | null
  balance_updated_at: string | null
  latest_payment: Payment | null
  latest_bill: Bill | null
  bills: Bill[]
  orphan_payments: Payment[]
}

// Helper component to format dates
function FormattedDate({ date, fallback }: { date: string | null | undefined, fallback?: string }) {
  if (!date) return <>{fallback || ''}</>
  return <>{formatDate(date, { year: 'numeric', month: 'short', day: 'numeric' })}</>
}

// Bill Payee Summary Component
interface PayeeSummary {
  user_id: number
  name: string
  responsibility_percent: number
  amount_owed: number
  amount_paid: number
  rollover_from_previous: number
  current_balance: number
  status: 'paid' | 'partial' | 'unpaid'
}

interface BillSummaryData {
  bill_id: number
  bill_total: number
  total_paid: number
  bill_balance: number
  bill_status: 'paid' | 'partial' | 'unpaid'
  payee_summaries: PayeeSummary[]
}

function BillPayeeSummary({ 
  billId, 
  billSummaries, 
  loadBillSummary 
}: { 
  billId: number
  billSummaries: {[key: number]: BillSummaryData}
  loadBillSummary: (id: number) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const summary = billSummaries[billId]
  
  const handleToggle = () => {
    if (!expanded && !summary) {
      loadBillSummary(billId)
    }
    setExpanded(!expanded)
  }

  // Check if there are any payee responsibilities configured
  const hasResponsibilities = summary?.payee_summaries?.some(p => p.responsibility_percent > 0)

  if (!expanded) {
    return (
      <button
        onClick={handleToggle}
        style={{
          width: '100%',
          padding: '0.4rem',
          backgroundColor: '#f8f9fa',
          border: '1px dashed #ddd',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.7rem',
          color: '#666',
          marginTop: '0.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.3rem'
        }}
      >
        <span>▶</span> View Payee Breakdown
      </button>
    )
  }

  return (
    <div style={{ 
      marginTop: '0.5rem', 
      padding: '0.6rem', 
      backgroundColor: '#f5f5f5', 
      borderRadius: '6px',
      border: '1px solid #e0e0e0'
    }}>
      <div 
        onClick={handleToggle}
        style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          cursor: 'pointer',
          marginBottom: summary ? '0.5rem' : 0
        }}
      >
        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#333' }}>
          Payee Breakdown
        </span>
        <span style={{ fontSize: '0.7rem', color: '#999' }}>▼ collapse</span>
      </div>

      {!summary ? (
        <div style={{ fontSize: '0.7rem', color: '#999', textAlign: 'center', padding: '0.5rem' }}>
          Loading...
        </div>
      ) : !hasResponsibilities ? (
        <div style={{ fontSize: '0.7rem', color: '#999', textAlign: 'center', padding: '0.5rem' }}>
          No payee responsibilities configured. Set them in Settings → Payees.
        </div>
      ) : (
        <div>
          {/* Bill Status */}
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            marginBottom: '0.5rem',
            padding: '0.4rem',
            backgroundColor: summary.bill_status === 'paid' ? '#e8f5e9' : summary.bill_status === 'partial' ? '#fff3e0' : '#ffebee',
            borderRadius: '4px',
            fontSize: '0.7rem'
          }}>
            <span>Bill Total: <strong>${summary.bill_total.toFixed(2)}</strong></span>
            <span>Paid: <strong style={{ color: '#4caf50' }}>${summary.total_paid.toFixed(2)}</strong></span>
            {summary.bill_balance > 0.01 && (
              <span>Remaining: <strong style={{ color: '#f44336' }}>${summary.bill_balance.toFixed(2)}</strong></span>
            )}
          </div>

          {/* Payee Breakdown */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
            {summary.payee_summaries.filter(p => p.responsibility_percent > 0).map(payee => (
              <div 
                key={payee.user_id}
                style={{
                  padding: '0.4rem 0.5rem',
                  backgroundColor: 'white',
                  borderRadius: '4px',
                  border: `1px solid ${payee.status === 'paid' ? '#4caf50' : payee.status === 'partial' ? '#ff9800' : '#f44336'}`,
                  fontSize: '0.7rem'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                  <span style={{ fontWeight: 600 }}>{payee.name}</span>
                  <span style={{ 
                    padding: '0.1rem 0.3rem', 
                    borderRadius: '3px',
                    backgroundColor: payee.status === 'paid' ? '#e8f5e9' : payee.status === 'partial' ? '#fff3e0' : '#ffebee',
                    color: payee.status === 'paid' ? '#2e7d32' : payee.status === 'partial' ? '#e65100' : '#c62828',
                    fontSize: '0.6rem',
                    fontWeight: 600
                  }}>
                    {payee.responsibility_percent}% share
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', color: '#666', fontSize: '0.65rem' }}>
                  <span>Owes: ${payee.amount_owed.toFixed(2)}</span>
                  <span>Paid: ${payee.amount_paid.toFixed(2)}</span>
                  {payee.rollover_from_previous !== 0 && (
                    <span style={{ color: payee.rollover_from_previous > 0 ? '#f44336' : '#4caf50' }}>
                      Rollover: {payee.rollover_from_previous > 0 ? '+' : ''}${payee.rollover_from_previous.toFixed(2)}
                    </span>
                  )}
                </div>
                {payee.current_balance !== 0 && (
                  <div style={{ 
                    marginTop: '0.2rem', 
                    fontWeight: 600, 
                    color: payee.current_balance > 0 ? '#f44336' : '#4caf50',
                    fontSize: '0.7rem'
                  }}>
                    {payee.current_balance > 0 ? `Owes: $${payee.current_balance.toFixed(2)}` : `Credit: $${Math.abs(payee.current_balance).toFixed(2)}`}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}


export default function AccountLedger({ onNavigate }: { onNavigate?: (tab: 'console' | 'settings') => void }) {
  const [ledgerData, setLedgerData] = useState<LedgerData | null>(null)
  const [screenshotPath, setScreenshotPath] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)
  const [showScreenshotModal, setShowScreenshotModal] = useState(false)
  const [showPdfModal, setShowPdfModal] = useState(false)
  const [pdfExists, setPdfExists] = useState(false)

  // Bill summary state
  const [billSummaries, setBillSummaries] = useState<{[billId: number]: any}>({})

  const loadLedgerData = useCallback(async () => {
    try {
      // Fetch from the new database-driven endpoint
      const response = await fetch(`${API_BASE_URL}/ledger`)
      if (response.ok) {
        const data = await response.json()
        setLedgerData(data)
        setApiError(null)
      } else {
        // Fallback to legacy endpoint if /ledger fails
        const legacyResponse = await fetch(`${API_BASE_URL}/scraped-data?limit=1`)
        if (legacyResponse.ok) {
          const legacyData = await legacyResponse.json()
          if (legacyData.data?.[0]) {
            const scraped = legacyData.data[0]
            // Convert legacy format to new format
            setLedgerData({
              account_balance: scraped.data?.account_balance || null,
              balance_updated_at: scraped.timestamp,
              latest_payment: null,
              latest_bill: null,
              bills: [],
              orphan_payments: []
            })
            setScreenshotPath(scraped.screenshot_path || null)
          }
        } else {
          setApiError('Failed to load ledger data')
        }
      }
      
      // Also get screenshot from legacy data
      const screenshotRes = await fetch(`${API_BASE_URL}/scraped-data?limit=1`)
      if (screenshotRes.ok) {
        const screenshotData = await screenshotRes.json()
        if (screenshotData.data?.[0]?.screenshot_path) {
          setScreenshotPath(screenshotData.data[0].screenshot_path)
        }
      }
    } catch (error) {
      setApiError('Cannot connect to Python service. Make sure it\'s running on port 8000.')
    } finally {
      setIsLoading(false)
    }
  }, [])

  const checkPdfExists = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/latest-bill-pdf/status`)
      if (res.ok) {
        const data = await res.json()
        setPdfExists(data.exists)
      }
    } catch {
      setPdfExists(false)
    }
  }, [])

  const loadBillSummary = useCallback(async (billId: number) => {
    if (billSummaries[billId]) return // Already loaded
    try {
      const res = await fetch(`${API_BASE_URL}/bills/${billId}/summary`)
      if (res.ok) {
        const data = await res.json()
        setBillSummaries(prev => ({ ...prev, [billId]: data }))
      }
    } catch {
      // Silently fail
    }
  }, [billSummaries])

  useEffect(() => {
    loadLedgerData()
    checkPdfExists()
    // Refresh every 30 seconds
    const interval = setInterval(loadLedgerData, 30000)
    return () => clearInterval(interval)
  }, [loadLedgerData, checkPdfExists])

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
          style={{ width: '64px', height: '64px', marginBottom: '1.5rem' }} 
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

  if (!ledgerData || (!ledgerData.account_balance && ledgerData.bills.length === 0)) {
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
          style={{ width: '80px', height: '80px', marginBottom: '2rem', opacity: 0.8 }} 
        />
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#333', marginBottom: '1rem' }}>
          No Account Data Yet
        </h2>
        <p style={{ color: '#666', fontSize: '1rem', maxWidth: '500px', lineHeight: '1.6', marginBottom: '2rem' }}>
          To get started, please configure your credentials in Settings and run the scraper from the Console.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
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
              fontWeight: 500
            }}
          >
            ⚙️ Go to Settings
          </button>
        </div>
      </div>
    )
  }

  const { account_balance, latest_payment, latest_bill, bills, orphan_payments = [] } = ledgerData

  return (
    <>
      {/* Screenshot Modal */}
      {showScreenshotModal && screenshotPath && (
        <div
          style={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
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
              top: '1rem', right: '1rem',
              backgroundColor: 'white',
              border: 'none',
              borderRadius: '50%',
              width: '40px', height: '40px',
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
            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', borderRadius: '4px' }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* PDF Bill Modal */}
      {showPdfModal && pdfExists && (
        <PdfViewer
          url={`${API_BASE_URL}/bill-document`}
          onClose={() => setShowPdfModal(false)}
        />
      )}

    <div className="ha-ledger">
        {/* Account Summary Card */}
      <div className="ha-card ha-card-summary">
        <div className="ha-card-header">
          <span className="ha-card-icon">💰</span>
          <span>Account Summary</span>
        </div>
          <div className="ha-card-content" style={{ padding: '0.5rem' }}>
            {/* Compact Balance + Info Row */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '0.75rem',
              marginBottom: '0.4rem'
            }}>
              {/* Balance */}
              <div style={{ 
                textAlign: 'center',
                padding: '0.4rem 0.75rem',
                background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                borderRadius: '6px',
                flex: '0 0 auto'
              }}>
                <div style={{ fontSize: '0.5rem', color: '#666', textTransform: 'uppercase', letterSpacing: '0.3px' }}>Balance</div>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#03a9f4' }}>{account_balance || '—'}</div>
              </div>
              
              {/* Last Payment */}
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{ fontSize: '0.5rem', color: '#999', textTransform: 'uppercase' }}>Last Payment</div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#4caf50' }}>
                  {latest_payment?.amount || '—'}
                </div>
                <div style={{ fontSize: '0.55rem', color: '#666' }}>
                  {latest_payment?.payment_date || ''}
                </div>
              </div>
              
              {/* Last Bill */}
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{ fontSize: '0.5rem', color: '#999', textTransform: 'uppercase' }}>Last Bill</div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f44336' }}>
                  {latest_bill?.bill_total || '—'}
                </div>
                <div style={{ fontSize: '0.55rem', color: '#666' }}>
                  {latest_bill?.month_range || ''}
          </div>
        </div>
      </div>

            {/* Action Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
              <button
                onClick={() => screenshotPath ? setShowScreenshotModal(true) : null}
                disabled={!screenshotPath}
                style={{ 
                  padding: '0.4rem',
                  border: 'none',
                  cursor: screenshotPath ? 'pointer' : 'not-allowed',
                  backgroundColor: screenshotPath ? '#03a9f4' : '#ccc',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '0.65rem',
                  fontWeight: 500
                }}
              >
                Account
              </button>
              <button
                onClick={() => pdfExists ? setShowPdfModal(true) : onNavigate?.('settings')}
                style={{ 
                  padding: '0.4rem',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: pdfExists ? '#4caf50' : '#ff9800',
                  color: 'white',
                  borderRadius: '4px',
                  fontSize: '0.65rem',
                  fontWeight: 500
                }}
              >
                {pdfExists ? 'Latest Bill' : 'Add Bill'}
              </button>
            </div>
          </div>
        </div>

        {/* Bill History Ledger */}
      <div className="ha-card ha-card-ledger">
        <div className="ha-card-header">
          <span className="ha-card-icon">📋</span>
          <span>Bill History Ledger</span>
        </div>
        <div className="ha-card-content">
            {bills.length > 0 ? (
            <div>
                {bills.map((bill) => (
                  <div key={bill.id} className="ha-bill-card">
                    <div className="ha-bill-header">
                      Bill Cycle: {bill.bill_cycle_date}
                      {bill.month_range && ` (${bill.month_range})`}
                    </div>

                    {/* Bill Entry */}
                    <div className="ha-bill-entry">
                      <div className="ha-bill-content">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                          <span className="ha-bill-badge">Bill</span>
                          <div>
                            <div style={{ fontWeight: 600, marginBottom: '0.15rem', fontSize: '0.8rem' }}>
                              {bill.month_range || 'Bill'}
                            </div>
                            <div style={{ fontSize: '0.7rem', color: '#666' }}>
                              {bill.bill_date ? <FormattedDate date={bill.bill_date} fallback={bill.bill_cycle_date} /> : bill.bill_cycle_date}
                            </div>
                          </div>
                        </div>
                        <div className="ha-bill-amount">
                          {bill.bill_total || '-'}
                        </div>
                      </div>
                    </div>

                    {/* Payments for this bill */}
                    {bill.payments && bill.payments.length > 0 && (
                      <div>
                        {bill.payments.map((payment) => (
                          <div 
                            key={payment.id} 
                            className="ha-payment-entry"
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                <span className="ha-payment-badge">Payment</span>
                                <div>
                                  <div style={{ fontWeight: 500, marginBottom: '0.1rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                    {payment.description || 'Payment Received'}
                                    {/* Payee indicator */}
                                    {payment.payee_status === 'confirmed' && payment.payee_name && (
                                      <span style={{ 
                                        fontSize: '0.6rem', 
                                        backgroundColor: '#e3f2fd', 
                                        color: '#1565c0',
                                        padding: '0.1rem 0.3rem',
                                        borderRadius: '3px'
                                      }}>
                                        {payment.payee_name}
                                      </span>
                                    )}
                                    {payment.payee_status === 'unverified' && (
                                      <span 
                                        style={{ 
                                          fontSize: '0.6rem', 
                                          backgroundColor: '#fff3e0', 
                                          color: '#e65100',
                                          padding: '0.1rem 0.3rem',
                                          borderRadius: '3px',
                                          display: 'inline-flex',
                                          alignItems: 'center',
                                          gap: '0.2rem'
                                        }}
                                        title="Unassigned - edit in Settings → Payments"
                                      >
                                        <span className="spinner-mini">⟳</span>
                                      </span>
                                    )}
                                  </div>
                                  <div style={{ fontSize: '0.65rem', color: '#666' }}>
                                    {payment.payment_date}
                                    {payment.card_last_four && (
                                      <span style={{ marginLeft: '0.5rem', color: '#999' }}>
                                        *{payment.card_last_four}
                                      </span>
                                    )}
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

                    {/* Payee Summary for this bill */}
                    <BillPayeeSummary billId={bill.id} billSummaries={billSummaries} loadBillSummary={loadBillSummary} />
                  </div>
                ))}

                {/* Orphan Payments (not linked to any bill) */}
                {orphan_payments.length > 0 && (
                  <div className="ha-bill-card" style={{ borderLeftColor: '#ff9800' }}>
                    <div className="ha-bill-header" style={{ backgroundColor: '#fff3e0', color: '#e65100' }}>
                      ⚠️ Unlinked Payments - Assign in Settings → Payments
                    </div>
                    {orphan_payments.map((payment) => (
                      <div 
                        key={payment.id} 
                        className="ha-payment-entry"
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <span className="ha-payment-badge">Payment</span>
                            <div>
                              <div style={{ fontWeight: 500, marginBottom: '0.1rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                {payment.description || 'Payment Received'}
                                {payment.payee_status === 'confirmed' && payment.payee_name && (
                                  <span style={{ 
                                    fontSize: '0.6rem', 
                                    backgroundColor: '#e3f2fd', 
                                    color: '#1565c0',
                                    padding: '0.1rem 0.3rem',
                                    borderRadius: '3px'
                                  }}>
                                    {payment.payee_name}
                                  </span>
                                )}
                                {payment.payee_status === 'unverified' && (
                                  <span 
                                    style={{ 
                                      fontSize: '0.6rem', 
                                      backgroundColor: '#fff3e0', 
                                      color: '#e65100',
                                      padding: '0.1rem 0.3rem',
                                      borderRadius: '3px',
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      gap: '0.2rem'
                                    }}
                                    title="Unassigned - edit in Settings → Payments"
                                  >
                                    <span className="spinner-mini">⟳</span>
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: '0.65rem', color: '#666' }}>
                                {payment.payment_date}
                                {payment.card_last_four && (
                                  <span style={{ marginLeft: '0.5rem', color: '#999' }}>
                                    *{payment.card_last_four}
                                  </span>
                                )}
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
                  style={{ width: '120px', height: '120px', marginBottom: '2rem' }} 
                />
                <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#333', marginBottom: '1rem' }}>
                  No Bill History Available
                </h3>
                <p style={{ color: '#666', fontSize: '1rem', maxWidth: '500px', lineHeight: '1.6', marginBottom: '1.5rem' }}>
                  Run the scraper to populate bill history data.
                </p>
            </div>
          )}
        </div>
      </div>
    </div>
    </>
  )
}
