# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-03-17

### Added
- Web shell admin UI and Tkinter admin UI.
- LAN questionnaire service with QR entry.
- Offline questionnaire export and vote import workflow.
- SQL query workspace for ballot processing.
- SQL-based live validation rules.
- Runtime kernel switch setting (`web` / `tkinter`).

### Changed
- Default startup now follows saved runtime kernel preference.
- SQL parsing/validation robustness improved for complex read-only SELECT syntax.

### Security
- Encrypted `.vote` storage with admin-key based decryption workflow.
