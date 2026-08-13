import json
import time
import os
import boto3

ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = "us-east-1"

s3 = boto3.client("s3", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)
sqs = boto3.client("sqs", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)


def test_integration_flow():
    print("--- INICIANDO TEST DE INTEGRACIÓN E2E ---")

    # 1. Caso Exitoso (Valid Order)
    valid_order = {
        "order_id": "ORD-TEST-001",
        "customer_id": "CUST-999",
        "items": [{"id": "ITEM-A", "qty": 1}],
        "total": 150.0
    }

    print("[+] Subiendo orden válida a S3...")
    s3.put_object(
        Bucket="orders-inbound",
        Key="valid_order.json",
        Body=json.dumps(valid_order)
    )

    # Esperar procesamiento asíncrono
    time.sleep(3)

    # Verificar DynamoDB
    table = dynamodb.Table("orders")
    response = table.get_item(Key={"order_id": "ORD-TEST-001"})
    
    assert "Item" in response, "ERROR: La orden válida no se guardó en DynamoDB."
    print("✅ Éxito: Orden válida guardada correctamente en DynamoDB.")

    # 2. Caso Fallido (Invalid Order)
    invalid_order = {
        "order_id": "ORD-TEST-BAD",
        "customer_id": "CUST-999",
        "items": [],  # Inválido: lista vacía
        "total": -5.0 # Inválido: <= 0
    }

    print("[+] Subiendo orden inválida a S3...")
    s3.put_object(
        Bucket="orders-inbound",
        Key="invalid_order.json",
        Body=json.dumps(invalid_order)
    )

    time.sleep(3)

    # Verificar SQS DLQ
    queue_url_response = sqs.get_queue_url(QueueName="orders-dlq")
    queue_url = queue_url_response["QueueUrl"]

    messages_response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=2
    )

    assert "Messages" in messages_response, "ERROR: No se encontró mensaje en la DLQ de SQS."
    
    body = json.loads(messages_response["Messages"][0]["Body"])
    assert "reason" in body, "ERROR: El mensaje en SQS no contiene la razón de falla."
    print(f"✅ Éxito: Orden inválida detectada en DLQ. Razón: {body['reason']}")


if __name__ == "__main__":
    test_integration_flow()
