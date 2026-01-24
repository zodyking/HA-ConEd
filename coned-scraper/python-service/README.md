# ConEd Scraper Python Service

Python service for scraping ConEd account data using browser automation.

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip

### Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
python -m playwright install chromium
```

### Running the Service

#### Option 1: Using the run script (recommended)
```bash
python run.py
```

#### Option 2: Using uvicorn directly
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Option 3: Using Python directly
```bash
python main.py
```

### Configuration

The service can be configured using environment variables:

- `API_PORT`: Port for the API server (default: 8000)
- `API_HOST`: Host to bind to (default: 0.0.0.0)
- `MQTT_HOST`: MQTT broker hostname (default: core-mosquitto)
- `MQTT_PORT`: MQTT broker port (default: 1883)
- `MQTT_USER`: MQTT username (optional)
- `MQTT_PASSWORD`: MQTT password (optional)
- `MQTT_TOPIC_PREFIX`: MQTT topic prefix (default: coned)
- `PLAYWRIGHT_HEADLESS`: Run browser in headless mode (default: true)

### API Endpoints

Once running, the API will be available at `http://localhost:8000`:

- `GET /` - Health check
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /api/totp` - Get current TOTP code
- `GET /api/settings` - Get saved credentials (masked)
- `POST /api/settings` - Save credentials
- `POST /api/scrape` - Start scraping
- `GET /api/logs` - Get log entries
- `GET /api/scraped-data` - Get scraped data
- `GET /api/scraped-data/latest` - Get latest scraped data
- `GET /api/screenshot/{filename}` - Get screenshot
- `GET /api/automated-schedule` - Get automated schedule
- `POST /api/automated-schedule` - Set automated schedule

### Data Storage

- Credentials are stored encrypted in `data/credentials.json`
- Scraped data is stored in SQLite database at `data/scraper.db`
- Screenshots are saved in the service directory

### Troubleshooting

**Playwright browsers not installed:**
```bash
python -m playwright install chromium
```

**Permission errors on Linux:**
```bash
python -m playwright install-deps chromium
```

**Port already in use:**
Change the port using the `API_PORT` environment variable:
```bash
API_PORT=8080 python run.py
```

**MQTT connection issues:**
The service will continue to work even if MQTT is unavailable. Sensors just won't be published. Check your MQTT broker settings.
