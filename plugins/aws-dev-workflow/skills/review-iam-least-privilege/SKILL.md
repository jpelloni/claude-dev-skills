---
name: review-iam-least-privilege
description: Review AWS IAM policies and role definitions in-repo for least-privilege issues across JSON/YAML policies, CloudFormation/SAM AWS::IAM::*, and Terraform aws_iam_*, then report ranked findings with suggested tighter patches. Apply patches only when the user asks. Use when the user asks to review IAM, tighten permissions, check least privilege, audit trust/policies, or invokes /review-iam-least-privilege.
---

# Review IAM for least privilege

Reviews AWS IAM definitions in the repository (docs and IaC in-tree only — no live account
scanning) and produces a ranked findings report with suggested tighter policy patches.
Project-specific rules in `CLAUDE.md` or existing IAM conventions always override the
defaults here.

**Do not auto-apply patches.** Propose revised JSON or Terraform HCL, then ask before writing
files. Never silently change production IAM.

## 1. Find the target files

- If the user named files or a directory, use those and skip the rest of this step.
- Otherwise find the base branch: the ref the user gives, or
  `git symbolic-ref --short refs/remotes/origin/HEAD`. Then collect everything changed against
  it, including uncommitted and untracked work:

  ```bash
  git diff --name-only --diff-filter=ACMR --merge-base <base>
  git ls-files --others --exclude-standard
  ```

- **Include** IAM-related paths from that set (or from the user-named scope):
  - Policy documents: `*policy*.json`, `*policy*.yaml`, `*policy*.yml`, and files that clearly
    contain an IAM policy document (`Version` + `Statement`, or `Effect`/`Action`/`Resource`).
  - CloudFormation / SAM: templates (`.yaml` / `.yml` / `.json` / `.template`) that define
    `AWS::IAM::Role`, `AWS::IAM::Policy`, `AWS::IAM::ManagedPolicy`,
    `AWS::IAM::RolePolicy`, `AWS::IAM::InstanceProfile`, or inline `Policies` /
    `AssumeRolePolicyDocument` on other resources.
  - Terraform: `*.tf` / `*.tf.json` containing `aws_iam_role`, `aws_iam_policy`,
    `aws_iam_role_policy`, `aws_iam_role_policy_attachment`, `aws_iam_policy_attachment`,
    `aws_iam_user_policy`, `aws_iam_group_policy`, `aws_iam_policy_document`,
    `aws_iam_instance_profile`, inline `assume_role_policy`, or policy JSON via heredoc /
    `jsonencode` / `templatefile`.
- Skip unrelated churn (app source, tests, lockfiles) unless it embeds an IAM document.
- If nothing IAM-related is found, say so and stop.

## 2. Learn project IAM conventions

Read these before scoring findings:

- **Project rules:** `CLAUDE.md` and any README / `docs/**` section on IAM, security, or
  infrastructure. Note required conditions, forbidden wildcards, approved managed policies,
  naming, or "never attach AdministratorAccess" style rules.
- **Existing patterns:** one or two nearby IAM roles/policies that already look tight. Prefer
  matching their condition keys, resource ARNs, and action granularity when suggesting
  patches.
- Prefer project rules over generic AWS advice when they conflict.

## 3. Analyze each target

For every IAM resource or policy document found, extract the effective statements (including
trust / assume-role policies and inline policies) and flag issues. Rank each finding
**critical**, **warn**, or **note**.

At least cover:

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `Action: "*"` or service-wide wildcards (`s3:*`, `iam:*`) where a short action list fits | critical / warn | Grants far more than the workload needs; blast radius on compromise |
| `Resource: "*"` without a strong justification or compensating `Condition` | critical / warn | Cross-account or cross-bucket impact; hard to reason about |
| Missing `Condition` on sensitive actions (`sts:AssumeRole`, `iam:PassRole`, object get/put, KMS decrypt, secrets reads) | warn / critical | Removes caller/context constraints attackers abuse |
| `Principal: "*"` or public / unexpected trust principals | critical | Public or overly trustable roles |
| Overbroad `sts:AssumeRole` trust (wildcard principal, missing `ExternalId` / org / source-ARN conditions when the project uses them) | critical / warn | Role assumption from unintended accounts or services |
| `iam:PassRole` without resource and/or condition constraints | critical / warn | Privilege escalation into stronger roles |
| Admin-style managed policy attachments (`AdministratorAccess`, `PowerUserAccess`, broad `*FullAccess`) on application or CI roles | critical | Turns a service role into an account-admin path |
| Terraform-specific: same issues inside `aws_iam_policy_document` data sources, JSON heredocs, `jsonencode({...})`, and `templatefile(...)` policy templates | same as above | Easy to miss when only scanning standalone JSON files |

**Terraform depth (portfolio priority):** always expand and review:

- `data "aws_iam_policy_document"` statements (`actions`, `resources`, `principals`,
  `condition` blocks).
- Inline `assume_role_policy` / `policy` arguments (string JSON, heredoc, `jsonencode`).
- `aws_iam_*_policy_attachment` and `managed_policy_arns` for admin-style ARNs.
- Variables or locals that only become wildcards at apply time — call them out as
  needs-human-review when the concrete value isn't in-repo.

**Out of scope for this skill:** Azure/Entra IAM, live AWS Access Analyzer / account scanning,
deep CDK L2 construct trees beyond readable policy JSON/HCL already present in the tree, and
applying patches without confirmation.

## 4. Report findings

Produce a ranked report. For each finding include:

1. **Location** — file path plus resource name (CFN logical ID, Terraform resource address, or
   policy sid/name).
2. **Severity** — critical / warn / note.
3. **Why it hurts** — one or two sentences on the risk.
4. **Tighter alternative** — concrete replacement snippet (JSON and/or Terraform HCL) that
   narrows actions, resources, principals, and adds conditions where appropriate.

Group by severity (critical first). If a statement looks intentionally broad (break-glass,
org-admin), mark it **note** / needs-human-review rather than forcing a rewrite.

## 5. Suggest patches (ask before applying)

- Propose revised policy JSON and/or Terraform HCL for each actionable finding.
- Keep suggestions idiomatic to the file's format (CFN intrinsic functions, SAM, Terraform
  `aws_iam_policy_document`, etc.).
- Ask the user which findings to apply. Write files only for the ones they confirm.
- Never silently edit IAM in the working tree.

## 6. Hand back

Summarize:

- Counts by severity (critical / warn / note).
- Files reviewed; files changed only if patches were applied.
- Residual risks and needs-human-review items (unknown principals, unresolved variables,
  managed policies that may be required by a service, anything that needs an account-side
  check).
- Remind that this review is in-repo only; Access Analyzer or IAM Access Advisor can catch
  unused permissions in a live account when the user wants that next step outside this skill.
