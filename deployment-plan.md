# Interly Deployment Plan

## Purpose

Define the intended deployment workflow for Interly without implementing it yet. The goal is to let Interly deploy a selected local repository to its configured deployment provider from the Interly terminal while preserving Interly's existing permission, audit, privacy, and safety model.

This document is a handoff schema for future implementation work. It should be reconciled against the repository state before any deployment code is added.

## User Experience

Primary command intent:

```text
You: deploy interly to production
```

Equivalent natural-language requests should be allowed, for example:

```text
please deploy interly
push intermail main to production
deploy the latest greyanalytics main
```

Interly should resolve the project, inspect its repository state, verify that the deployment target is safe and known, run the configured checks, repair authentication only when needed, deploy, verify the result, and report clearly.

On `set-free`, ordinary deployment steps may proceed without repeated prompts when policy allows, but hard safety stops remain in force.

## Core Flow

```text
resolve project
    ↓
inspect repository
    ↓
verify intended branch/ref
    ↓
check repository cleanliness/divergence
    ↓
run configured checks
    ↓
verify deployment provider
    ↓
verify provider authentication
    ↓
verify project linkage
    ↓
prepare deployment
    ↓
deploy
    ↓
collect deployment URL/status
    ↓
verify deployment health
    ↓
report result
```

## Project Resolution

Interly should maintain or derive a bounded project registry rather than accept arbitrary filesystem paths for deployment.

Each deployable project should resolve to a schema similar to:

```yaml
name: interly
repo_path: C:\path\to\interly
production_branch: main
provider: vercel
project_link: known
checks:
  - pytest -p no:cacheprovider
  - ruff check src tests packaging
deploy_targets:
  preview: allowed
  production: allowed
```

The exact storage format is implementation-defined. Existing Interly configuration patterns should be reused where possible.

## Repository Rules

Before deployment, Interly should:

1. Resolve the exact repository.
2. Confirm the expected production branch, normally `main`.
3. Inspect local working-tree status.
4. Inspect whether the local branch is ahead, behind, or diverged from its remote.
5. Refuse silent production deployment from an unexpected branch.
6. Refuse silent production deployment when uncommitted changes would make the deployed state ambiguous.
7. Report the exact commit SHA intended for deployment.

If GitHub authentication is already valid, Interly should not refresh it unnecessarily.

If GitHub authentication is unavailable or expired, the recovery path may use the existing GitHub CLI authentication flow, including browser/device confirmation where required.

Conceptual fallback:

```text
gh auth status
    ↓ failure
gh auth refresh / login flow
    ↓
user confirms in browser if required
    ↓
resume deployment
```

Authentication recovery is a fallback, not part of the normal happy path.

## Checks

Checks must be project-specific and bounded.

Interly should reuse its existing repository inspection and bounded command-execution model rather than introduce unrestricted shell execution.

A deployment must not proceed to production when a configured required check fails.

The deployment report should distinguish at minimum:

```text
repository check: passed / failed
build: passed / failed / not configured
tests: passed / failed / not configured
typecheck: passed / failed / not configured
lint: passed / failed / not configured
dependency/security check: passed / failed / not configured
```

## Vercel Provider

Initial provider target: Vercel.

Preferred interaction model:

```text
vercel authentication check
    ↓
known project link
    ↓
vercel deploy --prod
```

Interly should prefer the Vercel CLI over GUI automation for normal deployments.

If Vercel authentication is missing, Interly may initiate the supported login/browser flow and let the user complete provider confirmation.

If the local project is not linked to a known Vercel project, Interly must not silently associate it with an arbitrary project. Project linking must resolve to an explicit, known target.

GUI automation should remain an exceptional fallback rather than the primary deployment mechanism.

## Provider Abstraction

The implementation should not hard-wire deployment semantics so deeply that Vercel is the only possible provider forever.

Use a small provider boundary conceptually equivalent to:

```text
provider.status(project)
provider.authenticate(project)
provider.deploy(project, target, ref)
provider.status(deployment)
provider.logs(deployment)
```

Vercel is the first implementation. Cloudflare or other providers can be added later without changing the user-facing command model.

## Permission Model

Deployment actions should reuse Interly's existing governance model.

Suggested tool/policy separation:

```text
inspect_deployment_project
run_deployment_checks
prepare_deployment
deploy_project
read_deployment_status
read_deployment_logs
rollback_deployment
```

Suggested default behaviour:

