# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2026-03-17

### Fixed
- 修复 Web 内核“离线问卷导出”未注入名单校验成员数据的问题。
- 修复名单校验问卷在离线 HTML 中误报“不在允许名单中”的问题。

### Changed
- 统一 Tk/Web 两套“离线导出”逻辑，改为同一服务层数据组装入口。

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
