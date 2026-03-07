"""
Meter Service for Con Edison Usage Readings

Uses the opower library (https://github.com/tronikos/opower) to fetch
meter readings from Con Edison's Opower API.

The opower library is the same one used by Home Assistant's official
Opower integration and supports Con Edison with TOTP MFA.

Note: This uses hourly historical data (typically delayed 1-24 hours)
rather than true realtime data, which requires special smart meter
enrollment with Con Edison.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

import aiohttp

logger = logging.getLogger(__name__)

# Singleton instance
_meter_service: Optional['MeterService'] = None


class MeterService:
    """Service for fetching and caching meter readings from Con Edison via Opower."""
    
    def __init__(self):
        self.last_reading: Optional[Dict[str, Any]] = None
        self.last_reading_time: Optional[datetime] = None
        self.config: Optional[Dict[str, Any]] = None
        self._polling_task: Optional[asyncio.Task] = None
        self._running = False
        self._opower = None
        self._session = None
        self._accounts: List[Any] = []
    
    def is_configured(self) -> bool:
        """Check if meter service is properly configured.
        
        Requires email, password, and totp_secret for opower/ConEd authentication.
        """
        if not self.config:
            return False
        # opower ConEd requires: email, password, totp_secret
        required = ['email', 'password', 'totp_secret']
        return all(self.config.get(k) for k in required)
    
    def is_enabled(self) -> bool:
        """Check if meter tracking is enabled."""
        return self.config and self.config.get('enabled', False) and self.is_configured()
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize meter with configuration from database."""
        try:
            from opower import Opower, create_cookie_jar
            
            self.config = config
            
            if not self.is_configured():
                logger.warning("Meter service not fully configured")
                return False
            
            # Handle password - may be plain text (prefixed with 'plain:') or encrypted
            password = config.get('password', '')
            if password.startswith('plain:'):
                # Already decrypted, strip the prefix
                password = password[6:]
            elif password:
                # Try to decrypt
                try:
                    from main import decrypt_data
                    password = decrypt_data(password)
                except Exception:
                    # Failed to decrypt, use as-is
                    pass
            
            # Close existing session if any
            if hasattr(self, '_session') and self._session:
                await self._session.close()
            
            # Create session with opower's cookie jar (required for proper auth)
            self._session = aiohttp.ClientSession(cookie_jar=create_cookie_jar())
            
            # Initialize opower with ConEd utility (pass utility name as string)
            self._opower = Opower(
                session=self._session,
                utility="coned",
                username=config['email'],
                password=password,
                optional_totp_secret=config.get('totp_secret', ''),
            )
            
            logger.info("Meter service initialized (opower/ConEd with cookie_jar)")
            return True
            
        except ImportError as e:
            logger.error(f"opower library not installed: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize meter service: {e}")
            return False
    
    async def _login(self) -> bool:
        """Login to Con Edison via opower."""
        if not self._opower:
            return False
        
        try:
            await self._opower.async_login()
            logger.info("Logged in to Con Edison via opower")
            return True
        except Exception as e:
            logger.error(f"Opower login failed: {e}")
            return False
    
    async def _get_accounts(self) -> List[Any]:
        """Get accounts from opower."""
        if not self._opower:
            return []
        
        if not self._accounts:
            try:
                self._accounts = await self._opower.async_get_accounts()
                logger.info(f"Found {len(self._accounts)} opower account(s)")
            except Exception as e:
                logger.error(f"Failed to get opower accounts: {e}")
        
        return self._accounts
    
    async def fetch_reading(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest meter reading from Con Edison using hourly historical data.
        
        Uses opower's hourly usage API which provides data typically delayed 1-24 hours.
        This is more reliable than realtime API which requires special smart meter enrollment.
        """
        if not self.is_configured():
            logger.error("Meter not configured")
            return None
        
        try:
            from opower import AggregateType
            
            # Login if needed
            if not await self._login():
                return None
            
            # Get accounts
            accounts = await self._get_accounts()
            if not accounts:
                logger.error("No opower accounts found")
                return None
            
            # Get first electric account
            account = accounts[0]
            
            # Fetch last 48 hours of hourly data to ensure we get recent readings
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(hours=48)
            
            reads = await self._opower.async_get_cost_reads(
                account,
                AggregateType.HOUR,
                start_date,
                end_date
            )
            
            if not reads:
                logger.warning("No hourly readings available")
                return None
            
            # Get the most recent reading (last in list)
            latest = reads[-1]
            
            reading = {
                'start_time': latest.start_time.isoformat() if latest.start_time else None,
                'end_time': latest.end_time.isoformat() if latest.end_time else None,
                'value': float(latest.consumption) if latest.consumption is not None else None,
                'unit': 'kWh',
                'data_type': 'hourly',
                'fetched_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.last_reading = reading
            self.last_reading_time = datetime.now(timezone.utc)
            
            # Cache to database
            import db
            await db.save_meter_reading_db(reading)
            
            logger.info(f"Meter reading fetched: {reading['value']} {reading['unit']} (hourly data from {latest.end_time})")
            return reading
            
        except Exception as e:
            logger.error(f"Failed to fetch meter reading: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def fetch_forecast(self) -> Optional[Dict[str, Any]]:
        """Fetch the current billing period forecast from Con Edison."""
        if not self.is_configured():
            return None
        
        try:
            if not await self._login():
                return None
            
            forecasts = await self._opower.async_get_forecast()
            if not forecasts:
                return None
            
            forecast = forecasts[0]
            forecast_data = {
                'start_date': forecast.start_date.isoformat() if forecast.start_date else None,
                'end_date': forecast.end_date.isoformat() if forecast.end_date else None,
                'usage_to_date': forecast.usage_to_date,
                'forecasted_usage': forecast.forecasted_usage,
                'cost_to_date': forecast.cost_to_date,
                'forecasted_cost': forecast.forecasted_cost,
                'unit': str(forecast.unit_of_measure) if forecast.unit_of_measure else 'KWH',
                'fetched_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Cache to database
            import db
            await db.save_meter_forecast_db(forecast_data)
            
            return forecast_data
        except Exception as e:
            logger.error(f"Failed to fetch forecast: {e}")
            return None
    
    async def get_cached_forecast(self) -> Optional[Dict[str, Any]]:
        """Get the most recent cached forecast."""
        import db
        return await db.get_meter_forecast_db()
    
    async def fetch_quarter_hour_reads(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Fetch quarter-hour (15-minute) usage data for real-time chart.
        
        Args:
            hours: Number of hours to fetch (default 24, max ~144 hours / 6 days)
        
        Returns:
            List of readings with start_time, end_time, consumption
        """
        if not self.is_configured():
            logger.error("Meter not configured")
            return []
        
        try:
            from opower import AggregateType
            
            # Login if needed
            if not await self._login():
                return []
            
            # Get accounts
            accounts = await self._get_accounts()
            if not accounts:
                logger.error("No opower accounts found")
                return []
            
            account = accounts[0]
            
            # Request a wider window: Con Edison data is typically delayed 1-24 hours.
            # API max is 6 days. Request full 6 days to capture delayed data and store all.
            end_date = datetime.now(timezone.utc)
            fetch_hours = min(max(hours, 24), 144)  # At least 24h, max 6 days (API limit)
            start_date = end_date - timedelta(hours=fetch_hours)
            
            reads = await self._opower.async_get_cost_reads(
                account,
                AggregateType.QUARTER_HOUR,
                start_date,
                end_date
            )
            
            # Fallback: Con Edison often provides hourly data only (no quarter-hour unless realtime enrollment)
            if not reads:
                logger.info("No quarter-hour data, trying hourly fallback")
                reads = await self._opower.async_get_cost_reads(
                    account,
                    AggregateType.HOUR,
                    start_date,
                    end_date
                )
                if reads:
                    # Expand each hour into 4 x 15-min slots (divide consumption evenly)
                    from datetime import timedelta
                    result = []
                    for r in reads:
                        if r.start_time and r.end_time and r.consumption is not None:
                            val = float(r.consumption) / 4.0
                            delta = timedelta(minutes=15)
                            for i in range(4):
                                st = r.start_time + (delta * i)
                                et = st + delta
                                result.append({
                                    'start_time': st.isoformat(),
                                    'end_time': et.isoformat(),
                                    'consumption': val,
                                })
                    reads = result
                else:
                    logger.warning("No hourly readings available either")
                    return []
            else:
                result = None  # Will build below from reads
            
            if result is None:
                # Convert quarter-hour reads to dict format
                result = [
                    {
                        'start_time': r.start_time.isoformat() if r.start_time else None,
                        'end_time': r.end_time.isoformat() if r.end_time else None,
                        'consumption': float(r.consumption) if r.consumption is not None else 0,
                    }
                    for r in reads
                ]
            
            # Store all data to DB (up to 6 days). Chart shows last 24h from most recent.
            import db
            await db.save_realtime_readings_db(result)
            
            logger.info(f"Fetched {len(result)} readings, stored all for 24h chart")
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch quarter-hour reads: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information including smart meter status."""
        if not self.is_configured():
            return None
        
        try:
            if not await self._login():
                return None
            
            accounts = await self._get_accounts()
            if not accounts:
                return None
            
            account = accounts[0]
            
            # Check realtime support
            has_realtime = False
            realtime_error = None
            if self._opower.utility.supports_realtime_usage():
                try:
                    meters = await self._opower._async_get_meters(account)
                    has_realtime = len(meters) > 0
                except Exception as e:
                    realtime_error = str(e)
            
            return {
                'account_uuid': account.uuid,
                'utility_account_id': account.utility_account_id,
                'meter_type': str(account.meter_type) if account.meter_type else None,
                'read_resolution': str(account.read_resolution) if account.read_resolution else None,
                'has_realtime_access': has_realtime,
                'realtime_error': realtime_error,
                'customer_uuid': account.customer.uuid if account.customer else None
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None
    
    async def get_cached_reading(self) -> Optional[Dict[str, Any]]:
        """Get the most recent cached reading."""
        if self.last_reading:
            return self.last_reading
        
        # Try to load from database
        import db
        cached = await db.get_meter_reading_db()
        if cached:
            self.last_reading = cached
            return cached
        
        return None
    
    # Minimum = quarter-hour data resolution (Con Edison updates every 15 min)
    MIN_POLLING_MINUTES = 15

    async def start_polling(self, interval_minutes: int = 15):
        """Start background polling for meter readings."""
        if self._running:
            logger.warning("Meter polling already running")
            return
        
        interval_minutes = max(interval_minutes, self.MIN_POLLING_MINUTES)
        self._running = True
        interval_seconds = interval_minutes * 60
        
        async def poll_loop():
            while self._running:
                try:
                    if self.is_enabled():
                        # Latest hourly reading (data saved to DB for integration to poll)
                        await self.fetch_reading()
                        # 6-day data for History chart (API max); chart shows last 24h
                        await self.fetch_quarter_hour_reads(144)
                        # Also fetch forecast data
                        await self.fetch_forecast()
                except Exception as e:
                    logger.error(f"Meter polling error: {e}")
                
                await asyncio.sleep(interval_seconds)
        
        self._polling_task = asyncio.create_task(poll_loop())
        logger.info(f"Meter polling started (interval: {interval_minutes} minutes)")
    
    async def stop_polling(self):
        """Stop background polling."""
        self._running = False
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None
        
        # Close session
        if hasattr(self, '_session') and self._session:
            await self._session.close()
            self._session = None
        
        logger.info("Meter polling stopped")


def get_meter_service() -> MeterService:
    """Get or create the singleton meter service instance."""
    global _meter_service
    if _meter_service is None:
        _meter_service = MeterService()
    return _meter_service


async def init_meter_service():
    """Initialize meter service from database config."""
    import db
    
    service = get_meter_service()
    config = await db.get_meter_config_db()
    
    if config and config.get('enabled'):
        # Decrypt password for opower and mark as plain
        if config.get('password'):
            try:
                from main import decrypt_data
                config['password'] = 'plain:' + decrypt_data(config['password'])
            except Exception:
                pass
        
        success = await service.initialize(config)
        if success:
            interval = config.get('polling_interval', 15)
            await service.start_polling(interval)
            return True
    
    return False
