'use client'

import { useState, useCallback } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface PdfViewerProps {
  url: string
  onClose: () => void
}

export default function PdfViewer({ url, onClose }: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(1)
  const [scale, setScale] = useState<number>(1)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages)
    setLoading(false)
    setError(null)
  }, [])

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('PDF load error:', error)
    setError('Failed to load PDF')
    setLoading(false)
  }, [])

  const goToPrevPage = () => setPageNumber(prev => Math.max(prev - 1, 1))
  const goToNextPage = () => setPageNumber(prev => Math.min(prev + 1, numPages))
  const zoomIn = () => setScale(prev => Math.min(prev + 0.25, 3))
  const zoomOut = () => setScale(prev => Math.max(prev - 0.25, 0.5))
  const fitToWidth = () => setScale(1)

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.95)',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 9999
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.75rem 1rem',
        backgroundColor: '#1a1a2e',
        borderBottom: '1px solid #333',
        flexShrink: 0
      }}>
        <span style={{ color: 'white', fontWeight: 500 }}>📄 Latest Bill</span>
        
        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          {/* Zoom controls */}
          <button onClick={zoomOut} style={controlButtonStyle} title="Zoom out">−</button>
          <span style={{ color: 'white', fontSize: '0.8rem', minWidth: '50px', textAlign: 'center' }}>
            {Math.round(scale * 100)}%
          </span>
          <button onClick={zoomIn} style={controlButtonStyle} title="Zoom in">+</button>
          <button onClick={fitToWidth} style={{...controlButtonStyle, fontSize: '0.7rem', padding: '0.3rem 0.5rem'}} title="Fit">Fit</button>
          
          <div style={{ width: '1px', height: '20px', backgroundColor: '#444', margin: '0 0.5rem' }} />
          
          {/* Page navigation */}
          <button onClick={goToPrevPage} disabled={pageNumber <= 1} style={controlButtonStyle}>‹</button>
          <span style={{ color: 'white', fontSize: '0.8rem', minWidth: '60px', textAlign: 'center' }}>
            {pageNumber} / {numPages}
          </span>
          <button onClick={goToNextPage} disabled={pageNumber >= numPages} style={controlButtonStyle}>›</button>
        </div>

        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'white',
            fontSize: '1.5rem',
            cursor: 'pointer',
            padding: '0.25rem 0.5rem'
          }}
        >
          ✕
        </button>
      </div>

      {/* PDF Content */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
        padding: '1rem',
        backgroundColor: '#525659'
      }}>
        {loading && (
          <div style={{ color: 'white', padding: '2rem', textAlign: 'center' }}>
            <div style={{ marginBottom: '1rem' }}>Loading PDF...</div>
            <img src="/images/ajax-loader.gif" alt="Loading" style={{ width: '40px' }} />
          </div>
        )}
        
        {error && (
          <div style={{ color: '#ff6b6b', padding: '2rem', textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📄</div>
            <div>{error}</div>
            <button
              onClick={() => window.open(url, '_blank')}
              style={{
                marginTop: '1rem',
                padding: '0.5rem 1rem',
                backgroundColor: '#03a9f4',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Open PDF Directly
            </button>
          </div>
        )}

        <Document
          file={url}
          onLoadSuccess={onDocumentLoadSuccess}
          onLoadError={onDocumentLoadError}
          loading=""
        >
          <Page
            pageNumber={pageNumber}
            scale={scale}
            renderTextLayer={false}
            renderAnnotationLayer={false}
            loading=""
          />
        </Document>
      </div>

      {/* Mobile-friendly page navigation footer */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '1rem',
        padding: '0.75rem',
        backgroundColor: '#1a1a2e',
        borderTop: '1px solid #333'
      }}>
        <button
          onClick={goToPrevPage}
          disabled={pageNumber <= 1}
          style={{
            ...mobileNavButtonStyle,
            opacity: pageNumber <= 1 ? 0.5 : 1
          }}
        >
          ← Previous
        </button>
        <span style={{ color: 'white', fontSize: '0.9rem' }}>
          Page {pageNumber} of {numPages}
        </span>
        <button
          onClick={goToNextPage}
          disabled={pageNumber >= numPages}
          style={{
            ...mobileNavButtonStyle,
            opacity: pageNumber >= numPages ? 0.5 : 1
          }}
        >
          Next →
        </button>
      </div>
    </div>
  )
}

const controlButtonStyle: React.CSSProperties = {
  background: '#333',
  border: 'none',
  color: 'white',
  padding: '0.3rem 0.6rem',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '1rem',
  minWidth: '30px'
}

const mobileNavButtonStyle: React.CSSProperties = {
  background: '#03a9f4',
  border: 'none',
  color: 'white',
  padding: '0.5rem 1rem',
  borderRadius: '4px',
  cursor: 'pointer',
  fontSize: '0.85rem',
  fontWeight: 500
}

