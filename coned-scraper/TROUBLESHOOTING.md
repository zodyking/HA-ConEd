# Installation Error Troubleshooting

## Common Causes of Installation Failures

### 1. Docker Build Failures
Check supervisor logs for specific Docker build errors:
```bash
ha supervisor logs
```

Common issues:
- **Missing dependencies**: Playwright or Python packages fail to install
- **Architecture mismatch**: Base image not available for your architecture
- **Build timeout**: Build takes too long and times out

### 2. Configuration Validation Errors
- **Invalid YAML**: Check `config.yaml` syntax
- **Missing required fields**: Ensure all required fields are present
- **Schema validation**: Check schema types match options

### 3. File Structure Issues
- **Missing files**: Ensure all required files exist
- **Wrong paths**: Check COPY paths in Dockerfile match actual file structure

## Quick Fixes

### Fix 1: Verify Repository Structure
Ensure these files exist:
- `coned-scraper/config.yaml` ✅
- `coned-scraper/Dockerfile` ✅
- `coned-scraper/build.yaml` ✅
- `coned-scraper/run.sh` ✅
- `coned-scraper/python-service/requirements.txt` ✅
- All Python files in `coned-scraper/python-service/` ✅

### Fix 2: Check Supervisor Logs
```bash
# SSH into Home Assistant
ha supervisor logs | grep -i "coned\|error\|fail" | tail -50
```

### Fix 3: Verify config.yaml
```bash
# Check YAML syntax
python3 -c "import yaml; yaml.safe_load(open('coned-scraper/config.yaml'))"
```

### Fix 4: Test Docker Build Locally (if possible)
```bash
cd coned-scraper
docker build -t test-coned-scraper .
```

## Current Configuration Status

✅ **config.yaml** - Valid YAML format
✅ **Dockerfile** - Uses BUILD_FROM pattern
✅ **build.yaml** - Specifies base images
✅ **run.sh** - Uses jq for config parsing
✅ **Structure** - Matches Home Assistant requirements

## Next Steps

1. **Check supervisor logs** for specific error messages
2. **Verify repository is public** on GitHub
3. **Ensure all files are pushed** to GitHub
4. **Try removing and re-adding** the repository in Home Assistant

If the error persists, the supervisor logs will show the exact cause.

