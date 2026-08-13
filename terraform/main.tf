terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "mock_access_key"
  secret_key                  = "mock_secret_key"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # Si se usa "tflocal", tflocal sobrescribe automáticamente las URLs a LocalStack
}

module "dynamodb" {
  source     = "./modules/dynamodb"
  table_name = "orders"
}

module "sqs" {
  source     = "./modules/sqs"
  queue_name = "orders-dlq"
}

module "lambda" {
  source              = "./modules/lambda"
  function_name       = "order-processor"
  sqs_queue_url       = module.sqs.queue_url
  dynamodb_table_name = module.dynamodb.table_name
  s3_bucket_arn       = "arn:aws:s3:::orders-inbound"
}

module "s3" {
  source      = "./modules/s3"
  bucket_name = "orders-inbound"
  lambda_arn  = module.lambda.lambda_arn
}
