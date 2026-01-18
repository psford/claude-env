# Production Runbook

Operational procedures for Stock Analyzer production environment.

**Last Updated:** 2026-01-18

---

## Quick Reference

| Resource | URL/Command |
|----------|-------------|
| **Production URL** | https://psfordtaurus.com |
| **Health Check** | https://psfordtaurus.com/health/live |
| **GitHub Actions** | https://github.com/psford/claudeProjects/actions |
| **Azure Portal** | https://portal.azure.com |
| **Cloudflare** | https://dash.cloudflare.com |

---

## Deployment

### Deploy to Production

Production deployments are **manual only** via GitHub Actions.

1. Go to [GitHub Actions](https://github.com/psford/claudeProjects/actions)
2. Select "Deploy to Azure Production" workflow
3. Click "Run workflow"
4. Fill in:
   - **confirm_deploy:** Type `deploy` to confirm
   - **reason:** Brief description (e.g., "v2.3 - Added favicon")
5. Select branch (usually `master` or `develop`)
6. Click "Run workflow"

The workflow will:
- Validate confirmation
- Build and test
- Build Docker image (tagged `prod-{run_number}`)
- Push to ACR
- Deploy to ACI
- Run health check

### Verify Deployment

```bash
# Check health endpoint
curl -s https://psfordtaurus.com/health/live

# Check full health status
curl -s https://psfordtaurus.com/health | jq .

# Check container status
az container show --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug --query "instanceView.state"
```

---

## Rollback

### Option 1: Redeploy Previous Image (Fastest)

Each deployment tags images as `prod-{run_number}`. To rollback:

```bash
# Login to Azure
az login

# Get current run number from last successful deploy in GitHub Actions
# Then deploy the previous image

az container create \
  --resource-group rg-stockanalyzer-prod \
  --name stockanalyzer-er34ug \
  --image acrstockanalyzerer34ug.azurecr.io/stockanalyzer:prod-{PREVIOUS_RUN_NUMBER} \
  --registry-login-server acrstockanalyzerer34ug.azurecr.io \
  --registry-username acrstockanalyzerer34ug \
  --registry-password {ACR_PASSWORD} \
  --dns-name-label stockanalyzer-er34ug \
  --ports 80 \
  --cpu 1 \
  --memory 1.5 \
  --environment-variables ASPNETCORE_ENVIRONMENT=Production ASPNETCORE_URLS=http://+:80 \
  --secure-environment-variables ConnectionStrings__DefaultConnection="{SQL_CONN}" Finnhub__ApiKey="{FINNHUB_KEY}" \
  --location westus2 \
  --os-type Linux \
  --restart-policy Always
```

### Option 2: Revert Git and Redeploy

If the code change itself was bad:

```bash
# Find the last good commit
git log --oneline -10

# Revert to that commit on master
git checkout master
git revert HEAD  # or specific commit

# Push and trigger deploy via GitHub Actions
git push
# Then manually trigger deploy workflow
```

### Option 3: Emergency - Delete and Recreate ACI

If ACI is completely broken:

```bash
# Delete the container
az container delete --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug --yes

# Wait 30 seconds
sleep 30

# Recreate with latest known-good image
az container create ... (same as Option 1)
```

**Note:** This will cause ~1-2 minutes of downtime and may change the ACI IP address. Update Cloudflare DNS if IP changes.

---

## Monitoring

### Health Endpoints

| Endpoint | Purpose | Expected Response |
|----------|---------|-------------------|
| `/health/live` | Liveness probe | 200 OK |
| `/health/ready` | Readiness (DB connected) | 200 OK |
| `/health` | Full status JSON | 200 + JSON |

### Check Container Logs

```bash
az container logs --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug
```

### Check Container Events

```bash
az container show --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug --query "containers[0].instanceView.events"
```

---

## Common Issues

### Issue: 502/504 Gateway Timeout

**Cause:** Container crashed or not responding.

**Fix:**
```bash
# Check container state
az container show --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug --query "instanceView.state"

# If not "Running", restart
az container restart --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug
```

### Issue: Database Connection Failed

**Cause:** SQL credentials expired or network issue.

**Check:**
```bash
# View container logs for connection errors
az container logs --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug | grep -i "sql\|connection"
```

**Fix:** Verify `AZURE_SQL_CONNECTION` secret in GitHub is correct.

### Issue: Cloudflare 522 Error

**Cause:** Origin (ACI) not responding on expected port.

**Check:**
1. Container is running
2. Container is on port 80
3. Cloudflare A record points to correct ACI IP

**Get current ACI IP:**
```bash
az container show --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug --query "ipAddress.ip" -o tsv
```

### Issue: ACI IP Changed After Recreate

**Fix:** Update Cloudflare DNS:
```bash
# Get new IP
NEW_IP=$(az container show --resource-group rg-stockanalyzer-prod --name stockanalyzer-er34ug --query "ipAddress.ip" -o tsv)

# Update Cloudflare (using API)
curl -X PATCH "https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{RECORD_ID}" \
  -H "Authorization: Bearer {CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "{\"content\":\"$NEW_IP\"}"
```

---

## Contacts

| Role | Contact |
|------|---------|
| Primary | Patrick (repo owner) |
| Azure Support | https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade |
| Cloudflare | https://dash.cloudflare.com (free tier = community support) |

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-18 | Initial runbook created |
