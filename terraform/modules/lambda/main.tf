variable "function_name" { type = string }
variable "sqs_queue_url" { type = string }
variable "dynamodb_table_name" { type = string }
variable "s3_bucket_arn" { type = string }

# Compilar código python en un zip
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../../src/lambda_function"
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_iam_role" "lambda_role" {
  name = "${var.function_name}_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_lambda_function" "order_processor" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = var.function_name
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime          = "python3.10"

  environment {
    variables = {
      DYNAMODB_TABLE_NAME = var.dynamodb_table_name
      SQS_QUEUE_URL       = var.sqs_queue_url
    }
  }
}

# Permiso para que S3 pueda invocar a Lambda
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.order_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.s3_bucket_arn
}

output "lambda_arn" {
  value = aws_lambda_function.order_processor.arn
}
