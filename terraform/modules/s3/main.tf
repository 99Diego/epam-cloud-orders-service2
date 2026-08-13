variable "bucket_name" {
  type        = string
  description = "Nombre del bucket S3"
}

variable "lambda_arn" {
  type        = string
  description = "ARN de la función Lambda a activar"
}

resource "aws_s3_bucket" "orders_bucket" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.orders_bucket.id

  lambda_function {
    lambda_function_arn = var.lambda_arn
    events              = ["s3:ObjectCreated:*"]
  }
}

output "bucket_arn" {
  value = aws_s3_bucket.orders_bucket.arn
}

output "bucket_id" {
  value = aws_s3_bucket.orders_bucket.id
}
