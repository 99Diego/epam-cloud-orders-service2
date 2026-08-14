import decimal
import json
import os
import urllib.parse
import boto3

DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "orders")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")


def resolve_endpoint_url():
    """Determina el endpoint correcto para LocalStack en cualquier entorno CI/Docker."""
    # 1. Si LocalStack inyectó LOCALSTACK_HOSTNAME (dentro del contenedor de la Lambda)
    localstack_host = os.getenv("LOCALSTACK_HOSTNAME")
    if localstack_host:
        return f"http://{localstack_host}:4566"

    # 2. Si viene por variable explícita AWS_ENDPOINT_URL
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    if endpoint_url:
        return endpoint_url

    # 3. Fallback por defecto
    return "http://localhost:4566"


def get_boto3_client(service_name):
    """Obtiene cliente de boto3 usando el endpoint resuelto."""
    endpoint_url = resolve_endpoint_url()
    return boto3.client(service_name, endpoint_url=endpoint_url)


def get_boto3_resource(service_name):
    """Obtiene recurso de boto3 usando el endpoint resuelto."""
    endpoint_url = resolve_endpoint_url()
    return boto3.resource(service_name, endpoint_url=endpoint_url)


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

    if not isinstance(total, (int, float, decimal.Decimal)) or total <= 0:
        return False, "Invalid or missing 'total' (must be a number > 0)"

    return True, ""


def lambda_handler(event, context):
    """Manejador principal invocado por eventos de S3."""
    print(f"Received event: {json.dumps(event)}")

    s3_client = get_boto3_client("s3")
    dynamodb = get_boto3_resource("dynamodb")

    for record in event.get("Records", []):
        bucket_name = record["s3"]["bucket"]["name"]
        object_key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        try:
            print(f"Fetching object {object_key} from bucket {bucket_name}...")
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            content = response["Body"].read().decode("utf-8")
            
            # Convierte los floats en Decimal para compatibilidad directa con DynamoDB
            data = json.loads(content, parse_float=decimal.Decimal)

            is_valid, reason = validate_order(data)

            if is_valid:
                table = dynamodb.Table(DYNAMODB_TABLE_NAME)
                table.put_item(Item=data)
                print(f"Order {data['order_id']} saved successfully to DynamoDB.")
            else:
                send_to_dlq(data, reason)

        except json.JSONDecodeError:
            send_to_dlq({"raw_content": content if 'content' in locals() else ""}, "Invalid JSON format")
        except Exception as e:
            print(f"Unhandled error processing {object_key}: {str(e)}")
            send_to_dlq({"file_key": object_key}, f"System error: {str(e)}")
            raise e

    return {"statusCode": 200, "body": json.dumps("Processing complete")}


def send_to_dlq(payload: dict, reason: str):
    """Helper para enviar órdenes fallidas a la cola SQS DLQ."""
    sqs_client = get_boto3_client("sqs")
    dlq_payload = {
        "reason": reason,
        "original_payload": payload
    }

    if SQS_QUEUE_URL:
        sqs_client.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(dlq_payload, default=str)
        )
        print(f"Invalid order sent to DLQ. Reason: {reason}")
    else:
        print(f"Error: SQS_QUEUE_URL not set. Couldn't send DLQ message: {reason}")
