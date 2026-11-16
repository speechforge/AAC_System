#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$project_root"
cf_cli() {
  npm exec --cache "$project_root/.runtime/cloudflare-npm" --yes --package=node@22 --package=wrangler@4.162.0 -- wrangler "$@"
}
# The account must already have been authorized with Wrangler's device login.
# This creates a Cloudflare Pages project; it never starts a tunnel.
cf_cli pages project create indic-aac-studio-ravindra --production-branch main
cf_cli pages deploy deploy/free-demo/dist --project-name indic-aac-studio-ravindra --branch main --commit-dirty=true
