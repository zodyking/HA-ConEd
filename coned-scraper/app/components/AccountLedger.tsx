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

interface PayeeUser {
  id: number
  name: string
  is_default: boolean
}

export default function AccountLedger({ onNavigate }: { onNavigate?: (tab: 'console' | 'settings') => void }) {
  const [ledgerData, setLedgerData] = useState<LedgerData | null>(null)
  const [screenshotPath, setScreenshotPath] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [apiError, setApiError] = useState<string | null>(null)
  const [showScreenshotModal, setShowScreenshotModal] = useState(false)
  const [showPdfModal, setShowPdfModal] = useState(false)
  const [pdfExists, setPdfExists] = useState(false)
  
  // Payment attribution modal state
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null)
  const [payeeUsers, setPayeeUsers] = useState<PayeeUser[]>([])
  const [isAttributing, setIsAttributing] = useState(false)

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

  const loadPayeeUsers = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/payee-users`)
      if (res.ok) {
        const data = await res.json()
        setPayeeUsers(data.users || [])
      }
    } catch {
      // Silently fail
    }
  }, [])

  const handlePaymentClick = (payment: Payment) => {
    setSelectedPayment(payment)
    loadPayeeUsers()
    setShowPaymentModal(true)
  }

  const handleAttributePayment = async (userId: number) => {
    if (!selectedPayment) return
    setIsAttributing(true)
    try {
      const res = await fetch(`${API_BASE_URL}/payments/attribute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          payment_id: selectedPayment.id,
          user_id: userId,
          method: 'manual'
        })
      })
      if (res.ok) {
        await loadLedgerData() // Refresh data
        setShowPaymentModal(false)
        setSelectedPayment(null)
      }
    } finally {
      setIsAttributing(false)
    }
  }

  const handleClearAttribution = async () => {
    if (!selectedPayment) return
    setIsAttributing(true)
    try {
      const res = await fetch(`${API_BASE_URL}/payments/${selectedPayment.id}/attribution`, {
        method: 'DELETE'
      })
      if (res.ok) {
        await loadLedgerData() // Refresh data
        setShowPaymentModal(false)
        setSelectedPayment(null)
      }
    } finally {
      setIsAttributing(false)
    }
  }

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

      {/* Payment Attribution Modal */}
      {showPaymentModal && selectedPayment && (
        <div
          style={{
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '1rem'
          }}
          onClick={() => setShowPaymentModal(false)}
        >
          <div
            style={{
              backgroundColor: 'white',
              borderRadius: '12px',
              padding: '1.5rem',
              maxWidth: '400px',
              width: '100%',
              boxShadow: '0 4px 20px rgba(0,0,0,0.3)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#333' }}>
              Assign Payment
            </h3>
            
            <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.75rem', color: '#666' }}>Payment Details</div>
              <div style={{ fontWeight: 600, color: '#4caf50', fontSize: '1.1rem' }}>{selectedPayment.amount}</div>
              <div style={{ fontSize: '0.75rem', color: '#666' }}>{selectedPayment.payment_date}</div>
              {selectedPayment.payee_name && (
                <div style={{ marginTop: '0.5rem', fontSize: '0.75rem' }}>
                  <span style={{ color: '#999' }}>Currently assigned to: </span>
                  <span style={{ fontWeight: 500, color: '#1565c0' }}>{selectedPayment.payee_name}</span>
                </div>
              )}
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: '0.5rem' }}>Assign to:</div>
              {payeeUsers.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {payeeUsers.map(user => (
                    <button
                      key={user.id}
                      onClick={() => handleAttributePayment(user.id)}
                      disabled={isAttributing}
                      style={{
                        padding: '0.6rem 1rem',
                        backgroundColor: selectedPayment.payee_user_id === user.id ? '#e3f2fd' : '#f8f9fa',
                        border: selectedPayment.payee_user_id === user.id ? '2px solid #03a9f4' : '1px solid #ddd',
                        borderRadius: '8px',
                        cursor: isAttributing ? 'wait' : 'pointer',
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        textAlign: 'left',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                    >
                      <span>{user.name}</span>
                      {user.is_default && (
                        <span style={{ fontSize: '0.65rem', color: '#999' }}>(default)</span>
                      )}
                    </button>
                  ))}
                </div>
              ) : (
                <div style={{ color: '#999', fontSize: '0.85rem', textAlign: 'center', padding: '1rem' }}>
                  No payee users configured. Add users in Settings → Payees.
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              {selectedPayment.payee_status === 'confirmed' && (
                <button
                  onClick={handleClearAttribution}
                  disabled={isAttributing}
                  style={{
                    padding: '0.5rem 1rem',
                    backgroundColor: '#fff3e0',
                    color: '#e65100',
                    border: '1px solid #ffcc80',
                    borderRadius: '6px',
                    cursor: isAttributing ? 'wait' : 'pointer',
                    fontSize: '0.85rem'
                  }}
                >
                  Unassign
                </button>
              )}
              <button
                onClick={() => setShowPaymentModal(false)}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#e0e0e0',
                  color: '#333',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '0.85rem'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
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
                            className="ha-payment-entry ha-payment-clickable"
                            onClick={() => handlePaymentClick(payment)}
                            style={{ cursor: 'pointer' }}
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
                                        title="Click to assign payee"
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
                ))}

                {/* Orphan Payments (not linked to any bill) */}
                {orphan_payments.length > 0 && (
                  <div className="ha-bill-card" style={{ borderLeftColor: '#ff9800' }}>
                    <div className="ha-bill-header" style={{ backgroundColor: '#fff3e0', color: '#e65100' }}>
                      Unlinked Payments
                    </div>
                    {orphan_payments.map((payment) => (
                      <div 
                        key={payment.id} 
                        className="ha-payment-entry ha-payment-clickable"
                        onClick={() => handlePaymentClick(payment)}
                        style={{ cursor: 'pointer' }}
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
                                    title="Click to assign payee"
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
