import { NextRequest, NextResponse } from 'next/server'

// Use API_BASE_URL from docker-compose.yml, fallback to PYTHON_API_URL or localhost
const PYTHON_API_URL = process.env.API_BASE_URL || process.env.PYTHON_API_URL || 'http://127.0.0.1:8000'

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> }
) {
  const params = await context.params
  const slug = params.slug || []
  const path = slug.join('/')
  const searchParams = request.nextUrl.searchParams.toString()
  const url = `${PYTHON_API_URL}/api/${path}${searchParams ? `?${searchParams}` : ''}`

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: `API error: ${response.status} ${response.statusText}` },
        { status: response.status }
      )
    }

    // Check if response is an image
    const contentType = response.headers.get('content-type') || ''
    if (contentType.startsWith('image/')) {
      const blob = await response.blob()
      return new NextResponse(blob, {
        headers: {
          'Content-Type': contentType,
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
        },
      })
    }

    // Otherwise, parse as JSON
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Proxy error:', error)
    return NextResponse.json(
      { error: 'Failed to connect to Python API service' },
      { status: 503 }
    )
  }
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> }
) {
  const params = await context.params
  const slug = params.slug || []
  const path = slug.join('/')
  const url = `${PYTHON_API_URL}/api/${path}`

  try {
    const body = await request.json().catch(() => null)

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      return NextResponse.json(
        { error: errorData.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Proxy error:', error)
    return NextResponse.json(
      { error: 'Failed to connect to Python API service' },
      { status: 503 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ slug: string[] }> }
) {
  const params = await context.params
  const slug = params.slug || []
  const path = slug.join('/')
  const url = `${PYTHON_API_URL}/api/${path}`

  try {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: `API error: ${response.status}` },
        { status: response.status }
      )
    }

    const data = await response.json().catch(() => ({ success: true }))
    return NextResponse.json(data)
  } catch (error) {
    console.error('Proxy error:', error)
    return NextResponse.json(
      { error: 'Failed to connect to Python API service' },
      { status: 503 }
    )
  }
}
