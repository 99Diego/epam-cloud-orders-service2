# Product Backlog & Agile Framework

## Definition of Done (DoD)
A User Story or Task is considered "Done" when:
- [ ] Code is implemented following clean code principles.
- [ ] Unit tests are written and pass with at least 80% coverage.
- [ ] Terraform code is formatted (`terraform fmt`) and validated (`terraform validate`).
- [ ] Pull Request (PR) is opened with a clear description and linked to the User Story.
- [ ] CI/CD pipeline runs successfully on the PR.
- [ ] No hardcoded credentials or secrets exist in the repository.
- [ ] Documentation (README / Backlog) is updated accordingly.

---

## User Stories

### US-01: Inbound Order Storage (S3)
**As a** System Administrator,  
**I want** an S3 bucket named `orders-inbound`,  
**so that** clients can upload order files for processing.  
**Acceptance Criteria:**
1. Bucket named `orders-inbound` is provisioned via Terraform.
2. S3 bucket sends event notifications upon file upload (`s3:ObjectCreated:*`).

### US-02: Order Processing and Validation (Lambda)
**As a** Business Logic Service,  
**I want** a Lambda function triggered by S3 uploads,  
**so that** incoming JSON order files are validated against business rules.  
**Acceptance Criteria:**
1. Validates `order_id` (string), `customer_id` (string), `items` (non-empty list), and `total` (number > 0).
2. Functions continuously without unhandled crashes/exceptions.

### US-03: Storage of Valid Orders (DynamoDB)
**As a** Data Analyst,  
**I want** valid orders to be stored in DynamoDB,  
**so that** they can be queried for fulfillment.  
**Acceptance Criteria:**
1. DynamoDB table `orders` created with `order_id` as the Partition Key.
2. Lambda writes successfully parsed valid items into this table.

### US-04: Dead-Letter Queue for Invalid Orders (SQS)
**As a** Operations Engineer,  
**I want** bad/invalid orders pushed to an SQS Queue (`orders-dlq`),  
**so that** they can be inspected and reprocessed later.  
**Acceptance Criteria:**
1. SQS Queue `orders-dlq` created via Terraform.
2. Invalid order payloads include a failure reason payload when routed to SQS.

### US-05: Automated CI/CD & Local Testing Pipeline
**As a** Cloud Platform Engineer,  
**I want** a GitHub Actions workflow targeting LocalStack,  
**so that** integration and unit tests run automatically on every Pull Request.  
**Acceptance Criteria:**
1. Lints Python & Terraform files.
2. Spins up LocalStack, applies Terraform, and runs end-to-end integration tests.
3. Automatically blocks PR merging if tests fail.
