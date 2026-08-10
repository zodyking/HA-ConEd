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
import math
import re
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
        self._account_summaries: Dict[str, Dict[str, Any]] = {}
    
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
            self.last_reading = None
            self.last_reading_time = None
            self._accounts = []
            self._account_summaries = {}
            
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

        # Opower stores the bearer token on the client after login. Reuse it for
        # subsequent reads: Con Edison's MFA flow explicitly does not handle
        # rapid double-logins reliably, and one API request commonly fans out
        # into account, forecast, and usage calls.
        if getattr(self._opower, "access_token", None):
            return True
        
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

    @staticmethod
    def _account_matches(account: Any, selected_account_id: str) -> bool:
        """Return whether an Opower account matches a persisted stable ID."""
        selected_account_id = str(selected_account_id or "").strip()
        if not selected_account_id:
            return False
        return selected_account_id in {
            str(getattr(account, "id", "") or ""),
            str(getattr(account, "uuid", "") or ""),
            str(getattr(account, "utility_account_id", "") or ""),
        }

    def _select_account(self, accounts: List[Any]) -> Optional[Any]:
        """Select the configured account, preserving the legacy first-account default."""
        if not accounts:
            return None

        selected_account_id = str(
            (self.config or {}).get("selected_account_id", "") or ""
        ).strip()
        if not selected_account_id:
            return accounts[0]

        for account in accounts:
            if self._account_matches(account, selected_account_id):
                return account

        available_ids = ", ".join(
            str(getattr(account, "id", "") or getattr(account, "uuid", ""))
            for account in accounts
        )
        raise ValueError(
            f"Configured Opower account was not found. Available account IDs: {available_ids}"
        )

    @staticmethod
    def _mask_account_number(value: Any) -> str:
        """Mask an account number while retaining enough digits to distinguish it."""
        value = str(value or "").strip()
        if not value:
            return ""
        visible = value[-4:]
        return f"{'*' * max(0, len(value) - len(visible))}{visible}"

    @staticmethod
    def _finite_float(value: Any) -> Optional[float]:
        """Convert an API number to a JSON-safe float, excluding NaN/infinity."""
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    async def list_accounts(self, electric_only: bool = True) -> List[Dict[str, Any]]:
        """Return selectable Opower accounts with ConEd customer metadata."""
        if not self.is_configured() or not await self._login():
            return []

        accounts = await self._get_accounts()
        customer_map: Dict[str, Dict[str, Any]] = {}
        try:
            customers = await self._opower._async_get_customers()
            customer_map = {
                str(customer.get("uuid", "")): customer
                for customer in customers
                if isinstance(customer, dict)
            }
        except Exception as exc:
            logger.debug("Could not load optional Opower customer labels: %s", exc)

        summaries: List[Dict[str, Any]] = []
        for account in accounts:
            meter_type = str(getattr(account, "meter_type", "") or "")
            if electric_only and meter_type != "ELEC":
                continue

            customer_uuid = str(
                getattr(getattr(account, "customer", None), "uuid", "") or ""
            )
            customer = customer_map.get(customer_uuid, {})
            account_id = str(
                getattr(account, "id", "") or getattr(account, "uuid", "")
            )
            address = customer.get("address", "")
            if isinstance(address, dict):
                address = ", ".join(
                    str(value).strip() for value in address.values() if value
                )
            address = re.sub(r"\s+", " ", str(address or "")).strip()

            summary = {
                "id": account_id,
                "uuid": str(getattr(account, "uuid", "") or ""),
                "utility_account_id": str(
                    getattr(account, "utility_account_id", "") or ""
                ),
                "meter_type": meter_type,
                "read_resolution": str(
                    getattr(account, "read_resolution", "") or ""
                ),
                "customer_uuid": customer_uuid,
                "account_name": str(customer.get("accountName", "") or ""),
                "account_type": str(customer.get("type", "") or ""),
                "account_number": self._mask_account_number(
                    customer.get("accountNumber", "")
                ),
                "address": address,
            }
            summaries.append(summary)
            self._account_summaries[account_id] = summary

        return summaries

    def get_account_summary(self, account: Any) -> Dict[str, Any]:
        """Return cached display metadata for an Opower account when available."""
        account_id = str(
            getattr(account, "id", "") or getattr(account, "uuid", "")
        )
        return self._account_summaries.get(account_id, {})

    @staticmethod
    def _account_id(account: Any) -> str:
        """Return the stable identifier used for caches and Home Assistant entities."""
        return str(getattr(account, "id", "") or getattr(account, "uuid", ""))

    def _is_legacy_selected_account(
        self, account: Any, accounts: List[Any]
    ) -> bool:
        """Return whether an account should also populate legacy single-account caches."""
        selected_account_id = str(
            (self.config or {}).get("selected_account_id", "") or ""
        ).strip()
        if selected_account_id:
            return self._account_matches(account, selected_account_id)
        return bool(accounts) and account is accounts[0]

    def _enabled_accounts(self, accounts: List[Any]) -> List[Any]:
        """Filter service addresses selected for simultaneous polling."""
        configured_ids = (self.config or {}).get("enabled_account_ids", [])
        enabled_ids = {
            str(account_id or "").strip()
            for account_id in configured_ids
            if str(account_id or "").strip()
        }
        if enabled_ids:
            return [
                account
                for account in accounts
                if any(self._account_matches(account, item) for item in enabled_ids)
            ]

        selected_account_id = str(
            (self.config or {}).get("selected_account_id", "") or ""
        ).strip()
        if selected_account_id:
            return [
                account
                for account in accounts
                if self._account_matches(account, selected_account_id)
            ]
        return accounts[:1]
    
    async def fetch_reading(self, account: Any = None) -> Optional[Dict[str, Any]]:
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
            
            account = account or self._select_account(accounts)
            
            # Fetch Opower's six-day window so delayed or sparse accounts still
            # resolve to their newest valid reading.
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(hours=144)
            
            reads = await self._opower.async_get_cost_reads(
                account,
                AggregateType.HOUR,
                start_date,
                end_date
            )
            
            if not reads:
                logger.warning("No hourly readings available")
                return None
            
            # Opower can append a NaN placeholder for an interval whose usage is
            # not ready yet. Use the newest finite reading so JSON serialization
            # and Home Assistant ingestion remain valid.
            latest = next(
                (
                    candidate
                    for candidate in reversed(reads)
                    if self._finite_float(candidate.consumption) is not None
                ),
                None,
            )
            if latest is None:
                logger.warning("No finite hourly readings available")
                return None
            
            reading = {
                'account_id': self._account_id(account),
                'account_uuid': str(getattr(account, 'uuid', '') or ''),
                'utility_account_id': str(
                    getattr(account, 'utility_account_id', '') or ''
                ),
                'start_time': latest.start_time.isoformat() if latest.start_time else None,
                'end_time': latest.end_time.isoformat() if latest.end_time else None,
                'value': self._finite_float(latest.consumption),
                'unit': 'kWh',
                'data_type': 'hourly',
                'fetched_at': datetime.now(timezone.utc).isoformat()
            }
            
            import db
            await db.save_meter_reading_for_account_db(reading)
            if self._is_legacy_selected_account(account, accounts):
                self.last_reading = reading
                self.last_reading_time = datetime.now(timezone.utc)
                await db.save_meter_reading_db(reading)
            
            logger.info(f"Meter reading fetched: {reading['value']} {reading['unit']} (hourly data from {latest.end_time})")
            return reading
            
        except Exception as e:
            logger.error(f"Failed to fetch meter reading: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def fetch_forecast(
        self, account: Any = None, forecasts: Optional[List[Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch the current billing period forecast from Con Edison."""
        if not self.is_configured():
            return None
        
        try:
            if not await self._login():
                return None
            
            if forecasts is None:
                forecasts = await self._opower.async_get_forecast()
            if not forecasts:
                return None
            
            accounts = await self._get_accounts()
            account = account or self._select_account(accounts)
            forecast = next(
                (
                    candidate
                    for candidate in forecasts
                    if self._account_matches(
                        candidate.account,
                        self._account_id(account),
                    )
                    or self._account_matches(
                        candidate.account, getattr(account, "uuid", "")
                    )
                ),
                None,
            )
            if forecast is None:
                logger.warning("No forecast available for the selected account")
                return None
            forecast_data = {
                'account_id': self._account_id(account),
                'account_uuid': str(getattr(account, 'uuid', '') or ''),
                'utility_account_id': str(
                    getattr(account, 'utility_account_id', '') or ''
                ),
                'start_date': forecast.start_date.isoformat() if forecast.start_date else None,
                'end_date': forecast.end_date.isoformat() if forecast.end_date else None,
                'usage_to_date': self._finite_float(forecast.usage_to_date),
                'forecasted_usage': self._finite_float(forecast.forecasted_usage),
                'cost_to_date': self._finite_float(forecast.cost_to_date),
                'forecasted_cost': self._finite_float(forecast.forecasted_cost),
                'unit': str(forecast.unit_of_measure) if forecast.unit_of_measure else 'KWH',
                'fetched_at': datetime.now(timezone.utc).isoformat()
            }
            
            import db
            await db.save_meter_forecast_for_account_db(forecast_data)
            if self._is_legacy_selected_account(account, accounts):
                await db.save_meter_forecast_db(forecast_data)
            
            return forecast_data
        except Exception as e:
            logger.error(f"Failed to fetch forecast: {e}")
            return None

    async def fetch_all_account_data(self) -> List[Dict[str, Any]]:
        """Fetch and cache readings and forecasts for every electric account."""
        if not self.is_configured() or not await self._login():
            return []

        summaries = await self.list_accounts(electric_only=True)
        summary_by_id = {item["id"]: item for item in summaries if item.get("id")}
        electric_accounts = [
            account
            for account in await self._get_accounts()
            if self._account_id(account) in summary_by_id
        ]
        accounts = self._enabled_accounts(electric_accounts)
        try:
            forecasts = await self._opower.async_get_forecast()
        except Exception as exc:
            logger.warning("Failed to fetch all-account forecasts: %s", exc)
            forecasts = []

        async def fetch_account(account: Any) -> Dict[str, Any]:
            account_id = self._account_id(account)
            reading, forecast = await asyncio.gather(
                self.fetch_reading(account),
                self.fetch_forecast(account, forecasts),
            )
            return {
                **summary_by_id[account_id],
                "reading": reading,
                "forecast": forecast,
            }

        return list(
            await asyncio.gather(
                *(fetch_account(account) for account in accounts)
            )
        )

    async def get_cached_account_data(self) -> List[Dict[str, Any]]:
        """Return summaries and cached meter data for every electric account."""
        import db

        if not self._account_summaries:
            await self.list_accounts(electric_only=True)
        accounts = [
            account
            for account in await self._get_accounts()
            if str(getattr(account, "meter_type", "") or "") == "ELEC"
        ]
        enabled_accounts = self._enabled_accounts(accounts)
        readings = await db.get_meter_readings_by_account_db()
        forecasts = await db.get_meter_forecasts_by_account_db()
        return [
            {
                **self.get_account_summary(account),
                "reading": readings.get(self._account_id(account)),
                "forecast": forecasts.get(self._account_id(account)),
            }
            for account in enabled_accounts
            if self.get_account_summary(account)
        ]
    
    async def get_cached_forecast(self) -> Optional[Dict[str, Any]]:
        """Get the most recent cached forecast."""
        import db
        cached = await db.get_meter_forecast_db()
        selected_account_id = str(
            (self.config or {}).get('selected_account_id', '') or ''
        ).strip()
        if (
            cached
            and selected_account_id
            and cached.get('account_id') != selected_account_id
        ):
            return None
        return cached
    
    async def fetch_quarter_hour_reads(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Fetch quarter-hour (15-minute) usage data for real-time chart.
        
        Con Edison API limits each request to ~6 days. We fetch in 6-day chunks
        and merge into DB so the chart can show unlimited history over time.
        
        Args:
            hours: Total hours to fetch. Fetched in 144h (6-day) chunks. Default 720 (30 days).
        
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
            
            account = self._select_account(accounts)
            
            # API max ~6 days per request. Fetch in chunks and merge.
            CHUNK_HOURS = 144  # 6 days per API request
            total_hours = max(hours, CHUNK_HOURS)
            all_result: List[Dict[str, Any]] = []
            end_date = datetime.now(timezone.utc)
            
            while total_hours > 0:
                fetch_hours = min(total_hours, CHUNK_HOURS)
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
                        break
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

                all_result.extend(result)
                end_date = start_date
                total_hours -= fetch_hours

            if all_result:
                import db
                await db.save_realtime_readings_db(all_result)
                logger.info(f"Fetched {len(all_result)} readings across chunks, stored for chart")

            return all_result
            
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
            
            account = self._select_account(accounts)
            
            # Check realtime support
            has_realtime = False
            realtime_error = None
            if self._opower.utility.supports_realtime_usage():
                try:
                    meters = await self._opower._async_get_meters(account)
                    has_realtime = len(meters) > 0
                except Exception as e:
                    realtime_error = str(e)
            
            summary = self.get_account_summary(account)
            account_uuid = str(getattr(account, 'uuid', '') or '')
            customer = getattr(account, 'customer', None)
            return {
                'account_id': str(getattr(account, 'id', '') or account_uuid),
                'account_uuid': account_uuid,
                'utility_account_id': str(
                    getattr(account, 'utility_account_id', '') or ''
                ),
                'meter_type': str(getattr(account, 'meter_type', '') or '') or None,
                'read_resolution': str(
                    getattr(account, 'read_resolution', '') or ''
                ) or None,
                'has_realtime_access': has_realtime,
                'realtime_error': realtime_error,
                'customer_uuid': (
                    str(getattr(customer, 'uuid', '') or '') or None
                ),
                'account_name': summary.get('account_name', ''),
                'account_type': summary.get('account_type', ''),
                'account_number': summary.get('account_number', ''),
                'address': summary.get('address', ''),
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
        selected_account_id = str(
            (self.config or {}).get('selected_account_id', '') or ''
        ).strip()
        if (
            cached
            and selected_account_id
            and cached.get('account_id') != selected_account_id
        ):
            return None
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
                        # Poll every electric account and cache each independently.
                        await self.fetch_all_account_data()
                        # 6-day data for History chart (API max); chart shows last 24h
                        await self.fetch_quarter_hour_reads(144)
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
