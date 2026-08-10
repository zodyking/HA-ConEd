# Changelog

## Unreleased

### Added
- Electric account discovery and selection for Con Edison logins with multiple service addresses

### Fixed
- Opower readings and forecasts now use the selected account instead of always using the first result
- Browser scraping switches to the selected Con Edison service address
- Meter caches are cleared when the selected account changes to avoid mixing usage data

## 1.3.94

### Fixed
- Year-aware PDF auto-download for duplicate month ranges (e.g. MAY - JUN 2025 vs 2026)
- Bill history scrape deduplicates duplicate DOM rows

### Changed
- Version bump for Home Assistant add-on store update detection

## 1.3.93

### Fixed
- PDF auto-download now distinguishes bills with the same month range across different years (e.g. MAY - JUN 2025 vs 2026)
- Bill history scrape deduplicates duplicate DOM rows so ledger entries are not doubled

## 1.3.92

### Changed
- Documented Home Assistant add-on version source (`config.yaml`) and store refresh steps

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
