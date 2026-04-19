# Orion: AI Support Orchestrator (Serverless)

Automated support ticket triage system built with LangGraph, Amazon Bedrock, and AWS Lambda.

---

## Business Impact

- 80% reduction in manual ticket classification time  
- Approximately $0.10 to process 1,000 tickets using Nova Micro (illustrative; see Cost Analysis)  
- Sub-3 second average response time  

---

## Architecture

![Orion Architecture](https://github.com/user-attachments/assets/b3ccc2e2-5e6c-4020-9ffb-85e296fc1fa6)

---

## Technology Stack

| Component        | Technology                                   | Rationale |
|-----------------|----------------------------------------------|-----------|
| Orchestration   | LangGraph                                     | State management for multi-agent workflows |
| Validation      | Pydantic                                      | Type-safe data contracts to prevent malformed outputs |
| LLM             | Amazon Bedrock (Nova Micro)                   | Low per-token cost; Claude supported via `BEDROCK_MODEL_ID` |
| Infrastructure  | AWS Lambda, SQS, EventBridge                  | Serverless, event-driven, auto-scaling |
| IaC             | Terraform                                     | Reproducible infrastructure provisioning |

---


## Project Structure
```
ai-support-orchestrator/
├── infra/              # Terraform (AWS infrastructure)
├── src/
│   ├── agents/         # LangGraph workflow
│   ├── schemas/        # Pydantic data contracts
│   └── utils/          # AWS SDK helpers
├── tests/              # Unit + integration tests
└── docs/               # Architecture decisions
```

---


## Quick Start

### Prerequisites

- Python 3.12+
- AWS account (Free Tier eligible)
- Terraform 1.7+

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Build Lambda layer (requires Docker)
./scripts/build_lambda_layer.sh

# Deploy infrastructure
cd infra
terraform init
terraform apply
```

## Lambda Packaging

- The function package includes only application code (`src/`)
- Dependencies are included in a Lambda Layer (`infra/lambda_layer.zip`)
- The layer is built using a Python 3.12 Docker image for compatibility

Rebuild the layer after modifying `requirements-lambda.txt`:

```bash
./scripts/build_lambda_layer.sh
terraform apply
```

## Cost Analysis

Estimates based on Nova Micro defaults defined in [`src/utils/bedrock_client.py`](src/utils/bedrock_client.py). Verify actual pricing on AWS.

| Component                     | Free Tier | After Free Tier |
|------------------------------|-----------|-----------------|
| Lambda (1M requests)         | $0        | $0.20           |
| SQS (1M messages)            | $0        | $0.40           |
| Bedrock (~1.2M tokens)       | N/A       | ~$0.07          |
| **Total (1K tickets)**       | **~$0**   | **~$0.10**      |

**Assumption:** ~1.2K tokens per ticket across the workflow.

## Testing

Run the following commands to validate the system:

```bash
# Run unit tests (fast, no AWS required)
pytest tests/unit/ -v

# Run integration tests (requires AWS credentials)
pytest tests/integration/ -v

# Generate coverage report
pytest --cov=src tests/
```

## Example outputs

Illustrative traces for documentation and debugging. Timings and token counts reflect a real run shape; ticket id is aligned with [docs/examples/sqs_lambda_event.json](docs/examples/sqs_lambda_event.json).

### CloudWatch Logs (one invocation)

Example execution for a Billing ticket with urgency 3 (below the alert threshold, so no EventBridge → SNS notification is triggered).

To stream logs in real time:

```
aws logs tail "/aws/lambda/$(terraform -chdir=infra output -raw lambda_function_name)" --follow
```

Sample log output (simplified for readability):

```
START RequestId: 6b0a5ada...

[INFO] Received 1 SQS message
[INFO] Processing ticket: DEMO-README-001

[INFO] Initialized Bedrock client (Nova Micro)
[INFO] LangGraph workflow compiled

[INFO] Triaging ticket
[INFO] Bedrock tokens: 400 in, 74 out
[INFO] Triage result: Billing (urgency 3)

[INFO] Generating response
[INFO] Bedrock tokens: 336 in, 206 out
[INFO] Response generated (requires_review: True)

[INFO] Validating response
[INFO] Bedrock tokens: 443 in, 47 out
[INFO] Validation passed (score: 9/10)

[INFO] Processing complete
       Tokens: 1179 in / 327 out
       Cost: $0.000087

END RequestId: 6b0a5ada...
```

### Structured Lambda response (`aws lambda invoke`)

When Lambda is triggered by SQS, the response is not returned to the message producer.
To inspect the handler output, invoke the function manually with an SQS-formatted payload.

Example event: [docs/examples/sqs_lambda_event.json](docs/examples/sqs_lambda_event.json)

Run

```bash
cd infra

aws lambda invoke \
  --function-name "$(terraform output -raw lambda_function_name)" \
  --cli-binary-format raw-in-base64-out \
  --payload file://../docs/examples/sqs_lambda_event.json \
  /tmp/lambda-out.json

python3 -m json.tool /tmp/lambda-out.json
```

The response contains a body field as a JSON string. To pretty-print it:

```bash
jq -r '.body | fromjson' /tmp/lambda-out.json | jq .
```

Example fields in the parsed response:

- `analysis` (final AI output)
- `cost` (estimated execution cost)
- `critical_alert_sent` (boolean flag)
- `processed_records`
