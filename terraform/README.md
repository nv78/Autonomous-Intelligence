# Terraform — AWS deployment for Autonomous-Intelligence

Provisions: ECR repo, ECS Fargate cluster/service for the backend behind an ALB,
RDS MySQL, and an S3 + CloudFront distribution for the web frontend.
CloudFront routes `/api/*`, `/auth/*`, and `/health` to the backend ALB so the
React app can keep using same-origin relative paths in production, and
everything else to the S3 bucket holding the Vite build.

This stack deliberately uses the account's **default VPC** to keep the first
deploy simple. For a hardened production setup, swap `network.tf` for a real
VPC module with private subnets + NAT for ECS/RDS.

## One-time setup

1. Create an S3 bucket for Terraform state and uncomment/fill in the `backend "s3"`
   block in `versions.tf`, or pass `-backend-config` flags to `terraform init`.
2. `terraform init`
3. Provide secrets — never commit these. Use a `terraform.tfvars` file (gitignored)
   or `TF_VAR_*` environment variables:
   ```
   export TF_VAR_db_password="..."
   export TF_VAR_jwt_secret_key="..."
   export TF_VAR_anthropic_api_key="..."
   export TF_VAR_openai_api_key="..."
   export TF_VAR_stripe_secret_key="..."
   export TF_VAR_stripe_webhook_secret="..."
   export TF_VAR_stripe_price_basic="..."
   export TF_VAR_stripe_price_pro="..."
   export TF_VAR_provider_key_encryption_key="..."
   ```
   (see "Stripe billing + BYOK provider keys" below for how to obtain these)
4. `terraform plan` / `terraform apply`

## After the first apply

- Push a backend image to the ECR repo Terraform created (`ecr_repository_url` output),
  then either re-run `terraform apply -var backend_image_tag=<sha>` or let
  `.github/workflows/deploy.yml` roll it via `aws ecs update-service --force-new-deployment`.
- Sync the built frontend (`packages/web/dist`) to the S3 bucket (`s3_bucket_name` output)
  and invalidate CloudFront — `deploy.yml` already does both.
- Point your domain's DNS at the `cloudfront_domain_name` output (or set
  `domain_name` + `acm_certificate_arn` to use a custom domain with HTTPS).

## GitHub Actions authentication

The deploy workflow uses GitHub's OpenID Connect token to assume an AWS IAM
role. Configure the role ARN as a repository secret named
`AWS_ROLE_ARN`. The role's trust policy must allow this repository and the
selected GitHub environment to call `sts:AssumeRoleWithWebIdentity`.

The workflow intentionally does not use long-lived
`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` credentials.

## Stripe billing + BYOK provider keys

`ecs.tf` wires 5 env vars beyond the original set — `PROVIDER_KEY_ENCRYPTION_KEY`,
`OLLAMA_BASE_URL`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_BASIC`, `STRIPE_PRICE_PRO`
(`STRIPE_PRICE_ENTERPRISE` exists too but is intentionally left unset — enterprise
is "contact us", not self-serve). `terraform apply` alone does not make these
live; follow all the steps below.

**Prerequisites:** a **live-mode** Stripe account (not the test-mode one used for
local dev) and AWS credentials for this account.

1. **Get real Stripe values** (Stripe Dashboard, switched out of Test mode):
   - Secret key: Developers → API keys (`sk_live_...`).
   - Prices: decide real dollar amounts for the basic/pro tiers first — the
     `$9.99`/`$29.99` in `packages/backend/scripts/setup_stripe_prices.py` are
     explicitly marked placeholders. Either edit `_BASIC_PRICE_CENTS`/
     `_PRO_PRICE_CENTS` in that script and run it with `STRIPE_SECRET_KEY=sk_live_...`,
     or create the two recurring monthly Prices by hand in the Dashboard.
   - Webhook: Developers → Webhooks → Add endpoint, URL =
     `https://<production-domain>/api/payments/webhook`, events at minimum
     `checkout.session.completed`, `customer.subscription.deleted`,
     `customer.subscription.updated`, `invoice.payment_succeeded`. Copy the signing secret (`whsec_...`) —
     this is a *different* value from whatever `stripe listen` gave you locally.

