import json
import os
import urllib.parse
import boto3

# Inicializar clientes
endpoint_url = os.getenv("AWS_ENDPOINT_URL")

s3_client = boto3.client("s3", endpoint_url=endpoint_url)
dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url)
sqs_client = boto3.client("sqs", endpoint_url=endpoint_url)

DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "orders")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")


def validate_order(data: dict) -> tuple[bool, str]:
    """Valida la estructura y tipos de datos del pedido."""
    if not isinstance(data, dict):
        return False, "Payload must be a JSON object"

    order_id = data.get("order_id")
    customer_id = data.get("customer_id")
    items = data.get("items")
    total = data.get("total")

    if not order_id or not isinstance(order_id, str):
        return False, "Invalid or missing 'order_id' (must be a non-empty string)"

    if not customer_id or not isinstance(customer_id, str):
        return False, "Invalid or missing 'customer_id' (must be a non-empty string)"

    if not isinstance(items, list) or len(items) == 0:
        return False, "Invalid or missing 'items' (must be a non-empty list)"

    if not isinstance(total, (int, float)) or total <= 0:
        return False, "Invalid or missing 'total' (must be a number > 0)"

    return True, ""


def lambda_handler(event, context):
    """Manejador principal invocado por eventos de S3."""
    for record in event.get("Records", []):
        bucket_name = record["s3"]["bucket"]["name"]
        object_key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        try:
            # 1. Obtener el archivo desde S3
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)

            # 2. Validar
            is_valid, reason = validate_order(data)

            if is_valid:
                # 3. Guardar en DynamoDB
                table = dynamodb.Table(DYNAMODB_TABLE_NAME)
                table.put_item(Item=data)
                print(f"Order {data['order_id']} saved successfully to DynamoDB.")
            else:
                # 4. Enviar a SQS DLQ
                send_to_dlq(data, reason)

        except json.JSONDecodeError:
            send_to_dlq({"raw_content": content if 'content' in locals() else ""}, "Invalid JSON format")
        except Exception as e:
            print(f"Unhandled error processing {object_key}: {str(e)}")
            send_to_dlq({"file_key": object_key}, f"System error: {str(e)}")

    return {"statusCode": 200, "body": json.dumps("Processing complete")}


def send_to_dlq(payload: dict, reason: str):
    """Helper para enviar órdenes fallidas a la cola SQS DLQ."""
    dlq_payload = {
        "reason": reason,
        "original_payload": payload
    }

    if SQS_QUEUE_URL:
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(dlq_payload)
        )
        print(f"Invalid order sent to DLQ. Reason: {reason}")
    else:
        print(f"Error: SQS_QUEUE_URL not set. Couldn't send DLQ message: {reason}")
