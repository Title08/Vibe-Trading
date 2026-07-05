run codex resume 019f3043-d869-72c0-ae62-5f0ecb9dcde1

  # AKS Auto-Sync Deployment Plan

  ## Summary

  - Deploy fork to Azure AKS, not GitHub Pages. GitHub Pages can host static files only; this app needs FastAPI + frontend from the Docker image.
  - Use Azure AKS + ACR + one persistent Azure Disk PVC + one public Azure DNS label: title08-vibe-trading-<repo-id>.eastus.cloudapp.azure.com.
  - Use Caddy sidecar for HTTPS on that Azure subdomain, proxying to Vibe-Trading on localhost:8899.
  - Auto-merge upstream/main into origin/main every 6 hours, preserve fork extensions, run tests, then deploy same commit to AKS.

  ## Key Changes

  - Add deploy/aks/ manifests:
      - Namespace, Deployment, Service, PVC, ConfigMap.
      - App container uses existing Dockerfile, port 8899, /health probes.
      - Caddy sidecar exposes 80/443, auto TLS, reverse proxy to 127.0.0.1:8899.
      - One managed-csi Azure Disk PVC, 32Gi, mounted with subPaths for /app/agent/runs, /app/agent/sessions, /app/agent/uploads, /app/agent/.swarm/runs, /home/vibe/.vibe-trading, and Caddy cert storage.

  - Add .github/workflows/sync-and-deploy-aks.yml:
      - schedule: "17 */6 * * *" plus workflow_dispatch.
      - Fetch upstream/main, merge into origin/main with normal merge commit, never force-push.
      - If merge conflict: abort, open/update GitHub issue, no deploy.
      - Run existing Python/frontend CI. If fail: no push, no deploy.
      - Build image, push to ACR as vibe-trading:<merged-sha>, deploy to AKS, wait rollout.

  - GitHub secrets/vars:
      - Azure OIDC: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID.
      - Azure vars: AZURE_RESOURCE_GROUP, AKS_CLUSTER_NAME, ACR_LOGIN_SERVER, AZURE_LOCATION=eastus, AZURE_DNS_LABEL.
      - Runtime secrets synced into Kubernetes Secret: API_AUTH_KEY, LANGCHAIN_PROVIDER, LANGCHAIN_MODEL_NAME, provider API key such as OPENROUTER_API_KEY or DEEPSEEK_API_KEY.

  ## Test Plan

  - Local: docker build . and existing CI commands from .github/workflows/test.yml.
  - Manifests: kubectl apply --dry-run=server -k deploy/aks.
  - Deploy: kubectl rollout status deployment/vibe-trading -n vibe-trading.
  - Smoke: curl -fsS https://$PUBLIC_HOST/health.
  - Persistence: create one chat/session, delete pod, verify session/runs remain.
  - Sync safety: test no-upstream-change path, conflict path, failing-test path, successful merge/deploy path.

  ## Assumptions

  - Fork will keep custom extensions; origin/main is upstream plus fork commits, not exact mirror.
  - Single replica for v1 because Azure Disk is ReadWriteOnce. Scaling later needs Azure Files or external state.
  - If Caddy cannot issue TLS for the Azure cloudapp.azure.com hostname, deployment fails closed; do not expose API over plain HTTP.
  - Azure Student can cover early usage with credit/free allowances, but AKS worker nodes still consume VM resources.

  ## References

  - Azure for Students: https://azure.microsoft.com/en-us/free/students
  - AKS overview/cost model: https://learn.microsoft.com/en-us/azure/aks/what-is-aks
  - AKS DNS label/static IP: https://learn.microsoft.com/en-us/azure/aks/static-ip
  - Azure Disk PVC: https://learn.microsoft.com/en-us/azure/aks/create-volume-azure-disk
  - GitHub scheduled workflows: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
  - Azure OIDC for GitHub Actions: https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect
  - Caddy automatic HTTPS: https://caddyserver.com/docs/automatic-https


