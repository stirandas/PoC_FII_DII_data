#!/bin/bash
# =============================================================================
# deploy_scheduler.sh
# =============================================================================
# Purpose:
#   Idempotently deploy or update the Cloud Scheduler job that triggers
#   the Cloud Run Job 'nse-fii-dii-data-poc-gcloud-image'.
#
# Notes:
#   - Job name: nse_fii_dii_data_poc_job_schedule
#   - Region: asia-south1
#   - OAuth service account: poc-svc-ac@nse-fii-dii-poc.iam.gserviceaccount.com
#   - Scheduler YAML documentation: cloud-scheduler/nse_fii_dii_job_schedule.yaml
# =============================================================================

JOB_NAME="nse_fii_dii_data_poc_job_schedule"
LOCATION="asia-south1"
URI="https://asia-south1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/nse-fii-dii-poc/jobs/nse-fii-dii-data-poc-gcloud-image:run"
OAUTH_SERVICE_ACCOUNT="poc-svc-ac@nse-fii-dii-poc.iam.gserviceaccount.com"
SCHEDULE="*/15 17-20 * * 1-5"
TIMEZONE="Asia/Calcutta"
BODY="{}"
HEADERS="Content-Type:application/json"

echo "Checking if Cloud Scheduler job '$JOB_NAME' exists in location '$LOCATION'..."
if gcloud scheduler jobs describe "$JOB_NAME" --location="$LOCATION" &>/dev/null; then
    echo "Job exists. Updating existing job..."
    gcloud scheduler jobs update http "$JOB_NAME" \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --http-method=POST \
        --uri="$URI" \
        --oauth-service-account-email="$OAUTH_SERVICE_ACCOUNT" \
        --headers="$HEADERS" \
        --body="$BODY"
    echo "Job updated successfully."
else
    echo "Job does not exist. Creating new job..."
    gcloud scheduler jobs create http "$JOB_NAME" \
        --schedule="$SCHEDULE" \
        --time-zone="$TIMEZONE" \
        --http-method=POST \
        --uri="$URI" \
        --oauth-service-account-email="$OAUTH_SERVICE_ACCOUNT" \
        --headers="$HEADERS" \
        --body="$BODY"
    echo "Job created successfully."
fi

echo "Deployment complete. Verify in GCP console or with:"
echo "gcloud scheduler jobs describe $JOB_NAME --location=$LOCATION"
