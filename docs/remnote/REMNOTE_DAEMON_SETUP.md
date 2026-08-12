# RemNote Daemon Setup Guide

This guide explains how to set up the RemNote daemon for local development and CI/CD environments.

## Prerequisites

- **Node.js** (v18+ recommended)
- **npm** or **npx**
- **RemNote CLI** (`remnote-cli` package)
- **RemNote Account** with API access

---

## Local Development Setup

### 1. Install RemNote CLI

Install the RemNote CLI globally using npm:

```powershell
npm install -g remnote-cli
```

Verify installation:

```powershell
npx remnote-cli --version
```

### 2. Authenticate RemNote

Configure RemNote authentication credentials:

```powershell
# Set environment variable (Windows PowerShell)
$env:REMNOTE_API_KEY = "your-api-key-here"

# Or add to system environment variables permanently
[System.Environment]::SetEnvironmentVariable('REMNOTE_API_KEY', 'your-api-key-here', 'User')
```

**Alternative: Using .env file**

Create a `.env` file in the project root:

```
REMNOTE_API_KEY=your-api-key-here
REMNOTE_USER_ID=your-user-id
```

### 3. Start RemNote Daemon

Start the RemNote daemon service:

```powershell
remnote-cli daemon start
```

Check daemon status:

```powershell
remnote-cli daemon status
```

Stop daemon when done:

```powershell
remnote-cli daemon stop
```

### 4. Test Connection

Test RemNote CLI functionality:

```powershell
# List RemNote documents
remnote-cli list

# Read a specific rem by ID
remnote-cli read --id <rem-id>
```

---

## CI/CD Environment Setup (GitHub Actions)

### 1. Add GitHub Secrets

Navigate to your GitHub repository settings:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add the following secrets:

| Secret Name | Description |
|-------------|-------------|
| `REMNOTE_API_KEY` | Your RemNote API key |
| `REMNOTE_USER_ID` | Your RemNote user ID (optional) |

### 2. CI Workflow Integration

The GitHub Actions workflow (`.github/workflows/test.yml`) is already configured to:

1. Install Node.js and RemNote CLI
2. Set up RemNote authentication using secrets
3. Run E2E tests with RemNote integration

**Key workflow steps:**

```yaml
- name: Set up Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '20'

- name: Install RemNote CLI
  shell: pwsh
  run: |
    npm install -g remnote-cli
    npx remnote-cli --version

- name: Setup RemNote daemon
  shell: pwsh
  env:
    REMNOTE_API_KEY: ${{ secrets.REMNOTE_API_KEY }}
  run: |
    # Configure RemNote daemon
    remnote-cli daemon start
```

### 3. Handling E2E Test Failures

E2E tests are configured with `continue-on-error: true` to prevent CI failures when RemNote daemon is unavailable.

To make E2E tests **required**:

1. Remove `continue-on-error: true` from workflow
2. Ensure RemNote secrets are configured
3. Verify daemon starts successfully in CI

---

## Testing Without Real RemNote Daemon

For unit and integration tests, RemNote calls are **mocked** using `pytest-mock`:

```python
@pytest.fixture
def mock_remnote_cli(mocker):
    """Mock RemNote CLI for isolated testing"""
    mock_run = mocker.patch("subprocess.run")
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"remId": "test", "title": "Test Rem"}'
    )
    return mock_run
```

**E2E tests** (`tests/e2e/`) require a real RemNote daemon and are skipped by default:

```python
@pytest.mark.skip(reason="Requires real RemNote daemon setup")
def test_run_pipeline_with_real_remnote_calls(self, skip_if_no_remnote, e2e_test_env):
    # Real RemNote integration test
    pass
```

To enable E2E tests:

```powershell
# Set environment variable
$env:REMNOTE_DAEMON_AVAILABLE = "1"

# Run E2E tests
pytest tests/e2e -v
```

---

## Troubleshooting

### Issue: "RemNote daemon not available"

**Solution:**

1. Verify RemNote CLI is installed: `npx remnote-cli --version`
2. Check daemon status: `remnote-cli daemon status`
3. Restart daemon: `remnote-cli daemon restart`
4. Verify API key: `echo $env:REMNOTE_API_KEY`

### Issue: "Authentication failed"

**Solution:**

1. Verify API key is correct
2. Check RemNote account permissions
3. Regenerate API key from RemNote settings
4. Update `.env` or GitHub secrets with new key

### Issue: "E2E tests timeout"

**Solution:**

1. Increase test timeout in `pytest.ini`:
   ```ini
   [pytest]
   timeout = 120
   ```
2. Check network connectivity to RemNote servers
3. Verify daemon is running and responsive

### Issue: CI workflow fails on Windows runner

**Solution:**

1. Ensure PowerShell execution policy is set:
   ```yaml
   - name: Activate virtual environment
     shell: pwsh
     run: |
       Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
       .\antigravitytest-env\Scripts\Activate.ps1
   ```
2. Use `pwsh` shell instead of `bash` for Windows compatibility

---

## Best Practices

1. **Local Development**: Use mocked RemNote for unit tests, real daemon for E2E validation
2. **CI/CD**: Enable E2E tests only after secrets are configured and daemon is verified
3. **Security**: Never commit API keys or credentials to version control
4. **Test Isolation**: Use separate RemNote test account for CI to avoid data conflicts
5. **Cleanup**: Always stop daemon after testing: `remnote-cli daemon stop`

---

## Resources

- [RemNote CLI Documentation](https://github.com/remnote/remnote-cli)
- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [pytest-mock Documentation](https://pytest-mock.readthedocs.io/)

---

## Support

For issues or questions:
1. Check [RemNote CLI Issues](https://github.com/remnote/remnote-cli/issues)
2. Review test logs in GitHub Actions artifacts
3. Contact RemNote support for API access issues
