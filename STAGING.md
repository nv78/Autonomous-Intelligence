# Staging

Staging runs `develop` on its own URL (for example `https://staging.ourogen.ai`), so you can do the dry run and review changes without merging to `main`. Every push to `develop` deploys there automatically (`.github/workflows/deploy-staging.yml`). Production deploys only from `main` (`deploy.yml`).

Until it's set up, the staging workflow skips with a notice. Nothing fails.

## One-time setup (about an hour)

### 1. A host

Use a small separate EC2 instance (t3.medium is plenty) with the SSM agent and Docker. Don't share the production host: staging runs migrations and the worker against its own database.

On the instance:

```bash
sudo mkdir -p /opt/ourogen-staging && sudo chown $USER /opt/ourogen-staging
git clone https://github.com/anote-ai/Panacea.git /opt/ourogen-staging   # use a read-only deploy key
cd /opt/ourogen-staging
cp packages/backend/.env.example .env.staging   # then fill it in (step 3)
```

Give the instance an IAM role that can pull from your ECR repository, the same as production. Put HTTPS in front of port 5000 with your usual load balancer or Caddy/nginx, at e.g. `staging-api.ourogen.ai`, or serve both from `staging.ourogen.ai` like production does.

### 2. The web app

Create an S3 bucket and a CloudFront distribution for the staging frontend, like production's, pointing at `staging.ourogen.ai`.

### 3. `.env.staging` on the host

Fill it in like production, with these differences:

| Setting | Staging value |
|---|---|
| `APP_ENV` | `production` (so the same safety checks run) |
| `BACKEND_URL`, `FRONTEND_URL` | `https://staging.ourogen.ai` |
| `JWT_SECRET_KEY`, `PROVIDER_KEY_ENCRYPTION_KEY` | **New values**, never production's |
| `DB_PASSWORD` | Its own |
| OAuth apps (Google, Microsoft, Slack) | Add the staging redirect URLs to the same apps, or use separate test apps |
| `STRIPE_*` | Test-mode keys |
| `TWILIO_*`, inbound email | Leave empty unless you're testing those (a number's webhook can only point at one place) |

### 4. GitHub

**Settings → Environments → New environment → `staging`**, then add:

| Kind | Name | Value |
|---|---|---|
| Secret | `STAGING_INSTANCE_ID` | The EC2 instance ID |
| Secret | `AWS_ROLE_ARN` | Only if the deploy role's trust policy doesn't allow `environment:staging`; then a staging role |
| Variable | `STAGING_APP_DIR` | `/opt/ourogen-staging` |
| Variable | `STAGING_URL` | `https://staging.ourogen.ai` |
| Variable | `STAGING_S3_BUCKET` | The staging bucket |
| Variable | `STAGING_CLOUDFRONT_DISTRIBUTION_ID` | The staging distribution |

`AWS_REGION` and `ECR_REPOSITORY` come from the repository variables production already uses. Images are tagged `staging-<sha>` and `staging`, never `latest`.

The AWS deploy role is assumed through GitHub OIDC. If its trust policy only allows `ref:refs/heads/main`, add `repo:anote-ai/Panacea:environment:staging` to its allowed subjects.

### 5. Deploy

Run **Actions → Deploy staging → Run workflow**, or push to `develop`. The workflow:
- builds and pushes the image;
- runs `docker compose up` on the host (with `deploy/staging/compose.override.yml`);
- checks the configuration with `python -m coworker.config`;
- publishes the web app;
- smoke-tests the URL.

Then run the vendor check on the host:

```bash
cd /opt/ourogen-staging && BACKEND_IMAGE=$(docker inspect --format '{{.Config.Image}}' $(docker compose ps -q backend)) \
  docker compose -f docker-compose.yml -f deploy/staging/compose.override.yml --env-file .env.staging exec backend python -m coworker.vendor_check
```

## Dry run on staging

Follow issue #397 on staging with your own accounts. When it's clean, merge `develop` to `main` and production gets exactly what you tested.
