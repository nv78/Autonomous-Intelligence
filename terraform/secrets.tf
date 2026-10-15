resource "aws_secretsmanager_secret" "backend" {
  name = "${var.project_name}-${var.environment}-backend-secrets"
}

resource "aws_secretsmanager_secret_version" "backend" {
  secret_id = aws_secretsmanager_secret.backend.id
  secret_string = jsonencode({
    JWT_SECRET_KEY              = var.jwt_secret_key
    DB_PASSWORD                 = var.db_password
    ANTHROPIC_API_KEY           = var.anthropic_api_key
    OPENAI_API_KEY              = var.openai_api_key
    STRIPE_SECRET_KEY           = var.stripe_secret_key
    STRIPE_WEBHOOK_SECRET       = var.stripe_webhook_secret
    PROVIDER_KEY_ENCRYPTION_KEY = var.provider_key_encryption_key
    GOOGLE_CLIENT_SECRET        = var.google_client_secret
    SLACK_CLIENT_SECRET         = var.slack_client_secret
    ELEVENLABS_API_KEY          = var.elevenlabs_api_key
    RECALL_API_KEY              = var.recall_api_key
    TAVUS_API_KEY               = var.tavus_api_key
    PILOT_SLACK_WEBHOOK_URL     = var.pilot_slack_webhook_url
    SMTP_URL                    = var.smtp_url
  })
}
