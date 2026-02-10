# GitHub Workflows Documentation

This document describes the comprehensive CI/CD workflows implemented for the fast-k8s project.

## Overview

The project uses GitHub Actions for continuous integration, testing, Docker builds, and quality checks. All workflows are designed to:
- Provide fast feedback through dependency caching
- Report results directly in pull requests
- Maintain code quality and security standards
- Support multi-platform deployments

## Workflows

### 1. Tests Workflow (`tests.yml`)

**Trigger:** Push to `main`/`develop` branches, and all pull requests to `main`

**Purpose:** Automated testing and code coverage reporting

**Features:**
- **Matrix Testing:** Runs on Python 3.12 and 3.13
- **Dependency Caching:** Caches pip and uv packages for faster builds
- **Linting:** Uses ruff for code quality checks
- **Coverage Reporting:**
  - Generates XML, HTML, and terminal coverage reports
  - Uploads to Codecov for tracking
  - Comments coverage metrics directly on PRs
- **Test Artifacts:** Preserves test results and HTML coverage reports
- **Test Summary:** Provides detailed test summaries in GitHub UI

**Key Improvements:**
- Added `cache: 'pip'` to Python setup for faster dependency installation
- Added uv package caching with proper cache key based on `pyproject.toml` and `uv.lock`
- Generate HTML coverage reports as artifacts for detailed inspection
- Use `py-cov-action/python-coverage-comment-action@v3` for PR coverage comments
- Use `test-summary/action@v2` for test result summaries
- Extended permissions to allow PR comments and check writes

**Sample Output:**
```
✅ Python 3.12 Tests: 19 passed
✅ Python 3.13 Tests: 19 passed
📊 Coverage: 94% (Minimum: 90%)
```

### 2. Docker Build and Publish (`docker-publish.yml`)

