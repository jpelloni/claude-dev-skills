---
name: review-terraform-security
description: Review in-repo Terraform for security issues beyond IAM least privilege — public network exposure, unencrypted or public data stores, missing deletion protection and backups, plaintext secrets, and weak instance metadata — then report ranked findings with suggested HCL patches. Apply patches only when the user asks. Use when the user asks to review Terraform security, security groups, public buckets, encryption, IMDSv2, or invokes /review-terraform-security.
---

# Review Terraform security

Reviews Terraform (and OpenTofu) in the repository and produces a ranked findings report
with suggested tighter HCL. Scope is files on disk — no live account scanning, no
`terraform plan` or `terraform apply` against AWS. Project-specific rules in `CLAUDE.md` or
existing infrastructure conventions always override the defaults here.

**Do not auto-apply patches.** Propose revised HCL, then ask before writing files. Never
silently change infrastructure.

**IAM least privilege is out of scope.** Wildcards, trust policies, `iam:PassRole`, and
admin managed-policy attachments belong to `/aws-dev-workflow:review-iam-least-privilege`.
This skill still flags exposure that an IAM review misses: a bucket that is world-readable,
a database that is publicly reachable, a security group that opens SSH to the internet.
If a file is only `aws_iam_*` / `data.aws_iam_policy_document`, say so and stop — that
review is the other skill.

## 1. Find the target files

- If the user named files or a directory, use those and skip the rest of this step.
- Otherwise find the base branch: the ref the user gives, or
  `git symbolic-ref --short refs/remotes/origin/HEAD`. Then collect everything changed against
  it, including uncommitted and untracked work:

  ```bash
  git diff --name-only --diff-filter=ACMR --merge-base <base>
  git ls-files --others --exclude-standard
  ```

- **Include** from that set (or from the user-named scope):
  - `*.tf` and `*.tf.json` that declare or configure network, storage, data, compute,
    load-balancing, logging, or secret resources.
  - `*.tfvars` / `*.tfvars.json` and `terraform.tfvars` when they set CIDRs, public flags,
    passwords, or other security-relevant inputs.
  - Local module sources (`source = "./modules/..."` or `"../..."`) referenced by an included
    file. Read those module files even if they are unchanged.
  - `terragrunt.hcl` only when it sets inputs that change a pattern in section 3.
- Skip lockfiles, READMEs, app source, and pure IAM files. If a file mixes IAM and other
  resources, review only the non-IAM resources here and mention that IAM statements were
  left for the other skill.
- If nothing security-relevant is found, say so and stop.

## 2. Learn project conventions

Read these before scoring findings:

- **Project rules:** `CLAUDE.md` and any README / `docs/**` section on infrastructure,
  security, encryption, tagging, or environments. Note required tags, a required KMS key,
  "no public buckets", environment naming (`prod` vs `dev`), and anything the project
  explicitly allows (a public website bucket, a public HTTPS load balancer).
- **Existing patterns:** one or two nearby resources that already look tight (a locked-down
  security group, a bucket with a public-access block and encryption). Match that style in
  suggested patches — reuse an existing key alias instead of inventing a new KMS key.
- Prefer project rules over generic AWS advice when they conflict.
- Treat names and paths as hints: `prod`, `production`, and state backends raise severity;
  `dev`, `test`, `sandbox`, and `example` lower a missing backup or deletion-protection
  finding to **note** unless the project says otherwise.

## 3. Analyze each target

Read the whole resource, not only the diff hunk, so encryption or a public-access block set
in an unchanged block is not reported as missing. Resolve `local`s, `variable` defaults, and
module inputs that are in the tree. Expand `dynamic` blocks and `for` expressions enough to
see CIDRs and booleans.

For a module whose source is a registry or a remote git URL not checked out here, review
only the arguments the caller passes. Mark the module body as needs-human-review.

Rank each finding **critical**, **warn**, or **note**.

