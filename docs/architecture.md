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

#### Amazon Bedrock (Claude 3 Haiku)
- **Cost**: $0.00025 per 1K input tokens (10x cheaper than GPT-4)
- **Speed**: ~1-2s response time (vs 5-10s for larger models)
- **Quality**: Sufficient for triage (95%+ accuracy in tests)

#### SQS over Direct Lambda Invocation
- **Decnts cascading failures
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
| Bedrock (5M tokens @ $0.00025/1K) | N/A | $1.25 |
| EventBridge (1K critical events) | First 1M free | $0 |
| SNS (1K notifications) | First 1M free | $0 |
| **Total** | - | **~$1.33/month** |

## Security

- **Least Privilege IAM**: Lambda role has minimal permissions
- **No Hardcoded Secrets**: Uses AWS Systems Manager Parameter Store
- **VPC Isolation**: (Optional) Lambda in private subnet
- **Encryption at Rest**: SQS messages encrypted with AWS-managed keys

## Scalability

- **Auto-scaling**: Lambda scales to 1000 concurrent executions (soft limit)
- **Backpressure**: SQS queues prevent overload
- **Rate Limiting**: Bedrock throttling handled with exponential backoff
