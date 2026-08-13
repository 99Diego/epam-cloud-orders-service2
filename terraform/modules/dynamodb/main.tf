variable "table_name" {
  type = string
}

resource "aws_dynamodb_table" "orders_table" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "order_id"

  attribute {
    name = "order_id"
    type = "S"
  }
}

output "table_name" {
  value = aws_dynamodb_table.orders_table.name
}

output "table_arn" {
  value = aws_dynamodb_table.orders_table.arn
}
