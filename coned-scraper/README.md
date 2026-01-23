# ConEd Scraper - Home Assistant Addon

A Home Assistant addon for automating ConEd account scraping with TOTP authentication. Monitors account balance, bills, and payments, publishing changes to Home Assistant via MQTT.

## Features

- **Automated Scraping**: Scheduled scraping of ConEd account data
- **TOTP Support**: Generates TOTP codes matching Google Authenticator
- **Headless Browser Automation**: Uses Playwright to automate login
- **Secure Storage**: Encrypted credential storage
- **Home Assistant Integration**: MQTT sensors for account balance, bills, and payments
- **Change Detection**: Automatically detects and publishes changes to Home Assistant

## Home Assistant Sensors

The addon publishes the following MQTT sensors:

- **Account Balance** (`coned/account_balance`): Current account balance with change detection
- **Most Recent Bill** (`coned/most_recent_bill`): Amount of the most recent bill
- **Previous Bill** (`coned/previous_bill`): Amount of the previous bill
- **Last Payment** (`coned/last_payment`): Amount of the most recent payment

All sensors include attributes with timestamps, dates, and raw values. Sensors are only updated when values change, making them perfect for automations.

## Installation

### Add Repository to Home Assistant

1. In Home Assistant, go to **Supervisor** → **Add-on Store**
2. Click the three dots (⋮) in the top right corner
3. Select **Repositories**
4. Add repository URL: `https://github.com/zodyking/coned-scraper`
5. Click **Add**
6. The "ConEd Scraper" addon should now appear in the addon store
7. Click **Install** and configure your credentials

### Manual Installation

1. Copy the `coned-scraper` directory to your Home Assistant `addons` directory (typically `/usr/share/hassio/addons/` or `/config/addons/`)
2. In Home Assistant, go to **Supervisor** → **Add-on Store** → **Local add-ons**
3. Find "ConEd Scraper" and click **Install**
4. Configure the addon with your ConEd credentials and MQTT settings
5. Start the addon

## Configuration

Configure the addon through the Home Assistant UI:

- `username`: Your ConEd account email/username
- `password`: Your ConEd account password
- `totp_secret`: Base32-encoded TOTP secret (same as Google Authenticator)
- `scrape_frequency`: Scraping frequency in seconds (default: 3600 = 1 hour)
- `mqtt_host`: MQTT broker hostname (default: "core-mosquitto" for Home Assistant)
- `mqtt_port`: MQTT broker port (default: 1883)
- `mqtt_user`: MQTT username (optional)
- `mqtt_password`: MQTT password (optional)
- `mqtt_topic_prefix`: MQTT topic prefix (default: "coned")

## Home Assistant Configuration

See `home-assistant-config.yaml` for complete sensor configuration examples. Add to your `configuration.yaml`:

```yaml
mqtt:
  sensor:
    - name: "ConEd Account Balance"
      state_topic: "coned/account_balance/state"
      json_attributes_topic: "coned/account_balance/attributes"
      availability_topic: "coned/account_balance/availability"
      unit_of_measurement: "$"
      device_class: "monetary"
      state_class: "measurement"
      unique_id: "coned_account_balance"
      
    - name: "ConEd Most Recent Bill"
      state_topic: "coned/most_recent_bill/state"
      json_attributes_topic: "coned/most_recent_bill/attributes"
      availability_topic: "coned/most_recent_bill/availability"
      unit_of_measurement: "$"
      device_class: "monetary"
      state_class: "measurement"
      unique_id: "coned_most_recent_bill"
      
    - name: "ConEd Previous Bill"
      state_topic: "coned/previous_bill/state"
      json_attributes_topic: "coned/previous_bill/attributes"
      availability_topic: "coned/previous_bill/availability"
      unit_of_measurement: "$"
      device_class: "monetary"
      state_class: "measurement"
      unique_id: "coned_previous_bill"
      
    - name: "ConEd Last Payment"
      state_topic: "coned/last_payment/state"
      json_attributes_topic: "coned/last_payment/attributes"
      availability_topic: "coned/last_payment/availability"
      unit_of_measurement: "$"
      device_class: "monetary"
      state_class: "measurement"
      unique_id: "coned_last_payment"
```

## Security Notes

- Credentials are encrypted at rest using Fernet encryption
- Encryption key is auto-generated and stored in `data/.key`
- Never commit credentials or encryption keys to version control
- The addon runs in a containerized environment for isolation

## Troubleshooting

- **TOTP not generating**: Ensure the TOTP secret is valid base32 format
- **Scraping fails**: Check logs in Home Assistant Supervisor
- **MQTT not connecting**: Verify MQTT broker settings and that Mosquitto addon is running
- **Browser automation fails**: Ensure Playwright browsers are installed (handled automatically in Docker)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

