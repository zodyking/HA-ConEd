# Changelog

## 1.3.98

### Fixed
- Payee splits use the billing cycle’s new charges. Con Edison’s rolled-over balance stays with the payee who underpaid, instead of being divided by responsibility percent
- Rollover view lists why a portion is higher, for example “$50 from 10/15/26 underpayment”

## 1.3.97

### Added
- Ledger and History open from the last successful data, then refresh in the background with an updating status
- Payees & Payments can clear the rollover balance from a chosen month, and undo that clear
- Usage calendar prices each day with that billing period’s actual all-in rate

### Changed
- Usage calendar fits a phone: compact day cells, larger month controls, and usage and cost in a panel under the grid

### Fixed
- Rollover keeps overpayment credits, so the next bill is reduced instead of charging the full portion again
- Ledger, bill history, and scraped data no longer fail on mixed timezone dates, null kWh, non-object charge JSON, or an unbounded scrape load
- Meter fetches time out and no longer pile up; PDF parsing no longer blocks the API; a cancelled scrape still closes the browser

## 1.3.96

### Added
- Daily Usage calendar shows today (even while data is still arriving) and current billing-period start/end markers
- Clear “tap a day / View chart” affordance so the 15-minute chart is discoverable

### Changed
- Calendar layout restyled to match the add-on theme (period badge, legend, today ring)
- TTS now uses the same Home-Delivery Supervisor path: `tts.speak` with the TTS engine `entity_id`, then a legacy service fallback

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
