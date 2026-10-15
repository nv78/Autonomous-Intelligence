# AI coworker: private storage for twin files, its config, and the
# background worker that runs responsibilities and sends approved actions.

variable "backend_url" {
  description = "Public https URL of the backend (OAuth callbacks and webhooks), e.g. https://chat.ourogen.ai"
  type        = string
  default     = ""
}

variable "coworker_model" {
  type    = string
  default = "claude-opus-5-5"
}

variable "coworker_effort" {
  type    = string
  default = "medium"
}

variable "coworker_enforce_plans" {
  description = "\"1\" to enforce coworker plan limits (requires the Stripe coworker prices)"
  type        = string
  default     = "0"
}

variable "coworker_worker_interval" {
  description = "Seconds between worker passes"
  type        = number
  default     = 60
}

variable "slack_client_id" {
  type    = string
  default = ""
}

variable "tavus_replica_id" {
  type    = string
  default = ""
}

variable "stripe_price_coworker" {
  type    = string
  default = ""
}

variable "stripe_price_coworker_calls" {
  type    = string
  default = ""
}

variable "stripe_price_coworker_team" {
  type    = string
  default = ""
}

variable "pilot_booking_url" {
  type    = string
  default = ""
}

variable "pilot_admin_emails" {
  description = "Comma-separated emails allowed to review pilot applications"
  type        = string
  default     = ""
}

variable "slack_client_secret" {
  type      = string
  sensitive = true
  default   = ""
}

variable "elevenlabs_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "recall_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "tavus_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "pilot_slack_webhook_url" {
  type      = string
  sensitive = true
  default   = ""
}

locals {
  coworker_environment = [
    { name = "BACKEND_URL", value = var.backend_url },
    { name = "COWORKER_MODEL", value = var.coworker_model },
    { name = "COWORKER_EFFORT", value = var.coworker_effort },
    { name = "COWORKER_ENFORCE_PLANS", value = var.coworker_enforce_plans },
    { name = "GOOGLE_COWORKER_REDIRECT_URI", value = "${var.backend_url}/api/coworker/connections/google/callback" },
    { name = "SLACK_CLIENT_ID", value = var.slack_client_id },
    { name = "SLACK_REDIRECT_URI", value = "${var.backend_url}/api/coworker/connections/slack/callback" },
    { name = "TAVUS_REPLICA_ID", value = var.tavus_replica_id },
    { name = "STRIPE_PRICE_COWORKER", value = var.stripe_price_coworker },
    { name = "STRIPE_PRICE_COWORKER_CALLS", value = var.stripe_price_coworker_calls },
    { name = "STRIPE_PRICE_COWORKER_TEAM", value = var.stripe_price_coworker_team },
    { name = "PILOT_BOOKING_URL", value = var.pilot_booking_url },
    { name = "PILOT_ADMIN_EMAILS", value = var.pilot_admin_emails },
    { name = "TWIN_S3_BUCKET", value = aws_s3_bucket.twin.bucket },
    { name = "TWIN_S3_SSE", value = "aws:kms" },
    { name = "AWS_REGION", value = var.aws_region },
  ]

  coworker_secrets = [
    for name in ["SLACK_CLIENT_SECRET", "ELEVENLABS_API_KEY", "RECALL_API_KEY", "TAVUS_API_KEY", "PILOT_SLACK_WEBHOOK_URL"] :
    { name = name, valueFrom = "${aws_secretsmanager_secret.backend.arn}:${name}::" }
  ]
}

# ── Twin storage: voice/video samples and consent recordings ────────────────

resource "aws_s3_bucket" "twin" {
  bucket_prefix = "${var.project_name}-${var.environment}-twin-"
}

resource "aws_s3_bucket_public_access_block" "twin" {
  bucket                  = aws_s3_bucket.twin.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "twin" {
  bucket = aws_s3_bucket.twin.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "twin" {
  bucket = aws_s3_bucket.twin.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "twin" {
  bucket = aws_s3_bucket.twin.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Old versions exist only to recover from accidental overwrites. Revoking a
# twin deletes every version immediately; this expires any stragglers.
resource "aws_s3_bucket_lifecycle_configuration" "twin" {
  bucket = aws_s3_bucket.twin.id
  rule {
    id     = "expire-noncurrent"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration {
      noncurrent_days = 7
    }
  }
}

resource "aws_s3_bucket_policy" "twin_tls_only" {
  bucket = aws_s3_bucket.twin.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.twin.arn, "${aws_s3_bucket.twin.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.twin]
}

resource "aws_iam_role_policy" "ecs_task_twin" {
  name = "${var.project_name}-ecs-task-twin"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:DeleteObjectVersion"]
        Resource = "${aws_s3_bucket.twin.arn}/twin/*"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:ListBucket", "s3:ListBucketVersions"]
        Resource = aws_s3_bucket.twin.arn
      },
    ]
  })
}

# ── Background worker ───────────────────────────────────────────────────────

resource "aws_cloudwatch_log_group" "coworker_worker" {
  name              = "/ecs/${var.project_name}-coworker-worker"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "coworker_worker" {
  family                   = "${var.project_name}-coworker-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name        = "coworker-worker"
    image       = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
    essential   = true
    entryPoint  = ["python", "-m", "coworker.worker", "--interval", tostring(var.coworker_worker_interval)]
    environment = local.backend_environment
    secrets     = local.backend_secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.coworker_worker.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "worker"
      }
    }
  }])
}

# Exactly one worker: responsibilities are idempotent per run key, but one
# task keeps sends and nudges in a predictable order.
resource "aws_ecs_service" "coworker_worker" {
  name            = "${var.project_name}-coworker-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.coworker_worker.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = true
  }

  lifecycle {
    ignore_changes = [task_definition]
  }
}
