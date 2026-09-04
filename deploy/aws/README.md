# AWS Deployment

TrustLoop is served as a static site from a **private S3 bucket behind CloudFront**,
using Origin Access Control (OAC) — the bucket has no public URL at all; CloudFront
is the only path in. This is the standard secure pattern for a static SPA on AWS
(the alternative, S3 "static website hosting", makes the bucket itself a public HTTP
endpoint, which is unnecessary here).

## What's deployed

- **S3 bucket** — build output only (`app/dist/`), blocked from all public access
- **CloudFront distribution** — HTTPS, global edge caching, `PriceClass_100` (cheapest
  tier: North America + Europe edge locations — fine for a study audience)
- **No custom domain** — served from the default `*.cloudfront.net` address

Data collection is unaffected by any of this: it still goes to Supabase per
`server/supabase_schema.sql`. AWS here is hosting the frontend only.

## Redeploying after a code change

```bash
cd trustloop
python stimuli/build_trials.py && python stimuli/validate_trials.py
cd app && npm run build && cd ..

AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_DEFAULT_REGION=us-east-1 \
    python deploy/aws/deploy.py --bucket trustloop-chi-study-2026 --invalidate-only
```

`--invalidate-only` skips bucket/distribution creation (already exist, recorded in
`deploy/aws/state.json`) and just re-syncs `app/dist/` and busts the CloudFront cache.
Without that flag the script is still safe to re-run — it detects the existing bucket
and distribution rather than erroring — but `--invalidate-only` is faster.

## Cache behaviour, and why it matters here

Vite fingerprints every JS/CSS filename with a content hash (`index-DR9x5Xcm.css`), so
those files are cached at the edge for a year — a redeploy produces new filenames, so
there is no staleness risk. `index.html` is the opposite: `max-age=0, must-revalidate`,
because it is the one file that *references* those hashed filenames. If it were cached
long, a participant could load a stale `index.html` pointing at JS that no longer
exists in the bucket after a redeploy. The invalidation on every deploy is a second
layer of the same protection.

## Cost

At this traffic level (a few hundred study sessions, each loading ~360 KB once),
expect **low single-digit dollars a month, likely within the AWS Free Tier** (1 TB/month
CloudFront data transfer, 2M HTTP requests — both free tier limits are far above what
this study will use). S3 storage cost for a 360 KB bucket is negligible.

## Rotating or removing access

The IAM user (`trustloop-deploy`) used to run `deploy.py` is scoped to only
`s3:*` on buckets named `trustloop-*` and CloudFront management — it cannot reach
anything else in the account. Even so, once you're done deploying for a while:

1. IAM Console → Users → `trustloop-deploy` → Security credentials → deactivate/delete
   the access key.
2. Nothing about the live site depends on that key staying active — it's only needed
   to run this script, not to serve traffic.
3. To redeploy later, create a fresh access key on the same user (the policy is
   already attached) rather than leaving one alive indefinitely.

## Tearing it down entirely

```python
# Not scripted deliberately -- deletion is destructive and should be a conscious,
# one-off action taken from the console, not a flag on a reusable deploy script.
```
CloudFront console → disable the distribution → wait for it to finish disabling
(a few minutes) → delete it. Then S3 console → empty the bucket → delete the bucket.
