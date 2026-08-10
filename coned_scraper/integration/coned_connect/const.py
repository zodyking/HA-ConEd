"""Constants for the Con Edison integration."""
from datetime import timedelta

DOMAIN = "coned_connect"
DEFAULT_NAME = "ConEd Connect"
DEFAULT_URL = "http://9a4bbad0-coned-scraper:8000"

CONF_ADDON_URL = "addon_url"

SCAN_INTERVAL = timedelta(minutes=5)

SENSOR_ACCOUNT_BALANCE = "account_balance"
SENSOR_LATEST_BILL = "latest_bill"
SENSOR_PREVIOUS_BILL = "previous_bill"
SENSOR_LAST_PAYMENT = "last_payment"
SENSOR_BILL_PDF_URL = "bill_pdf_url"
SENSOR_DUE_DATE = "due_date"
SENSOR_KWH_COST = "kwh_cost"
SENSOR_LAST_BILL_KWH = "last_bill_kwh"
SENSOR_CURRENT_USAGE_COST = "current_usage_cost"
SENSOR_BILLING_START_DATE = "billing_start_date"
SENSOR_BILLING_END_DATE = "billing_end_date"
SENSOR_CURRENT_CYCLE_USAGE = "current_cycle_usage"
SENSOR_FORECASTED_USAGE = "forecasted_usage"

SENSORS = {
    SENSOR_ACCOUNT_BALANCE: {
        "name": "Account Balance",
        "unit": "USD",
        "device_class": "monetary",
        "icon": "mdi:cash",
    },
    SENSOR_LATEST_BILL: {
        "name": "Latest Bill",
        "unit": "USD",
        "device_class": "monetary",
        "icon": "mdi:file-document",
    },
    SENSOR_PREVIOUS_BILL: {
        "name": "Previous Bill",
        "unit": "USD",
        "device_class": "monetary",
        "icon": "mdi:file-document-outline",
    },
    SENSOR_LAST_PAYMENT: {
        "name": "Last Payment",
        "unit": "USD",
        "device_class": "monetary",
        "icon": "mdi:credit-card-check",
    },
    SENSOR_BILL_PDF_URL: {
        "name": "Bill PDF URL",
        "unit": None,
        "device_class": None,
        "icon": "mdi:file-pdf-box",
    },
    SENSOR_DUE_DATE: {
        "name": "Due Date",
        "unit": None,
        "device_class": None,
        "icon": "mdi:calendar-clock",
    },
    SENSOR_KWH_COST: {
        "name": "kWh Cost",
        "unit": "$/kWh",
        "device_class": None,
        "icon": "mdi:lightning-bolt",
    },
    SENSOR_LAST_BILL_KWH: {
        "name": "Last Bill kWh",
        "unit": "kWh",
        "device_class": "energy",
        "icon": "mdi:flash",
    },
    SENSOR_CURRENT_USAGE_COST: {
        "name": "Current Usage Cost",
        "unit": "USD",
        "device_class": "monetary",
        "icon": "mdi:currency-usd",
    },
    SENSOR_BILLING_START_DATE: {
        "name": "Billing Start Date",
        "unit": None,
        "device_class": None,
        "icon": "mdi:calendar-start",
    },
    SENSOR_BILLING_END_DATE: {
        "name": "Billing End Date",
        "unit": None,
        "device_class": None,
        "icon": "mdi:calendar-end",
    },
    SENSOR_CURRENT_CYCLE_USAGE: {
        "name": "Current Cycle Usage",
        "unit": "kWh",
        "device_class": "energy",
        "icon": "mdi:flash-outline",
    },
    SENSOR_FORECASTED_USAGE: {
        "name": "Forecasted Usage",
        "unit": "kWh",
        "device_class": "energy",
        "icon": "mdi:chart-line",
    },
}


# Sensors created once per electric Opower account. Their unique IDs include a
# privacy-preserving hash of the stable account ID, while the local device name
# uses the account label/address returned by the add-on.
ACCOUNT_SENSORS = {
    "latest_hourly_usage": {
        "name": "Latest Hourly Usage",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "measurement",
        "icon": "mdi:flash",
    },
    "current_usage_cost": {
        "name": "Latest Hourly Cost",
        "unit": "USD",
        "device_class": "monetary",
        "icon": "mdi:currency-usd",
        "source": "cost",
    },
    "current_cycle_usage": {
        "name": "Current Cycle Usage",
        "unit": "kWh",
        "device_class": "energy",
        "state_class": "total",
        "icon": "mdi:flash-outline",
    },
    "forecasted_usage": {
        "name": "Forecasted Usage",
        "unit": "kWh",
        "device_class": "energy",
        "icon": "mdi:chart-line",
    },
    "usage_to_date_cost": {
        "name": "Current Cycle Cost",
        "unit": "USD",
        "device_class": "monetary",
        "icon": "mdi:cash-clock",
    },
    "projected_cost": {
        "name": "Projected Cost",
        "unit": "USD",
        "device_class": "monetary",
        "icon": "mdi:cash-fast",
    },
    "billing_start_date": {
        "name": "Billing Start Date",
        "unit": None,
        "device_class": None,
        "icon": "mdi:calendar-start",
    },
    "billing_end_date": {
        "name": "Billing End Date",
        "unit": None,
        "device_class": None,
        "icon": "mdi:calendar-end",
    },
    "kwh_cost": {
        "name": "kWh Cost",
        "unit": "$/kWh",
        "device_class": None,
        "icon": "mdi:lightning-bolt",
    },
}