### Network exposure

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| Ingress from `0.0.0.0/0` or `::/0` on 22, 3389, or all ports (`-1`, `0-65535`) via `aws_security_group`, `aws_security_group_rule`, `aws_vpc_security_group_ingress_rule`, or `aws_network_acl` | critical | Admin protocols reachable from the internet |
| Ingress from `0.0.0.0/0` or `::/0` on data ports (3306, 5432, 1433, 6379, 9200, 9300, 27017, 11211, 5900) | critical | Data store reachable without the VPC path |
| `publicly_accessible = true` on `aws_db_instance`, `aws_rds_cluster`, Redshift, or OpenSearch / Elasticsearch | critical | Bypasses private networking |
| `0.0.0.0/0` on 80/443 (or `internal = false`) where the name, docs, or peer resources say the service is internal | warn | Accidental public entry point |
| Public 80/443 on a load balancer or website the project documents as public | note | Often intentional; confirm, do not rewrite |
| `associate_public_ip_address = true` or an `aws_eip` on a workload the project treats as private | warn | Direct internet path; private subnet plus SSM or a load balancer is the usual fit |
| Egress `0.0.0.0/0` on all ports | note | Default and often required. Mention only when the project forbids it |

### S3 exposure and state

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `acl` of `public-read-write` or `authenticated-read` | critical | Anyone, or any AWS principal, can write objects |
| `acl` of `public-read` on a bucket that is not a documented website or asset bucket | warn | Objects readable without credentials |
| Missing `aws_s3_bucket_public_access_block`, or any of `block_public_acls`, `block_public_policy`, `ignore_public_acls`, `restrict_public_buckets` set to false | warn | ACLs or a bucket policy can make the bucket public. If account-level Block Public Access is not in the repo, mark that needs-human-review instead of claiming the bucket is safe |
| Bucket policy with `Principal = "*"` granting `s3:GetObject`, `s3:PutObject`, or `s3:*` (exposure, not IAM least privilege) | critical, or note when website hosting is explicit in the same module | Anonymous read or write |
| Terraform state backend bucket missing versioning, encryption, or a public-access block | critical | State files hold secrets and resource IDs |
| Versioning suspended on a bucket that holds state or user data | warn | Deletes and overwrites are not recoverable |

### Encryption

Flag an explicit `false`. Flag an omitted setting when the provider default for that
resource is unencrypted, or when peer resources in the repo use a customer-managed key and
this one does not. Do not flag an omitted block when current AWS defaults already encrypt
and the project does not require a CMK.

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `storage_encrypted = false` (or omitted, where that defaults to false) on RDS, DocumentDB, Neptune, or Redshift | critical on prod names, otherwise warn | Snapshots and disks readable if storage is copied |
| `aws_ebs_volume` or a launch-template / instance root block device with `encrypted = false` | warn | Volume snapshots leak data |
| `aws_efs_file_system` `encrypted = false`, ElastiCache `at_rest_encryption_enabled = false`, or OpenSearch `encrypt_at_rest` disabled | warn | Data store at rest without encryption |
| SSE missing on an S3 bucket while peer buckets set `aws_s3_bucket_server_side_encryption_configuration` | warn | Inconsistent bar; match the peer algorithm and key |
| `aws_lb_listener` on HTTP port 80 with no redirect listener to HTTPS | warn | Credentials and cookies on the wire |
| ElastiCache `transit_encryption_enabled = false`, or OpenSearch `enforce_https = false` / an obsolete `tls_security_policy` | warn | In-transit traffic to the data store |

### Deletion protection and backups

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| `deletion_protection = false` on prod RDS, `aws_lb`, or `aws_dynamodb_table` | warn | One apply can destroy the system of record |
| `skip_final_snapshot = true` or `backup_retention_period = 0` on RDS | warn | No recovery point after delete |
| DynamoDB `point_in_time_recovery` disabled on a table that looks like a system of record | warn | Point restore is unavailable |
| The same gaps on `dev` / `test` / `sandbox` names | note | Real, but usually accepted |

