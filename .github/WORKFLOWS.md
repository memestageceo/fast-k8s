# GitHub Workflows Documentation

This document provides detailed documentation for all GitHub Actions workflows in this repository, including concepts, examples, and best practices.

## Table of Contents

- [Overview](#overview)
- [Workflow Architecture](#workflow-architecture)
- [Individual Workflows](#individual-workflows)
  - [Tests Workflow](#tests-workflow)
  - [Docker Publish Workflow](#docker-publish-workflow)
  - [PR Quality Checks Workflow](#pr-quality-checks-workflow)
  - [Test Reports Workflow](#test-reports-workflow)
- [Key Concepts](#key-concepts)
- [Troubleshooting](#troubleshooting)

## Overview

This repository uses GitHub Actions for continuous integration and deployment. The workflows are organized into four main components:

1. **Tests** - Run unit tests and generate coverage reports
2. **Docker Publish** - Build and publish Docker images
3. **PR Quality Checks** - Automated code quality and security scanning
4. **Test Reports** - Aggregate and report test results

## Workflow Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Pull Request Created                      │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌──────────────────┐
│  Tests        │      │  PR Quality      │
│  Workflow     │      │  Workflow        │
├───────────────┤      ├──────────────────┤
│ • Lint code   │      │ • Run ruff       │
│ • Run tests   │      │ • Security scan  │
│ • Coverage    │      │ • PR summary     │
└───────┬───────┘      └──────────────────┘
        │
        ▼
┌──────────────────┐
│  Test Reports    │
│  Workflow        │
├──────────────────┤
│ • Aggregate      │
│ • Comment on PR  │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  Docker Build    │
│  (validation)    │
├──────────────────┤
│ • Build image    │
│ • No push        │
└──────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Push to Main Branch                       │
└───────────────────┬─────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────┐      ┌──────────────────┐
│  Tests        │      │  Docker Publish  │
│  Workflow     │      │  Workflow        │
├───────────────┤      ├──────────────────┤
│ • Full suite  │      │ • Build image    │
│ • Coverage    │      │ • Push to GHCR   │
└───────────────┘      │ • Tag: latest    │
                       └──────────────────┘
```

---

## Individual Workflows

### Tests Workflow

**File:** `.github/workflows/tests.yml`

#### Purpose
Runs automated tests across multiple Python versions to ensure code quality and compatibility.

#### Triggers
- **Push** to `main` or `develop` branches
- **Pull requests** targeting `main`

#### Key Features

**Matrix Strategy**
Tests run in parallel across multiple Python versions:
```yaml
strategy:
  matrix:
    python-version: ["3.12", "3.13"]
```

**Benefits:**
- Faster feedback (parallel execution)
- Ensures compatibility across Python versions
- Catches version-specific bugs early

**Dependency Caching**
Two-layer caching strategy for faster builds:
```yaml
# pip cache (built-in)
cache: 'pip'

# uv package cache (custom)
uses: actions/cache@v4
with:
  path: ~/.cache/uv
  key: ${{ runner.os }}-uv-${{ matrix.python-version }}-${{ hashFiles('pyproject.toml', 'uv.lock') }}
```

**Cache invalidation** happens when:
- Python version changes
- `pyproject.toml` changes
- `uv.lock` changes

**Coverage Generation**
Generates comprehensive coverage reports:
```yaml
pytest test_main.py \
  --cov=. \
  --cov-report=xml \
  --cov-report=html \
  --junitxml=test-results-${{ matrix.python-version }}.xml
```

**Coverage Reporting**
- **Codecov**: Uploads coverage to external service (Python 3.12 only)
- **PR Comments**: Automatically comments coverage stats on PRs
- **Thresholds**:
  - Green: ≥90%
  - Orange: ≥80%
  - Red: <80%

#### Example Workflow Run

```
Python 3.12                          Python 3.13
├── Checkout                         ├── Checkout
├── Setup Python                     ├── Setup Python
├── Restore caches                   ├── Restore caches
├── Install dependencies             ├── Install dependencies
├── Lint with ruff                   ├── Lint with ruff
│   └── ✓ No issues                  │   └── ✓ No issues
├── Run pytest                       ├── Run pytest
│   ├── 15 tests passed              │   ├── 15 tests passed
│   └── Coverage: 92%                │   └── Coverage: 92%
├── Upload artifacts                 ├── Upload artifacts
└── Post coverage (PR only)          └── Test summary
```

#### Artifacts Generated
- `test-results-3.12.xml` - JUnit test results (Python 3.12)
- `test-results-3.13.xml` - JUnit test results (Python 3.13)
- `coverage-3.12/` - Coverage reports (Python 3.12)
- `coverage-3.13/` - Coverage reports (Python 3.13)

---

### Docker Publish Workflow

**File:** `.github/workflows/docker-publish.yml`

#### Purpose
Builds multi-architecture Docker images and publishes them to GitHub Container Registry (GHCR).

#### Triggers
- **Push** to `main` - Builds and pushes
- **Pull requests** to `main` - Builds only (validation)

#### Key Features

**Multi-Platform Builds**
Builds for multiple architectures in a single workflow:
```yaml
platforms: linux/amd64,linux/arm64
```

**Supported platforms:**
- `linux/amd64` - Standard x86_64 servers
- `linux/arm64` - ARM-based systems (Apple Silicon, AWS Graviton, Raspberry Pi)

**QEMU Setup**
Enables cross-platform compilation:
```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3
```

**Docker Buildx**
Advanced build features:
```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3
```

**Benefits:**
- Multi-platform builds
- Build caching
- Parallel builds
- Advanced BuildKit features

**Conditional Authentication**
Only logs in to registry on push events:
```yaml
- name: Log in to GitHub Container Registry
  if: github.event_name == 'push'
  uses: docker/login-action@v3
```

**Automatic Tagging**
Smart tagging based on event type:
```yaml
tags: |
  type=ref,event=branch          # main, develop
  type=ref,event=pr              # pr-123
  type=sha                       # sha-abc1234
  type=raw,value=latest,enable={{is_default_branch}}  # latest (main only)
```

**Example tags generated:**
- Push to `main`: `main`, `sha-abc1234`, `latest`
- Push to `develop`: `develop`, `sha-def5678`
- Pull request #42: `pr-42`, `sha-ghi9012`

**GitHub Actions Cache**
Speeds up subsequent builds:
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

**Cache modes:**
- `min` - Only final image layers
- `max` - All intermediate layers (faster rebuilds)

#### Example Workflow Runs

**Pull Request (Validation)**
```
Build Docker Image
├── Checkout repository
├── Set up QEMU
├── Set up Docker Buildx
├── Extract metadata
│   └── Tags: pr-42, sha-abc1234
├── Build Docker image
│   ├── Platform: linux/amd64
│   ├── Platform: linux/arm64
│   └── Push: false (validation only)
└── Docker image summary
    └── ✓ Built successfully (not pushed)
```

**Push to Main (Production)**
```
Build Docker Image
├── Checkout repository
├── Set up QEMU
├── Set up Docker Buildx
├── Log in to GHCR
│   └── ✓ Authenticated
├── Extract metadata
│   └── Tags: main, sha-abc1234, latest
├── Build and push Docker image
│   ├── Platform: linux/amd64
│   │   └── ✓ Pushed to ghcr.io/owner/repo:main
│   ├── Platform: linux/arm64
│   │   └── ✓ Pushed to ghcr.io/owner/repo:main
│   └── ✓ Manifest created
└── Docker image summary
    └── Published: 3 tags
```

#### Using Published Images

```bash
# Pull latest version
docker pull ghcr.io/memestageceo/fast-k8s:latest

# Pull specific commit
docker pull ghcr.io/memestageceo/fast-k8s:sha-abc1234

# Pull specific branch
docker pull ghcr.io/memestageceo/fast-k8s:main

# Pull PR build (if you need to test)
docker pull ghcr.io/memestageceo/fast-k8s:pr-42
```

**Multi-arch usage:**
```bash
# Docker automatically pulls the right architecture
docker run ghcr.io/memestageceo/fast-k8s:latest

# Force specific platform
docker run --platform linux/amd64 ghcr.io/memestageceo/fast-k8s:latest
docker run --platform linux/arm64 ghcr.io/memestageceo/fast-k8s:latest
```

---

### PR Quality Checks Workflow

**File:** `.github/workflows/pr-quality.yml`

#### Purpose
Automated code quality analysis and security scanning for pull requests.

#### Triggers
- Pull requests: `opened`, `reopened`, `ready_for_review`
- Target branch: `main`

#### Jobs

##### 1. PR Information
Generates a summary comment with PR metadata:

```markdown
### Pull Request Quality Report 📊

**PR #42:** Add new feature
**Author:** @username
**Base:** `main` ← **Head:** `feature-branch`

**Changed Files:** 5
**Additions:** +127 | **Deletions:** -34

---

✅ Tests are running - check the workflow tabs for detailed results.
```

**GitHub Script Example:**
```javascript
const pr = context.payload.pull_request;
await github.rest.issues.createComment({
  owner: context.repo.owner,
  repo: context.repo.repo,
  issue_number: pr.number,
  body: summary
});
```

##### 2. Code Quality Analysis
Runs `ruff` linter with GitHub annotations:

```yaml
- name: Run ruff with annotations
  run: ruff check main.py test_main.py --output-format=github
```

**Output format `github`:**
- Creates annotations on changed lines
- Shows up in PR "Files changed" tab
- Fails the check if issues found

**Example annotation:**
```
main.py:45:1: E501 Line too long (120 > 88 characters)
main.py:67:5: F841 Local variable 'unused_var' is assigned but never used
```

##### 3. Security Scan
Uses Trivy to scan for vulnerabilities:

**Scan configuration:**
```yaml
scan-type: 'fs'          # Filesystem scan
scan-ref: '.'            # Current directory
format: 'sarif'          # Security Alert Report Interchange Format
exit-code: '0'           # Don't fail on findings
```

**What Trivy scans:**
- Python dependencies (CVEs)
- Dockerfile vulnerabilities
- Misconfigurations
- Secrets in code
- License compliance

**Results uploaded to:**
- GitHub Security tab
- Code scanning alerts
- Dependabot integration

#### Example Security Finding

```
┌────────────────────────────────────────────────────────┐
│ Severity: HIGH                                         │
│ Package:  requests                                     │
│ Version:  2.28.0                                       │
│ CVE:      CVE-2023-32681                              │
│ Fixed:    2.31.0                                       │
│ Title:    HTTP Request Smuggling in requests          │
└────────────────────────────────────────────────────────┘
```

---

### Test Reports Workflow

**File:** `.github/workflows/test-reports.yml`

#### Purpose
Aggregates test results and posts summaries on pull requests.

#### Triggers
```yaml
on:
  workflow_run:
    workflows: ["Tests"]
    types: [completed]
```

**Trigger mechanism:**
1. Tests workflow completes
2. This workflow automatically starts
3. Downloads artifacts from Tests workflow
4. Generates reports

**Why separate workflow?**
- Security: `workflow_run` has elevated permissions
- Can access artifacts from fork PRs safely
- Centralized reporting logic

#### Workflow Steps

**1. Download Test Artifacts**
```yaml
- name: Download test artifacts
  uses: actions/download-artifact@v4
  with:
    pattern: test-results-*
    run-id: ${{ github.event.workflow_run.id }}
    merge-multiple: true
```

Downloads all test results from the triggering workflow:
- `test-results-3.12.xml`
- `test-results-3.13.xml`

**2. Publish Test Report**
Creates interactive test report:
```yaml
- name: Publish Test Report
  uses: dorny/test-reporter@v1
  with:
    name: Test Results
    path: 'test-results-*.xml'
    reporter: java-junit
    fail-on-error: false
```

**Generated report includes:**
- Total tests run
- Pass/fail/skip counts
- Execution time
- Failure details
- Historical trends

**3. Comment Test Summary**
Posts results to the PR:

```markdown
### Test Results Summary 🧪

✅ All tests passed successfully!

Detailed test reports are available in the workflow artifacts.
```

**PR Detection Logic:**
```javascript
// Try to get PR number from workflow_run payload
if (workflowRun.pull_requests.length > 0) {
  prNumber = workflowRun.pull_requests[0].number;
}

// Fallback: search for PR by branch name
if (!prNumber) {
  const pulls = await github.rest.pulls.list({
    state: 'open',
    head: `${owner}:${branch}`
  });
  prNumber = pulls.data[0]?.number;
}
```

#### Example Test Report Comment

```markdown
### Test Results Summary 🧪

❌ Some tests failed. Please review the logs.

Detailed test reports are available in the workflow artifacts.

---

**Python 3.12:**
- Total: 15 tests
- ✓ Passed: 14
- ✗ Failed: 1
- Duration: 2.3s

**Python 3.13:**
- Total: 15 tests
- ✓ Passed: 15
- Duration: 2.1s

**Failed Tests:**
- `test_api_endpoint_validation` (Python 3.12)
```

---

## Key Concepts

### 1. Matrix Builds

**Definition:** Run the same job with different configurations in parallel.

**Example:**
```yaml
strategy:
  matrix:
    python-version: ["3.12", "3.13"]
    os: [ubuntu-latest, macos-latest]
```

**Generates 4 jobs:**
- Python 3.12 on Ubuntu
- Python 3.13 on Ubuntu
- Python 3.12 on macOS
- Python 3.13 on macOS

**Best practices:**
- Use for version testing
- Keep matrix small (fast CI)
- Use `fail-fast: false` to see all failures

### 2. Caching

**Types of caching:**

**a) Built-in caching:**
```yaml
- uses: actions/setup-python@v5
  with:
    cache: 'pip'  # Automatic pip cache
```

**b) Custom caching:**
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/uv
    key: ${{ runner.os }}-${{ hashFiles('*.lock') }}
```

**c) Build caching:**
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

**Cache key strategies:**
```yaml
# Good: Invalidates when dependencies change
key: ${{ runner.os }}-deps-${{ hashFiles('**/package-lock.json') }}

# Bad: Never invalidates
key: my-dependencies

# Better: Includes OS and dependency hash
key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}

# Best: Includes version, OS, and hash
key: v1-${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

### 3. Conditional Execution

**Event-based conditions:**
```yaml
if: github.event_name == 'push'
if: github.event_name == 'pull_request'
```

**Branch-based conditions:**
```yaml
if: github.ref == 'refs/heads/main'
if: startsWith(github.ref, 'refs/heads/release/')
```

**Status-based conditions:**
```yaml
if: success()        # Previous steps succeeded
if: failure()        # Previous steps failed
if: always()         # Run regardless of status
if: cancelled()      # Workflow was cancelled
```

**Combined conditions:**
```yaml
if: |
  github.event_name == 'pull_request' &&
  matrix.python-version == '3.12'
```

### 4. Artifacts

**Uploading artifacts:**
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: |
      test-results-*.xml
      coverage.xml
```

**Downloading artifacts:**
```yaml
- uses: actions/download-artifact@v4
  with:
    name: test-results
    path: ./results
```

**Artifact lifecycle:**
- Retention: 90 days (default)
- Size limit: 10GB per workflow
- Use for: test results, build outputs, reports

### 5. Workflow Dependencies

**Sequential workflows:**
```yaml
on:
  workflow_run:
    workflows: ["Tests"]
    types: [completed]
```

**Why use workflow_run:**
- Elevated permissions
- Access to artifacts
- Safe for fork PRs

### 6. Permissions

**Least privilege principle:**
```yaml
permissions:
  contents: read        # Read repository
  packages: write       # Publish packages
  pull-requests: write  # Comment on PRs
  checks: write         # Create check runs
```

**Default permissions:**
- `permissions: {}` - No permissions
- Omitted - Default permissions based on settings

### 7. Environment Variables

**Repository level:**
```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
```

**Job level:**
```yaml
jobs:
  build:
    env:
      NODE_ENV: production
```

**Step level:**
```yaml
- name: Build
  env:
    CUSTOM_VAR: value
  run: echo $CUSTOM_VAR
```

**Default environment variables:**
- `${{ github.repository }}` - owner/repo
- `${{ github.ref }}` - refs/heads/main
- `${{ github.sha }}` - Commit SHA
- `${{ github.actor }}` - User who triggered

### 8. Step Outputs

**Setting outputs:**
```yaml
- id: meta
  run: echo "version=1.0.0" >> $GITHUB_OUTPUT
```

**Using outputs:**
```yaml
- run: echo ${{ steps.meta.outputs.version }}
```

**Job outputs:**
```yaml
jobs:
  build:
    outputs:
      version: ${{ steps.meta.outputs.version }}
  deploy:
    needs: build
    steps:
      - run: echo ${{ needs.build.outputs.version }}
```

---

## Troubleshooting

### Common Issues

#### 1. Tests Failing on CI but Pass Locally

**Possible causes:**
- Environment differences
- Missing dependencies
- Timing issues
- File path differences

**Solutions:**
```yaml
# Add debug output
- name: Debug environment
  run: |
    python --version
    pip list
    env | sort

# Use same Python version locally
- uses: actions/setup-python@v5
  with:
    python-version: '3.12'  # Match local version
```

#### 2. Docker Build Failures

**Issue: Out of disk space**
```yaml
# Clean up before build
- name: Free disk space
  run: |
    docker system prune -af
    df -h
```

**Issue: Platform not supported**
```yaml
# Specify platforms explicitly
platforms: linux/amd64  # Remove arm64 if not needed
```

#### 3. Cache Not Working

**Check cache key:**
```yaml
# Add debug step
- name: Debug cache
  run: |
    echo "Cache key: ${{ runner.os }}-${{ hashFiles('**/package-lock.json') }}"
    ls -la ~/.cache/
```

**Force cache refresh:**
```yaml
# Add version prefix to invalidate
key: v2-${{ runner.os }}-deps-${{ hashFiles('**/package-lock.json') }}
```

#### 4. Permissions Errors

**Issue: Can't push Docker image**
```yaml
# Check token has correct permissions
permissions:
  packages: write  # Required for GHCR push
```

**Issue: Can't comment on PR from fork**
```yaml
# Use workflow_run instead
on:
  workflow_run:
    workflows: ["Tests"]
    types: [completed]
```

#### 5. Artifacts Not Found

**Check artifact retention:**
```yaml
- uses: actions/upload-artifact@v4
  with:
    name: my-artifact
    retention-days: 90  # Increase retention
```

**Check download pattern:**
```yaml
- uses: actions/download-artifact@v4
  with:
    pattern: test-results-*  # Use pattern for multiple artifacts
    merge-multiple: true
```

### Debugging Workflows

**Enable debug logging:**
```bash
# Set repository secrets
ACTIONS_STEP_DEBUG=true
ACTIONS_RUNNER_DEBUG=true
```

**Add debug steps:**
```yaml
- name: Debug context
  run: |
    echo "Event: ${{ github.event_name }}"
    echo "Ref: ${{ github.ref }}"
    echo "SHA: ${{ github.sha }}"
    echo "Actor: ${{ github.actor }}"

- name: Debug files
  run: |
    ls -la
    find . -name "*.xml"
```

**Use tmate for SSH debugging:**
```yaml
- name: Setup tmate session
  uses: mxschmitt/action-tmate@v3
  if: failure()  # Only on failure
```

### Performance Optimization

**1. Reduce job execution time:**
```yaml
# Use concurrency to cancel old runs
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

**2. Optimize dependencies:**
```yaml
# Install only what's needed
- run: pip install --no-deps package-name

# Use uv for faster installs
- run: pip install uv && uv pip install -r requirements.txt
```

**3. Parallelize jobs:**
```yaml
jobs:
  test:
    strategy:
      matrix:
        shard: [1, 2, 3, 4]
    steps:
      - run: pytest --shard-id=${{ matrix.shard }}
```

**4. Smart caching:**
```yaml
# Restore from multiple keys
restore-keys: |
  ${{ runner.os }}-deps-
  ${{ runner.os }}-
```

---

## Best Practices

### 1. Security

- ✅ Use `permissions` to limit access
- ✅ Pin action versions (`actions/checkout@v4`)
- ✅ Use secrets for sensitive data
- ✅ Enable Dependabot for actions
- ❌ Don't log secrets
- ❌ Don't use `pull_request_target` without caution

### 2. Reliability

- ✅ Use `if: always()` for cleanup steps
- ✅ Set reasonable timeouts
- ✅ Handle failures gracefully
- ✅ Use retry actions for flaky operations
- ❌ Don't assume external services are available
- ❌ Don't hardcode values

### 3. Maintainability

- ✅ Use meaningful job names
- ✅ Add comments for complex logic
- ✅ Keep workflows DRY (reusable workflows)
- ✅ Document workflow dependencies
- ❌ Don't create monolithic workflows
- ❌ Don't duplicate logic

### 4. Cost Efficiency

- ✅ Use concurrency to cancel old runs
- ✅ Cache dependencies aggressively
- ✅ Use matrix strategically
- ✅ Optimize Docker builds with caching
- ❌ Don't run unnecessary jobs
- ❌ Don't rebuild unchanged artifacts

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions)
- [GitHub Actions Marketplace](https://github.com/marketplace?type=actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)
- [Trivy Security Scanner](https://github.com/aquasecurity/trivy)
- [Test Reporter Action](https://github.com/dorny/test-reporter)

---

## Contributing

When modifying workflows:

1. **Test changes** on a feature branch first
2. **Document** any new concepts or actions
3. **Review** security implications
4. **Monitor** workflow execution time
5. **Update** this documentation

### Example PR Description for Workflow Changes

```markdown
## Workflow Changes

**What:** Add coverage reporting to test workflow

**Why:** Need visibility into test coverage trends

**Changes:**
- Added `--cov` flag to pytest
- Configured Codecov integration
- Added coverage threshold checks

**Testing:**
- ✅ Tested on feature branch
- ✅ Verified artifacts upload correctly
- ✅ Confirmed PR comments work

**Impact:**
- Duration: +30s per test job
- Cost: Minimal (free for open source)
```

---

**Last Updated:** 2026-02-10
**Maintained By:** Repository maintainers
**Questions?** Open an issue with the `workflows` label
