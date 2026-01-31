## GCP Deployment Runbook (Cloud Run + Pub/Sub)

This repo’s GCP migration (PR **#397**) deploys Emoji Smith as:

- **Cloud Run (public)**: `emoji-smith-webhook` (Slack calls this)
- **Pub/Sub**: `emoji-smith-jobs` topic + push subscription to worker
- **Cloud Run (internal)**: `emoji-smith-worker` (Pub/Sub pushes jobs here)
- **Secret Manager**: stores Slack/OpenAI/Google credentials (injected into Cloud Run)
- **Artifact Registry**: stores container images
- **GitHub Actions (OIDC / Workload Identity Federation)**: deploys without service account keys

---

## Before you start (one-time prerequisites)

### Confirm the PR is merged (or you’re on the PR branch)

You need the following paths from PR #397 to exist in your checkout:

- `infra_gcp/terraform/`
- `.github/workflows/deploy-gcp.yml`
- `Dockerfile.webhook`, `Dockerfile.worker`
- `src/emojismith/infrastructure/gcp/`

If these files aren’t present, you’re not on the PR branch / the PR isn’t merged yet.

---

## Blocker fix (required before first deploy)

### Fix `PUBSUB_TOPIC` so publishing works

**Why:** The Python publisher (`PubSubJobQueue`) expects `PUBSUB_TOPIC` to be the **topic name** (e.g. `emoji-smith-jobs`), but Terraform currently sets it to the topic **ID** (usually a fully-qualified resource path).

**Do this:**

1. Open `infra_gcp/terraform/cloud_run_webhook.tf`
2. Find the environment variable block for `PUBSUB_TOPIC`
3. Change it from:
   - `google_pubsub_topic.jobs.id`
4. To:
   - `google_pubsub_topic.jobs.name`

After that change, the webhook can publish jobs successfully.

---

## Step 1 — Create / select a GCP project (click-by-click)

1. Go to the Google Cloud Console: `https://console.cloud.google.com/`
2. In the top bar, click the **project selector** (next to “Google Cloud”).
3. Click **New Project**.
4. Enter:
   - **Project name**: `emoji-smith` (or your preference)
   - **Project ID**: note this value (you’ll use it later)
5. Click **Create**.

### Attach billing (required)

1. In the left sidebar, go to **Billing**.
2. If prompted, click **Link a billing account** (or “Manage billing accounts” → select one).
3. Ensure the project now shows an active billing account.

### Capture the Project Number (required)

1. Go to **IAM & Admin** → **Settings**.
2. Copy:
   - **Project ID**
   - **Project number** (numeric)

Keep both handy.

---

## Step 2 — Run Terraform to create GCP infrastructure

Terraform lives in `infra_gcp/terraform/`.

### 2.1 Local auth (click-by-click + minimal commands)

1. Install the Google Cloud CLI if you don’t have it:
   - `https://cloud.google.com/sdk/docs/install`
2. Install Terraform (>= 1.6):
   - `https://developer.hashicorp.com/terraform/downloads`
3. In a terminal:
   - Sign in to gcloud (opens a browser flow)
   - Configure the active project to your new project ID

### 2.2 Configure Terraform variables

1. In your editor, open `infra_gcp/terraform/terraform.tfvars`.
2. Replace placeholders:
   - `project_id = "your-project-id"` → your real **Project ID**
   - `region = "us-central1"` (leave unless you need a different region)
   - `github_repo_owner` → `willtech3` (or your fork owner)
   - `github_repo_name` → `emoji-smith` (or your fork name)
   - `github_repo_owner_id` → numeric owner id (GitHub user/org numeric ID)

   Tip to get your numeric owner id:
   - On GitHub, go to your profile/org page, open DevTools → Network (advanced), or use `gh api users/<OWNER> --jq .id`.

### 2.3 Apply Terraform

Run Terraform from `infra_gcp/terraform/`:

- `terraform init`
- `terraform plan`
- `terraform apply`

Terraform will:
- enable APIs
- create Artifact Registry
- create Cloud Run services (initially pointing at placeholder images)
- create Pub/Sub topics/subscriptions
- create Secret Manager secrets (no values yet)
- create Workload Identity Federation resources for GitHub Actions

### 2.4 Record Terraform outputs you will need later

After apply, record:
- `workload_identity_provider`
- `cicd_service_account_email`
- `webhook_url`

---

## Step 3 — Add secret values (Secret Manager “versions”)

Terraform creates the **secrets**, but you must create secret **versions** (values) out-of-band.

### Click-by-click (Console)

1. Go to **Security** → **Secret Manager**.
2. You should see secrets named:
   - `emoji-smith-slack-bot-token`
   - `emoji-smith-slack-signing-secret`
   - `emoji-smith-openai-api-key`
   - `emoji-smith-google-api-key`
3. For each secret:
   - Click the secret
   - Click **Add new version**
   - Paste the correct value
   - Click **Save**

---

## Step 4 — Wire GitHub Actions → GCP (Workload Identity Federation)

This migration uses **keyless auth** (OIDC). There is no JSON key file.

### 4.1 Add GitHub Actions variables (click-by-click)

1. In GitHub, go to your repo → **Settings**
2. In the left sidebar, go to **Secrets and variables** → **Actions**
3. Click **Variables** tab → **New repository variable**
4. Add:
   - **Name**: `GCP_PROJECT_ID`
     - **Value**: your GCP **Project ID**
   - **Name**: `GCP_PROJECT_NUMBER`
     - **Value**: your GCP **Project number** (numeric)
   - **Name**: `GCP_WORKLOAD_IDENTITY_PROVIDER`
     - **Value**: Terraform output `workload_identity_provider`
   - **Name**: `GCP_CICD_SERVICE_ACCOUNT`
     - **Value**: Terraform output `cicd_service_account_email`

### 4.2 Update the workflow to use those variables

Open `.github/workflows/deploy-gcp.yml` and replace placeholders so it uses:
- `${{ vars.GCP_PROJECT_ID }}`
- `${{ vars.GCP_PROJECT_NUMBER }}`
- `${{ vars.GCP_WORKLOAD_IDENTITY_PROVIDER }}`
- `${{ vars.GCP_CICD_SERVICE_ACCOUNT }}`

At minimum, you must remove:
- `PROJECT_ID: your-gcp-project-id`
- any reference to `${{ env.PROJECT_NUMBER }}` unless you also define it

**Goal:** the auth step should use the exact provider string Terraform output, not a hardcoded path.

---

## Step 5 — First real deploy (via GitHub Actions)

1. Ensure the PR is **not DRAFT** and is merged to `main` (or push the workflow changes to `main`).
2. Go to GitHub → **Actions** tab.
3. Click workflow **“Deploy to GCP”**.
4. Click the latest run and verify:
   - **build-and-test** succeeds
   - **build-images** pushes images to Artifact Registry
   - **deploy** updates both Cloud Run services

---

## Step 6 — Configure the Slack app to point at Cloud Run (click-by-click)

You need the Cloud Run webhook base URL from Terraform output: `webhook_url`.

### 6.1 Events API

1. Go to `https://api.slack.com/apps`
2. Select your app
3. Click **Event Subscriptions**
4. Enable events (if not enabled)
5. Set **Request URL** to:
   - `${WEBHOOK_URL}/slack/events`
6. Wait for Slack “Verified” confirmation, then click **Save Changes**

### 6.2 Interactivity & Shortcuts

1. In the same Slack app, click **Interactivity & Shortcuts**
2. Enable interactivity (if not enabled)
3. Set **Request URL** to:
   - `${WEBHOOK_URL}/slack/interactive`
4. Click **Save Changes**

---

## Step 7 — Smoke test (click-by-click)

### 7.1 Verify Cloud Run services exist

1. In GCP Console, go to **Cloud Run**
2. Confirm services exist:
   - `emoji-smith-webhook`
   - `emoji-smith-worker`
3. Click `emoji-smith-webhook` → **URL** → open `/health`:
   - `${WEBHOOK_URL}/health` should return healthy JSON

### 7.2 Verify Pub/Sub flow

1. Go to **Pub/Sub** → **Topics**:
   - confirm `emoji-smith-jobs` exists
2. Go to **Pub/Sub** → **Subscriptions**:
   - confirm `emoji-smith-jobs-push` exists
3. Trigger an emoji generation in Slack
4. Go to **Logging** → **Logs Explorer**
   - Resource: **Cloud Run Revision**
   - Service: `emoji-smith-webhook` (verify publish log)
   - Service: `emoji-smith-worker` (verify job processed)

### 7.3 Watch the DLQ (optional but recommended)

1. Go to **Pub/Sub** → **Subscriptions**
2. Click `emoji-smith-jobs-dlq-pull`
3. If messages appear here, the worker is failing repeatedly (check worker logs).

---

## Ongoing operations (recommended)

- **Artifact Registry storage**: keep it under the free tier (Terraform keeps only a few recent versions).
- **Secret rotation**: add a new secret version; Cloud Run reads `latest`.
- **Rollback**: update Slack request URLs back to AWS while AWS infra still exists.