### Credentials and instance metadata

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| A password, secret, access key, or `secret_string` written as a literal in a resource, variable default, `locals`, or tfvars | critical | Secret lands in git and in plan output |
| An output of a secret or connection string without `sensitive = true` | warn | Value shows up in plans and CI logs |
| `metadata_options.http_tokens` omitted or not `"required"` on `aws_instance` or `aws_launch_template` | warn | IMDSv1 lets SSRF steal the instance role |
| `http_put_response_hop_limit` greater than 1 | note | Containers often need 2. Mention it; do not force 1 without a reason |

### Logging

Only compare against what this repo already does. Do not demand a trail, flow log, or
access log that no peer resource has.

| Pattern | Typical severity | Why it hurts |
| ------- | ---------------- | ------------ |
| An `aws_cloudtrail` in the repo with `enable_log_file_validation = false`, or a single-region trail where peers are multi-region | warn | Tampered or incomplete audit trail |
| A VPC with no `aws_flow_log` while other VPCs in the repo have one | warn | No network record for that VPC |
| A load balancer with access logs off while peer load balancers enable them | note | Request logs missing for that one balancer |

### Tags

Flag missing tags only when `CLAUDE.md` or existing resources define a required set. Do not
invent a tag policy. Severity is **note**.

### Indirection

- A `variable` or `local` whose default is `0.0.0.0/0`, `publicly_accessible = true`, or a
  literal secret is a finding at the variable as well as at the resource.
- `lifecycle { ignore_changes = [...] }` on a security-relevant argument (CIDRs, encryption,
  public access, passwords): **note** / needs-human-review. Drift will not show up in plan.
- Unresolved values (`var.something` with no default and no tfvars in repo): do not guess.
  Report needs-human-review and quote the argument name.

**Out of scope:** IAM least privilege (other skill), Azure and GCP, live AWS config or
Security Hub, remote module bodies not in the tree, and applying patches without
confirmation. Do not run `terraform apply`. Do not treat `tfsec`, Trivy, or Checkov output
as a substitute for this report; they can corroborate a finding, not replace the reading.

## 4. Report findings

Produce a ranked report. For each finding include:

1. **Location** — file path plus resource address (`aws_security_group.api`, including
   `count` / `for_each` key when it is visible).
2. **Severity** — critical / warn / note.
3. **Why it hurts** — one or two sentences on the risk.
4. **Tighter alternative** — concrete HCL that narrows the CIDR, sets the boolean, or adds
   the missing companion resource. Prefer a reference to an existing KMS key, log bucket, or
   VPC in the repo over inventing new ones.

Group by severity (critical first). If a public listener, public bucket, or open egress is
documented or matches a peer that is clearly intentional, mark it **note** /
needs-human-review rather than forcing a rewrite.

## 5. Suggest patches (ask before applying)

- Propose revised HCL for each actionable finding, idiomatic to the file (separate
  `aws_s3_bucket_*` resources vs. inline blocks — match what the file already uses).
- A fix that needs a new resource (public-access block, HTTPS redirect, flow log) is still
  a suggestion. Call out that it is a new resource and ask before adding it.
- Ask the user which findings to apply. Write files only for the ones they confirm.
- Never silently edit Terraform in the working tree.

## 6. Hand back

Summarize:

- Counts by severity (critical / warn / note).
- Files reviewed; files changed only if patches were applied.
- Residual risks and needs-human-review items: unresolved variables, remote module bodies,
  account-level S3 Block Public Access or EBS default encryption that is not in the repo,
  security group rules that may be attached outside this module.
- IAM findings, if any were seen, deferred to
  `/aws-dev-workflow:review-iam-least-privilege`.
- Remind that this review is in-repo only. Account-level services (Config, Security Hub,
  Access Analyzer) are a separate step when the user wants them.
