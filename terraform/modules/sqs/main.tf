variable "queue_name" {
  type = string
}

resource "aws_sqs_queue" "dlq" {
  name = var.queue_name
}

output "queue_url" {
  value = aws_sqs_queue.dlq.id
}

output "queue_arn" {
  value = aws_sqs_queue.dlq.arn
}
