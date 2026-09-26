# Changelog

## 1.3.95

### Added
- Daily Usage now opens on a month calendar with each day's total kWh and estimated dollar amount
- Clicking a calendar day opens the existing 15-minute usage chart, with a Calendar control to return

### Changed
- Day-to-day chart arrows are removed; month paging on the calendar is how you move between days
- All TTS announcements now call Home Assistant `tts.speak` with cache enabled, targeting the TTS device when available

### Fixed
- TTS no longer falls back to deprecated `tts.*_say` services

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
