# Architecture Overview

## System Design

### High-Level Flow
1. Customer submits ticket → SQS Queue
2. Lambda polls SQS (event source mapping)
3. LangGraph orchestrator processes ticket:
   - Triage Agent → Classifies category + urgency
   - Response Agent → Generates draft reply
   - Validation Agent → Ensures Pydantic compliance
4. If urgency ≥ 4 → Emit EventBridge event
5. EventBridge → SNS → Slack/Email notification

### Why This Stack?

#### LangGraph over LangChain Chains
- **State Management**: Multi-step workflows need memory between nodes
- **Error Recovery**: Can retry individual nodes without re-running entire flow
- **Observability**: Each node emits separate traces

#### Amazon Bedrock (Nova Micro by default)
- **Default model**: `amazon.nova-micro-v1:0` via Terraform `bedrock_model_id` / Lambda `BEDROCK_MODEL_ID`. The Bedrock client in `src/utils/bedrock_client.py` also supports Anthropic Claude when the model id implies the Messages API.
- **Cost**: On-demand list defaults in code are ~$0.000035/1K input and ~$0.00014/1K output for Nova Micro; run `estimate_cost` in the client or check [AWS Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) for current rates.
- **Speed**: Fast enough for sub–3s multi-agent turns on typical tickets.
- **Quality**: Sufficient for structured triage + draft + validation; validate against your own evals.

#### SQS over Direct Lambda Invocation
- **Decouples** cascading failures
- **Throttling**: Lambda auto-scales but Bedrock has rate limits
- **Retry Logic**: DLQ captures failed messages

#### EventBridge over SNS Direct
- **Filtering**: Only critical tickets trigger alerts
- **Extensibility**: Easy to add new targets (Slack, PagerDuty, etc.)
- **Audit Trail**: All events logged in CloudWatch

## Cost Analysis

| Component | Free Tier | Estimated Monthly Cost (10K tickets) |
|-----------|-----------|--------------------------------------|
| Lambda (10K invocations @ 512MB, 3s avg) | First 1M free | $0.08 |
| SQS (10K messages) | First 1M free | $0.004 |
| Bedrock (5M tokens, Nova Micro, ~70% in / 30% out blend) | N/A | ~$0.33 |
| EventBridge (1K critical events) | First 1M free | $0 |
| SNS (1K notifications) | First 1M free | $0 |
| **Total** | - | **~$0.41/month** |

_Bedrock row uses the same illustrative blend as README Cost Analysis; confirm live pricing on AWS._

## Security

- **Least Privilege IAM**: Lambda role has minimal permissions
- **No Hardcoded Secrets**: Uses AWS Systems Manager Parameter Store
- **VPC Isolation**: (Optional) Lambda in private subnet
- **Encryption at Rest**: SQS messages encrypted with AWS-managed keys

## Scalability

- **Auto-scaling**: Lambda scales to 1000 concurrent executions (soft limit)
- **Backpressure**: SQS queues prevent overload
- **Rate Limiting**: Bedrock throttling handled with exponential backoff
