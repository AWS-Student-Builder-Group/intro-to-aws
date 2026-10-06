#!/usr/bin/env bash
# Delete everything scripts/deploy.sh created.
#
#   scripts/teardown.sh
#
# Both buckets are emptied first, because CloudFormation can't delete a bucket that still
# has files. Deleting the CloudFront distribution takes a few minutes.
# Uses the same STACK_NAME and AWS_REGION variables as deploy.sh.
set -euo pipefail

cd "$(dirname "$0")/.."

STACK_NAME="${STACK_NAME:-quickdrop}"
REGION="${AWS_REGION:-$(aws configure get region || true)}"

for tool in aws sam; do
  command -v "$tool" >/dev/null || { echo "Missing '$tool'. Install it first." >&2; exit 1; }
done
[ -n "$REGION" ] || { echo "No region set. Run 'aws configure' or set AWS_REGION." >&2; exit 1; }

output() {
  aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
UPLOAD_BUCKET="$(output UploadBucketName)"
SITE_BUCKET="$(output SiteBucketName)"

echo "This will delete stack '$STACK_NAME' in $REGION, plus every file in:"
echo "  $UPLOAD_BUCKET"
echo "  $SITE_BUCKET"
read -r -p "Type 'yes' to continue: " answer
[ "$answer" = "yes" ] || { echo "Cancelled."; exit 1; }

aws s3 rm "s3://$UPLOAD_BUCKET" --recursive --region "$REGION"
aws s3 rm "s3://$SITE_BUCKET" --recursive --region "$REGION"
sam delete --stack-name "$STACK_NAME" --region "$REGION" --no-prompts

echo "Deleted."
