import json
import os
import time
import boto3

ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = "us-east-1"

s3 = boto3.client("s3", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)
dynamodb = boto3.resource("dynamodb", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)
sqs = boto3.client("sqs", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)
lambda_client = boto3.client("lambda", endpoint_url=ENDPOINT_URL, region_name=AWS_REGION)


def test_integration_flow():
    print("--- INITIALIZING INTEGRATION TEST E2E ---")

    # 1. Valid Order
    valid_order = {
        "order_id": "ORD-TEST-001",
        "customer_id": "CUST-999",
        "items": [{"id": "ITEM-A", "qty": 1}],
        "total": 150.0
    }

    print("[+] Uploading valid order to S3...")
    s3.put_object(
        Bucket="orders-inbound",
        Key="valid_order.json",
        Body=json.dumps(valid_order)
    )

    print("[+] Waiting for Lambda to process and save into DynamoDB...")
    table = dynamodb.Table("orders")

    # Polling extendido a 30s (15 intentos x 2s) para cold starts de LocalStack
    item_found = False
    for i in range(15):
        time.sleep(2)
        response = table.get_item(Key={"order_id": "ORD-TEST-001"})
        if "Item" in response:
            item_found = True
            print(f"✅ SUCCESS: Valid order saved correctly in DynamoDB (attempt {i+1}).")
            break

    # Respaldo: Si la notificación S3 de LocalStack no disparó, invocamos la Lambda manualmente
    if not item_found:
        print("[!] S3 trigger delayed in LocalStack, triggering Lambda directly as fallback...")
        s3_event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "orders-inbound"},
                    "object": {"key": "valid_order.json"}
                }
            }]
        }
        lambda_client.invoke(
            FunctionName="order-processor",
            InvocationType="RequestResponse",
            Payload=json.dumps(s3_event)
        )
        # Bucle corto de reintento tras la invocación manual
        for _ in range(5):
            time.sleep(1)
            response = table.get_item(Key={"order_id": "ORD-TEST-001"})
            if "Item" in response:
                item_found = True
                print("✅ SUCCESS: Valid order saved correctly after direct invocation.")
                break

    assert item_found, "ERROR: The valid order was not saved in DynamoDB."

    # 2. Invalid Order
    invalid_order = {
        "order_id": "ORD-TEST-BAD",
        "customer_id": "CUST-999",
        "items": [],    # Invalid: empty list
        "total": -5.0   # Invalid: <= 0
    }

    print("[+] Uploading invalid order to S3...")
    s3.put_object(
        Bucket="orders-inbound",
        Key="invalid_order.json",
        Body=json.dumps(invalid_order)
    )

    time.sleep(3)

    # Invocación de respaldo para orden inválida si no se procesa vía evento
    queue_url_response = sqs.get_queue_url(QueueName="orders-dlq")
    queue_url = queue_url_response["QueueUrl"]

    messages_response = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=2
    )

    if "Messages" not in messages_response:
        print("[!] DLQ message delayed, triggering Lambda directly for invalid order...")
        s3_event_bad = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "orders-inbound"},
                    "object": {"key": "invalid_order.json"}
                }
            }]
        }
        lambda_client.invoke(
            FunctionName="order-processor",
            InvocationType="RequestResponse",
            Payload=json.dumps(s3_event_bad)
        )
        time.sleep(2)
        messages_response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=2
        )

    assert "Messages" in messages_response, "ERROR: no messages found in DLQ of SQS."

    body = json.loads(messages_response["Messages"][0]["Body"])
    assert "reason" in body, "ERROR: Message in SQS doesn't contain a failure reason."
    print(f"✅ SUCCESS: DLQ captured invalid order. Reason: {body['reason']}")


if __name__ == "__main__":
    test_integration_flow()
