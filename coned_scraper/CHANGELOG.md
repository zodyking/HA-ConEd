# Changelog

## 1.3.91

### Fixed
- Late payment detection no longer flags recent payments as late fees
- Late fees capped at legal 1.5% per month maximum
- PDF parsing improvements for due date, kWh, and cost fields
- Bill details no longer wiped on failed PDF re-parse
- Cost/projected bill fallbacks from meter forecast when PDF data is missing

## 1.3.90

### Fixed
- Initial release of late-fee and PDF parsing fixes (version bump for HA update detection)