2. **Generate a real encryption key** (encrypts users' BYOK provider keys at rest —
   don't reuse whatever fallback was used locally):
   ```
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. **Apply**, supplying the values from steps 1-2 as `TF_VAR_*` (see "One-time
   setup" above) or `-var` flags, then run `terraform apply`. This creates a
   **new revision** of the backend ECS task definition — it does not yet affect
   the running service.

4. **Point the running service at the new revision — don't skip this.** The
   `aws_ecs_service.backend` resource has `lifecycle { ignore_changes =
   [task_definition] }` specifically so `deploy.yml`'s image-only redeploys
   don't fight with Terraform — but that also means a plain `terraform apply`
   never updates the live service to the new revision. After applying, run:
   ```
   aws ecs update-service \
     --cluster <ECS_CLUSTER> \
     --service <ECS_SERVICE_BACKEND> \
     --task-definition anote-ai-backend \
     --force-new-deployment
   aws ecs wait services-stable --cluster <ECS_CLUSTER> --services <ECS_SERVICE_BACKEND>
   ```
   (Omitting the revision number after the family name tells AWS to use the
   latest active revision — the one Terraform just created.)

5. **Verify**:
   - CloudWatch logs (`/ecs/anote-ai-backend`) show the container starting
     cleanly and the migration step (auto-run via `entrypoint.sh`) applying
     without errors.
   - `GET /api/payments/plans` on the production API shows `available: true`
     for basic/pro.
   - One real end-to-end test: subscribe with a real card (or dry-run first
     against a *separate* test-mode webhook endpoint), and confirm the Stripe
     Dashboard shows the webhook delivered successfully and the DB's
     `users.plan`/`credits` updated.

## Google Sign-In

This uses the server-side OAuth redirect flow, entirely on the backend — the
frontend just links to `/auth/google/login`; there's no Google JS SDK and no
frontend build-time env var. The backend redirects the browser to Google,
Google redirects back to `/callback` (a bare path outside `/auth/*`, matching
the exact "Authorized redirect URI" registered on the OAuth client — see the
routing rule `cloudfront.tf` adds for it), the backend exchanges the code
server-side (needs the client *secret*, unlike the old popup approach), then
redirects the browser to `${FRONTEND_URL}/oauth/callback?token=...` where the
SPA picks up the JWT.

1. Create an OAuth client ID in Google Cloud Console (APIs & Services → Credentials →
   Create Credentials → OAuth client ID → Web application). Add the production
   redirect URI — `https://<cloudfront-or-custom-domain>/callback` — under
   **Authorized redirect URIs** (not "JavaScript origins", a different field).
   For local dev this is `http://127.0.0.1:5000/callback`.
2. Apply with these vars (or `TF_VAR_*`):
   ```
   -var google_client_id=<id>.apps.googleusercontent.com
   -var google_client_secret=GOCSPX-...
   -var google_oauth_redirect_uri=https://<domain>/callback
   -var frontend_url=https://<domain>
   ```
   Same "new revision doesn't affect the running service" caveat as Stripe
   above — force a new ECS deployment after applying.
3. No GitHub Actions secret or frontend build step change needed — the client
   ID/secret never reach the frontend bundle in this flow.

## What this does NOT cover yet

- Redis / Tika sidecars (used by docker-compose locally) — add `aws_elasticache_cluster`
  and a second ECS service if those are needed in production.
- Multi-AZ / private subnets — current setup runs ECS tasks with public IPs in the
  default VPC's public subnets for simplicity.
- CI/CD bootstrapping of the Terraform state bucket itself (chicken-and-egg —
  create that bucket manually once, by hand).

## AI coworker

`coworker.tf` adds what the coworker needs in production:

- **Twin bucket.** A private S3 bucket for voice/video samples and consent recordings. It has KMS encryption, versioning, all public access blocked, and a TLS-only policy. Noncurrent versions expire after 7 days. Revoking a twin deletes every version right away.
- **Worker service.** One `coworker-worker` Fargate task running `python -m coworker.worker`. It uses the backend image, environment, and secrets.
- **Config.** `BACKEND_URL` drives the Google and Slack OAuth callback URLs. Integration keys go in Secrets Manager: `slack_client_secret`, `elevenlabs_api_key`, `recall_api_key`, `tavus_api_key`, `pilot_slack_webhook_url`.

With `APP_ENV=production` the backend refuses to start on a default or short `JWT_SECRET_KEY`, a missing `PROVIDER_KEY_ENCRYPTION_KEY`, or a SQLite coworker store. Generate the encryption key with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keys stored before you set it still decrypt. `ALLOW_UNSAFE_CONFIG=1` bypasses the check; use it only to recover a broken deploy.

CI deploys roll the backend service. To roll the worker onto a new image too:

```bash
aws ecs update-service --cluster "$(terraform output -raw ecs_cluster_name)" \
  --service "$(terraform output -raw coworker_worker_service_name)" --force-new-deployment
```