- inspection: ordinary governed action
- checks: ordinary governed action
- preview deployment: ordinary governed action
- production deployment: policy-aware governed action
- rollback: separate governed action
- destructive provider/project relinking: explicit confirmation required

`set-free` may suppress repeated prompts for ordinary actions when policy permits, but it must not bypass hard safety conditions.

## Hard Stops

The following should stop automatic production deployment even during `set-free`:

1. Unknown repository.
2. Unknown deployment provider.
3. Unknown or ambiguous production target.
4. Unexpected branch or ref.
5. Ambiguous uncommitted local state.
6. Diverged repository state that makes the intended commit unclear.
7. Required checks failing.
8. Provider authentication that cannot be repaired safely.
9. Unknown Vercel project linkage.
10. Deployment response that does not identify the deployed version clearly.

Hard stops should produce a concise explanation and the minimum user action required to continue.

## Secrets and Authentication

Interly may invoke authenticated CLIs but should not expose raw credentials to the model or audit log.

Reports should contain states such as:

```text
github: authenticated
vercel: authenticated
project: linked
```

and never raw values such as access tokens, cookies, API keys, or credential files.

Existing Interly privacy rules for sensitive local data remain authoritative.

## Audit Requirements

Deployment operations should be auditable using the existing Interly JSONL audit model.

Record non-sensitive metadata such as:

```text
project
environment
provider
branch
commit SHA
checks requested
checks result
deployment start/end status
deployment identifier or public URL when safe
rollback target when used
```

Do not record raw authentication material or sensitive command output.

## Deployment Verification

A successful provider command is not automatically a successful release.

After deployment, Interly should collect what the provider exposes and verify at least:

1. Provider reports a completed deployment.
2. Deployment maps to the expected project.
3. Deployment maps to the expected commit/ref where provider metadata allows it.
4. Public deployment URL is reachable when a public URL exists.
5. Basic health/runtime status does not immediately report a known failure.

Verification should remain bounded. It does not need to become a full synthetic monitoring platform in the first implementation.

## Rollback

Rollback is a later but expected part of the deployment surface.

A rollback must target a previously known successful deployment/version rather than inventing a ref.

Conceptual command:

```text
rollback interly to previous successful deployment
```

Rollback should remain a distinct permission/tool from deploy.

## Minimal First Implementation

The first coherent deployment slice should do only this:

```text
1. resolve a registered project
2. verify main
3. inspect repository cleanliness and remote relation
4. run configured checks
5. verify Vercel CLI authentication
6. verify known Vercel project linkage
7. deploy production with the Vercel CLI
8. capture deployment URL/status
9. perform bounded verification
10. write an audit record and user-facing report
```

Do not add arbitrary remote-shell capability, generic command execution, broad GUI control, or speculative multi-provider architecture solely to support this feature.

## Example Session

```text
You: set-free 30
You: please deploy interly to production

Interly:
Project: interly
Repository: clean
Branch: main
Commit: <sha>
Checks: passed
GitHub: authenticated
Vercel: authenticated
Target: known production project
Deployment: completed
URL: <deployment-url>
Verification: healthy
```

Failure example:

```text
You: deploy intermail to production

Interly:
Deployment stopped.
Reason: local main is behind origin/main.
Required action: update the repository and retry.
```

## Non-Goals

This plan does not authorize or require:

- changing Interly's existing permission semantics
- replacing current audit/privacy controls
- unrestricted shell access
- arbitrary filesystem deployment
- automatic project relinking
- automatic credential extraction
- changing GitHub repository history
- modifying application code during deployment
- implementing a general CI/CD platform
- adding deployment providers that are not needed yet

## Future MCP Direction

If Interly later exposes deployment through MCP, the MCP surface should call the same internal governed deployment primitives rather than creating a second execution path.

Conceptually:

```text
ChatGPT / MCP client
        ↓
Interly governed deployment tool
        ↓
existing permission + policy + audit engine
        ↓
repository checks
        ↓
provider adapter
        ↓
deployment + verification
```

MCP should therefore be an external control surface over Interly's existing trust model, not a bypass around it.

## Implementation Handoff Rule

Before implementing this plan, inspect the latest `main`, recent commits, active branches, open pull requests, issues, roadmap/work-queue files, and current repository/developer tooling. Reconcile this document with any newer work before changing code.

Prefer the smallest coherent deployment slice. If repository state or provider behaviour makes a safe implementation unclear, stop rather than forcing deployment automation.
