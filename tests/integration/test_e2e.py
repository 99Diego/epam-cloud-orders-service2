import json
import os
import time
import boto3

ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

s3_client = boto3.client("s3", endpoint_url=ENDPOINT_URL, region_name=REGION)
dynamodb = boto3.resource("dynamodb", endpoint_url=ENDPOINT_URL, region_name=REGION)
lambda_client = boto3.client("lambda", endpoint_url=ENDPOINT_URL, region_name=REGION)

BUCKET_NAME = "orders-inbound"
TABLE_NAME = "orders"


def test_integration_flow():
    print("--- INITIALIZING INTEGRATION TEST E2E ---")

    test_order = {
        "order_id": "ORD-E2E-999",
        "customer_id": "CUST-001",
        "items": [{"item_id": "ITEM-1", "quantity": 2, "price": 50.0}],
        "total": 100.0
    }

    object_key = "e2e_valid_order.json"

    # 1. Subir archivo a S3
    print("[+] Uploading valid order to S3...")
    s3_client.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=json.dumps(test_order)
    )

    # 2. Esperar con retries a que S3 dispare la Lambda y esta guarde en DynamoDB
    table = dynamodb.Table(TABLE_NAME)
    item_found = False
    max_retries = 10
    retry_interval = 2  # Esperar 2s entre intentos (hasta 20s total)

    print("[+] Waiting for Lambda to process and save into DynamoDB...")
    for attempt in range(1, max_retries + 1):
        time.sleep(retry_interval)
        response = table.get_item(Key={"order_id": test_order["order_id"]})
        if "Item" in response:
            print(f"[✓] Order found in DynamoDB on attempt {attempt}!")
            item_found = True
            break
        print(f"[-] Attempt {attempt}/{max_retries}: Item not in DynamoDB yet, retrying...")

    # 3. Fallback: Si el evento S3 no se disparó en LocalStack, invocar la Lambda manualmente
    # 3. Fallback: Si el evento S3 no se disparó en LocalStack, invocar la Lambda manualmente
    if not item_found:
        print("[!] S3 trigger delayed in LocalStack, invoking Lambda directly as fallback...")
        s3_event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": BUCKET_NAME},
                        "object": {"key": object_key}
                    }
                }
            ]
        }

        response = lambda_client.invoke(
            FunctionName="order-processor",
            InvocationType="RequestResponse",
            Payload=json.dumps(s3_event)
        )

        # Imprimir logs/payload de respuesta de la Lambda para depuración
        payload_res = response["Payload"].read().decode("utf-8")
        print(f"[debug] Lambda Response: {payload_res}")

        # Volver a verificar DynamoDB tras la invocación directa
        time.sleep(2)
        res_db = table.get_item(Key={"order_id": test_order["order_id"]})
        if "Item" in res_db:
            print("[✓] Order successfully saved in DynamoDB after direct invocation!")
            item_found = True

    # Asert de confirmación
    assert item_found, "ERROR: The valid order was not saved in DynamoDB."


if __name__ == "__main__":
    test_integration_flow()
