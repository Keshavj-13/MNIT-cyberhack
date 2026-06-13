# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial repository governance with `.gitignore` and `CHANGELOG.md`.
- Project structure for Banking Threat Detection System.
- Basic `README.md` with setup instructions.
- FastAPI backend stub.
- React/Vite frontend.

### Fixed
- Backend initialization failure: Implemented missing abstract methods in `RiskProvider` implementations (`Transaction`, `Network`, `Device`, `Context`, `Behavior`).
- Port conflict: Identified and resolved hanging backend processes.