**Trigger:**
- Push to `main` branch (builds and pushes)
- Pull requests to `main` (builds only, doesn't push)

**Purpose:** Build and publish multi-platform Docker images

**Features:**
- **Multi-Platform Builds:** Supports linux/amd64 and linux/arm64
- **QEMU Support:** Cross-platform builds using QEMU
- **Build Caching:** GitHub Actions cache for faster subsequent builds
- **Smart Tagging:**
  - Branch name (e.g., `main`)
  - Git SHA (e.g., `main-abc1234`)
  - Latest tag on main branch
  - PR reference for pull requests
- **PR Validation:** Builds Docker images on PRs without pushing (validates Dockerfile)
- **Summary Reports:** Provides build summary in GitHub step summary

**Key Improvements:**
- Added QEMU and Docker Buildx setup for multi-platform builds
- Added build caching with `cache-from` and `cache-to` directives
- Build on PRs to validate Dockerfile changes early
- Enhanced tagging strategy with PR tags
- Added detailed build summary with tags and platforms
- Conditional login (only on non-PR events)

**Sample Output:**
```
### Docker Build Summary 🐋

**Image Tags:**
ghcr.io/memestageceo/fast-k8s:main
ghcr.io/memestageceo/fast-k8s:main-abc1234
ghcr.io/memestageceo/fast-k8s:latest

**Platforms:** linux/amd64, linux/arm64
```

### 3. PR Quality Checks (`pr-quality.yml`)

**Trigger:** Pull requests to `main`

**Purpose:** Automated code quality analysis and security scanning

**Features:**
- **PR Information Summary:**
  - PR title, author, and branch information
  - File changes statistics
  - Automatically posted as a comment
  
- **Code Quality Analysis:**
  - Runs ruff with GitHub annotations
  - Inline code suggestions in PR diff
  - Code complexity metrics in step summary
  
- **Security Scanning:**
  - Trivy vulnerability scanner for filesystem
  - SARIF format results uploaded to GitHub Security
  - Identifies vulnerabilities in dependencies and code

**Key Benefits:**
- Provides immediate feedback on PR quality
- Catches security issues before merge
- Educates contributors with inline suggestions
- Maintains security posture with automated scanning

**Sample PR Comment:**
```
### Pull Request Quality Report 📊

**PR #123:** Add new feature
**Author:** @username
**Base:** `main` ← **Head:** `feature-branch`

**Changed Files:** 5
**Additions:** +150 | **Deletions:** -20

---

✅ Tests are running - check the workflow tabs for detailed results.
```

### 4. Test Reports (`test-reports.yml`)

**Trigger:**
- Pull requests to `main`
- Completion of Tests workflow

**Purpose:** Detailed test reporting and PR feedback

**Features:**
- **Test Result Publishing:**
  - Downloads test artifacts from Tests workflow
  - Publishes JUnit test reports as GitHub checks
  - Provides detailed test breakdown
  
- **PR Test Summary:**
  - Automatically comments on PRs with test results
  - Links to detailed reports in artifacts
  - Shows pass/fail status at a glance

**Key Benefits:**
- Centralizes test reporting
- Makes test results easily accessible in PR UI
- Preserves historical test data as artifacts
- Reduces need to check workflow logs

## Workflow Dependencies

```
Tests Workflow
    ↓
Test Reports Workflow → PR Comment
    
PR Creation
    ↓
PR Quality Checks → Security Scan + Code Quality
    ↓
Docker Build (validation only)
```

## Caching Strategy

All workflows use GitHub Actions cache to improve performance:

1. **Python Dependencies:**
   - `cache: 'pip'` in setup-python action
   - Automatic caching based on requirements

2. **UV Packages:**
   - Cached in `~/.cache/uv`
   - Cache key: OS + Python version + hash of `pyproject.toml` and `uv.lock`
   - Restore keys for partial cache hits

3. **Docker Builds:**
   - GitHub Actions cache type (`type=gha`)
   - Mode: `max` for maximum caching
   - Significantly faster rebuilds

## Status Badges

Add these badges to your README to show workflow status:

```markdown
[![Tests](https://github.com/memestageceo/fast-k8s/actions/workflows/tests.yml/badge.svg)](https://github.com/memestageceo/fast-k8s/actions/workflows/tests.yml)
[![Docker](https://github.com/memestageceo/fast-k8s/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/memestageceo/fast-k8s/actions/workflows/docker-publish.yml)
[![codecov](https://codecov.io/gh/memestageceo/fast-k8s/branch/main/graph/badge.svg)](https://codecov.io/gh/memestageceo/fast-k8s)
```

## Required Secrets

For full functionality, configure these secrets in your repository:

- `CODECOV_TOKEN`: Token for uploading coverage to Codecov (optional, but recommended)
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

## Permissions

Workflows use minimal required permissions:

- **Tests:**
  - `contents: read` - Checkout code
  - `pull-requests: write` - Comment on PRs
  - `checks: write` - Create check runs
  
- **Docker:**
  - `contents: read` - Checkout code
  - `packages: write` - Push to GHCR
  
- **PR Quality:**
  - `contents: read` - Checkout code
  - `pull-requests: write` - Comment on PRs
  - `checks: write` - Upload security scans

## Best Practices Implemented

1. **Security:**
   - Minimal permissions (principle of least privilege)
   - Action versions pinned to major versions (e.g., @v4, @v5)
   - Security scanning with Trivy
   - Non-root Docker user

2. **Performance:**
   - Comprehensive caching strategy
   - Parallel test execution across Python versions
   - Incremental Docker builds

3. **Developer Experience:**
   - Rich PR feedback (comments, summaries, checks)
   - Inline code suggestions
   - Clear failure messages
   - Accessible test reports

4. **Quality:**
   - Automated linting
   - Code coverage tracking with thresholds
   - Test result preservation
   - Multi-platform Docker builds

## Future Enhancements

Potential improvements for consideration:

1. **Enhanced Test Reporting:**
   - Flaky test detection
   - Test timing analysis
   - Historical trend tracking

2. **Performance Monitoring:**
   - Build time tracking
   - Docker image size monitoring
   - Test execution time trends

3. **Advanced Security:**
   - Dependency update automation (Dependabot)
   - SAST (Static Application Security Testing)
   - License compliance checking

4. **Deployment:**
   - Automatic deployment to staging on PR
   - Production deployment on merge to main
   - Blue-green deployment support

## Troubleshooting

### Cache Issues

If caching isn't working properly:
1. Check cache key in workflow logs
2. Verify `pyproject.toml` and `uv.lock` are committed
3. Try clearing cache from GitHub UI (Settings → Actions → Caches)

### Coverage Comments Not Appearing

1. Ensure `CODECOV_TOKEN` is set (if using private repo)
2. Check PR permissions allow writing comments
3. Verify coverage reports are being generated in test run

### Docker Build Failures

1. Check Dockerfile syntax
2. Verify base image is accessible
3. Review build logs for specific error messages
4. Test build locally with same platforms

### Security Scan Issues

1. Check Trivy is scanning correct paths
2. Review SARIF output in workflow artifacts
3. Verify GitHub Security tab is enabled
4. Check for known false positives

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Buildx Documentation](https://docs.docker.com/buildx/working-with-buildx/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Trivy Security Scanner](https://trivy.dev/)
