# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-10

### Added
- Comprehensive error handling for all endpoints
- Structured logging with configurable levels
- Complete type hints throughout the codebase
- Detailed docstrings for all functions and endpoints
- Input validation for environment variables (READY_AFTER)
- CORS middleware for cross-origin requests
- Application lifespan management with startup/shutdown logging
- Comprehensive test suite with pytest
  - Unit tests for all endpoints
  - Thread safety tests for counter
  - Error handling tests
  - Environment variable validation tests
  - CORS configuration tests
  - OpenAPI documentation tests
- GitHub Actions workflow for automated testing
- Development dependencies in pyproject.toml (pytest, ruff, coverage)
- `.dockerignore` file for optimized Docker builds
- This CHANGELOG file

### Changed
- Updated Dockerfile to use non-root user (appuser) for better security
- Added proper resource limits in Kubernetes deployment
- Enhanced health probe configurations with timeouts and thresholds
- Added security context to Kubernetes deployment
- Improved thread safety in `/whoami` endpoint (now uses lock for counter read)
- Enhanced FastAPI app configuration with better metadata
- Updated pyproject.toml with better project description and Python version requirement
- Improved dependency installation in Dockerfile with `--no-cache-dir` flags

### Fixed
- Thread safety issue in `/whoami` endpoint where counter was accessed without lock
- Missing error handling in home page and whoami endpoints
- Potential issues with invalid READY_AFTER environment variable values
- Missing ready status in `/whoami` endpoint response

### Security
- Implemented non-root user in Docker container (UID 1000)
- Added security context in Kubernetes deployment with privilege escalation prevention
- Added capability dropping (ALL capabilities) in container security context
- Proper file ownership in Docker image
- Added CORS middleware (should be configured for production)
- Input validation for environment variables

## [0.1.0] - Initial Release

### Added
- Initial FastAPI application
- Basic health probes (liveness and readiness)
- Home page with dashboard
- Whoami endpoint
- Docker and Kubernetes support
- Comprehensive README documentation
