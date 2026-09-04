#!/usr/bin/env python3
"""
Deploy the TrustLoop app to AWS: a private S3 bucket behind CloudFront, using
Origin Access Control (OAC) so the bucket itself is never publicly reachable --
CloudFront is the only path to the content.

This script is idempotent. First run creates everything and writes state.json
(bucket name, distribution id/domain -- no secrets) next to this file. Every
subsequent run reads that state, re-syncs app/dist/, and invalidates the cache,
so "redeploy after a code change" is the same command as "deploy for the first
time."

Credentials: read from the environment (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
/ AWS_DEFAULT_REGION), the standard boto3 resolution order. Never pass them as
Python arguments and never hardcode them in this file -- they must not end up in
shell history or a committed file.

Usage:
    AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_DEFAULT_REGION=us-east-1 \\
        python deploy/aws/deploy.py --bucket trustloop-chi-study-2026
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "app" / "dist"
STATE_FILE = Path(__file__).resolve().parent / "state.json"

# Managed cache policy id for "CachingOptimized" -- an AWS-provided constant, the
# same across every account, not a secret.
CACHING_OPTIMIZED_POLICY_ID = "658327ea-f89d-4fab-a63d-7e88639e58f6"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def ensure_bucket(s3, bucket: str, region: str) -> None:
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"  bucket {bucket} already exists")
        return
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code not in ("404", "NoSuchBucket"):
            raise

    print(f"  creating bucket {bucket} in {region}")
    kwargs = {"Bucket": bucket}
    if region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**kwargs)

    # Bucket-owner-enforced: disables ACLs entirely. All access control goes
    # through the bucket policy (below), which is the only mechanism CloudFront's
    # OAC needs -- there is no reason for this bucket to understand ACLs at all.
    s3.put_bucket_ownership_controls(
        Bucket=bucket,
        OwnershipControls={"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]},
    )
    # Block every form of public access. The bucket is never public; CloudFront
    # reaches it via a signed service-principal policy, not via a public ACL/URL.
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_tagging(
        Bucket=bucket,
        Tagging={"TagSet": [{"Key": "project", "Value": "trustloop"}]},
    )


def sync_dist(s3, bucket: str) -> int:
    if not DIST.exists():
        sys.exit(f"Build output not found at {DIST}. Run `npm run build` first.")

    uploaded = 0
    for path in DIST.rglob("*"):
        if not path.is_file():
            continue
        key = path.relative_to(DIST).as_posix()
        ctype, _ = mimetypes.guess_type(path.name)
        ctype = ctype or "application/octet-stream"
        # HTML must never be cached at the edge for long: it is the file that
        # carries the reference to hashed asset filenames, so a stale cached
        # index.html can point at JS/CSS that no longer exists after a redeploy.
        # Hashed assets (Vite fingerprints every build) are safe to cache for a year.
        cache_control = (
            "public, max-age=0, must-revalidate"
            if path.name == "index.html"
            else "public, max-age=31536000, immutable"
        )
        s3.put_object(
            Bucket=bucket, Key=key, Body=path.read_bytes(),
            ContentType=ctype, CacheControl=cache_control,
        )
        uploaded += 1
    print(f"  uploaded {uploaded} files")
    return uploaded


def ensure_oac(cf, name: str) -> str:
    # boto3/CloudFront omits "Items" entirely (rather than returning []) when the
    # list is empty -- .get(..., []) handles the very-first-run case.
    existing = cf.list_origin_access_controls()["OriginAccessControlList"].get("Items", [])
    for item in existing:
        if item["Name"] == name:
            return item["Id"]
    resp = cf.create_origin_access_control(
        OriginAccessControlConfig={
            "Name": name,
            "Description": "TrustLoop S3 origin access control",
            "SigningProtocol": "sigv4",
            "SigningBehavior": "always",
            "OriginAccessControlOriginType": "s3",
        }
    )
    return resp["OriginAccessControl"]["Id"]


def create_distribution(cf, bucket: str, region: str, oac_id: str) -> dict:
    origin_domain = (
        f"{bucket}.s3.amazonaws.com" if region == "us-east-1"
        else f"{bucket}.s3.{region}.amazonaws.com"
    )
    origin_id = "trustloop-s3-origin"

    config = {
        "CallerReference": f"trustloop-{int(time.time())}",
        "Comment": "TrustLoop CHI SRC study",
        "Enabled": True,
        "DefaultRootObject": "index.html",
        "PriceClass": "PriceClass_100",  # cheapest tier: NA + Europe edge locations
        "Origins": {
            "Quantity": 1,
            "Items": [{
                "Id": origin_id,
                "DomainName": origin_domain,
                "OriginAccessControlId": oac_id,
                "S3OriginConfig": {"OriginAccessIdentity": ""},
            }],
        },
        "DefaultCacheBehavior": {
            "TargetOriginId": origin_id,
            "ViewerProtocolPolicy": "redirect-to-https",
            "CachePolicyId": CACHING_OPTIMIZED_POLICY_ID,
            "Compress": True,
        },
    }
    resp = cf.create_distribution(DistributionConfig=config)
    return resp["Distribution"]


def set_bucket_policy(s3, bucket: str, distribution_arn: str) -> None:
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowCloudFrontServicePrincipalReadOnly",
            "Effect": "Allow",
            "Principal": {"Service": "cloudfront.amazonaws.com"},
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket}/*",
            "Condition": {"StringEquals": {"AWS:SourceArn": distribution_arn}},
        }],
    }
    s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))


def wait_for_deployed(cf, distribution_id: str, max_wait_s: int = 60) -> str:
    """
    Poll briefly, but don't block the whole script on it: CloudFront's first
    deployment commonly takes 5-15 minutes, and there is nothing more useful to
    do by waiting synchronously than by reporting status and letting the caller
    check back.
    """
    waited = 0
    while waited < max_wait_s:
        status = cf.get_distribution(Id=distribution_id)["Distribution"]["Status"]
        if status == "Deployed":
            return status
        time.sleep(10)
        waited += 10
    return status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--invalidate-only", action="store_true",
                     help="Skip bucket/distribution creation; just sync + invalidate.")
    args = ap.parse_args()

    s3 = boto3.client("s3", region_name=args.region)
    cf = boto3.client("cloudfront")  # CloudFront is a global service, no region

    state = load_state()

    if args.invalidate_only and not state.get("distribution_id"):
        sys.exit("No existing deployment recorded in state.json; run without "
                  "--invalidate-only first.")

    print("1/5 Ensuring S3 bucket exists...")
    if not args.invalidate_only:
        ensure_bucket(s3, args.bucket, args.region)

    print("2/5 Uploading build output...")
    sync_dist(s3, args.bucket)

    if args.invalidate_only:
        print("3/5 Skipped (--invalidate-only): reusing existing distribution")
        distribution_id = state["distribution_id"]
        domain = state["domain"]
    else:
        print("3/5 Setting up CloudFront (Origin Access Control + distribution)...")
        oac_id = ensure_oac(cf, "trustloop-oac")
        dist = create_distribution(cf, args.bucket, args.region, oac_id)
        distribution_id = dist["Id"]
        domain = dist["DomainName"]

        print("4/5 Locking the bucket to this distribution only...")
        set_bucket_policy(s3, args.bucket, dist["ARN"])

        state = {
            "bucket": args.bucket, "region": args.region,
            "distribution_id": distribution_id, "domain": domain,
            "arn": dist["ARN"],
        }
        save_state(state)

    print("5/5 Invalidating CloudFront cache...")
    cf.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": str(time.time()),
        },
    )

    print(f"\nURL:    https://{domain}")
    print(f"Bucket: {args.bucket} (region {args.region})")
    print(f"Dist:   {distribution_id}")

    if not args.invalidate_only:
        print("\nWaiting up to 60s for initial deployment status (it can take "
              "5-15 min total; the URL will 403 with an XML error until then, "
              "not a browser error page)...")
        status = wait_for_deployed(cf, distribution_id)
        print(f"Status: {status}"
              + ("" if status == "Deployed" else " (still deploying -- check "
                 "back, or re-run with --invalidate-only later to confirm)"))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
