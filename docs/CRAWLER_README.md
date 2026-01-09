# AWS Glue Crawler User Guide
## Automatic Blockchain Schema Discovery

Automatically discovers and catalogs blockchain data from the AWS Public Blockchain S3 bucket. When new blockchains are added, they're detected, dedicated databases are created, schemas are inferred, and Glue tables are created—all without manual intervention.

**Key Benefits:**
- Zero manual schema definition
- Automatic discovery of new blockchains
- Separate database per blockchain
- Built-in Glue crawler scheduling (1min, 10min, hourly, daily)
- Email notifications on discoveries
- ~$2-5/month base cost

---

## Quick Start

### Prerequisites

```bash
aws configure
```

### 1. Deploy the Stack

```bash
aws cloudformation create-stack \
  --stack-name blockchain-crawlers \
  --template-body file://data-consumer/aws-public-blockchain-with-crawlers.yaml \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation wait stack-create-complete --stack-name blockchain-crawlers
```

The stack automatically runs initial discovery on deployment, creating databases and crawlers (with built-in schedules) for all blockchains found in S3.

### 2. Subscribe to Notifications

```bash
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name blockchain-crawlers \
  --query 'Stacks[0].Outputs[?OutputKey==`CrawlerNotificationTopicArn`].OutputValue' \
  --output text)

aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com
```

### 3. Query Data

```sql
-- In Athena console
SHOW DATABASES;
SHOW TABLES IN btc;
SELECT * FROM btc.blocks WHERE date = '2024-01-01' LIMIT 10;
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  AWS Public Blockchain S3                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              BlockchainDiscoveryFunction (Lambda)            │
│  - Scans S3 for blockchain namespaces                       │
│  - Creates database per blockchain                          │
│  - Creates crawler with built-in schedule per blockchain    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│           AWS Glue Crawlers (with native scheduling)         │
│       BTC-Crawler | ETH-Crawler | TON-Crawler | etc.        │
│         (daily)   |   (daily)   |   (daily)   |             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  AWS Glue Data Catalog                       │
│              btc | eth | ton | (auto-created)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Managing Crawler Schedules

Crawlers use Glue's native scheduling. Manage schedules via AWS Console or CLI.

### Available Schedules

| Schedule | Cron Expression | Use Case |
|----------|-----------------|----------|
| Every minute | `cron(0/1 * * * ? *)` | Real-time monitoring (expensive) |
| Every 10 min | `cron(0/10 * * * ? *)` | Near real-time |
| Hourly | `cron(0 * * * ? *)` | Balanced |
| Daily | `cron(0 0 * * ? *)` | Cost-effective (default) |

### View Crawler Schedule

```bash
aws glue get-crawler --name blockchain-crawlers-BTC-Crawler \
  --query 'Crawler.Schedule' --output json
```

### Update Crawler Schedule

```bash
# Set to hourly
aws glue update-crawler \
  --name blockchain-crawlers-BTC-Crawler \
  --schedule "cron(0 * * * ? *)"

# Set to every 10 minutes
aws glue update-crawler \
  --name blockchain-crawlers-ETH-Crawler \
  --schedule "cron(0/10 * * * ? *)"

# Set to daily (midnight UTC)
aws glue update-crawler \
  --name blockchain-crawlers-TON-Crawler \
  --schedule "cron(0 0 * * ? *)"
```

### Disable Schedule (Manual Only)

```bash
aws glue update-crawler \
  --name blockchain-crawlers-TON-Crawler \
  --schedule ""
```

### Manually Trigger a Crawler

```bash
aws glue start-crawler --name blockchain-crawlers-BTC-Crawler
```

### List All Crawlers

```bash
aws glue list-crawlers --query 'CrawlerNames[?starts_with(@, `blockchain-crawlers-`)]'
```

---

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `S3Bucket` | aws-public-blockchain | Source S3 bucket |
| `SchemaVersion` | v1.0 | Schema version for BTC/ETH |
| `SchemaVersionTON` | v1.1 | Schema version for TON |
| `DiscoverySchedule` | Weekly (Sunday 2AM) | How often to scan for new blockchains |
| `DefaultCrawlerSchedule` | daily | Default schedule for new crawlers |
| `EnableAutoCrawling` | true | Enable/disable automatic scheduling |

### Deploy with Custom Settings

```bash
aws cloudformation create-stack \
  --stack-name blockchain-crawlers \
  --template-body file://data-consumer/aws-public-blockchain-with-crawlers.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters \
    ParameterKey=DefaultCrawlerSchedule,ParameterValue=hourly \
    ParameterKey=DiscoverySchedule,ParameterValue="cron(0 0 * * ? *)"
```

---

## Cost Considerations

| Schedule | Crawler Runs/Month | Est. Cost/Chain |
|----------|-------------------|-----------------|
| 1min | 43,200 | $50-100+ |
| 10min | 4,320 | $5-10 |
| hourly | 720 | $1-2 |
| daily | 30 | $0.50 |

**Recommendations:**
- Use `daily` for most chains (default)
- Use `hourly` for chains you actively query
- Use `10min` or `1min` only for real-time requirements
- Disable schedules for chains you don't need

---

## Troubleshooting

### Crawler Not Running

```bash
# Check crawler state
aws glue get-crawler --name blockchain-crawlers-BTC-Crawler \
  --query 'Crawler.{State:State,Schedule:Schedule}' --output json

# Check if schedule is set
aws glue get-crawler --name blockchain-crawlers-BTC-Crawler \
  --query 'Crawler.Schedule.ScheduleExpression' --output text
```

### No Tables After Crawler Run

```bash
# Check crawler logs
aws logs tail /aws-glue/crawlers --follow

# Verify S3 data exists
aws s3 ls s3://aws-public-blockchain/v1.0/btc/ --request-payer requester
```

### Discovery Not Finding New Chains

```bash
# Check discovery Lambda logs
aws logs tail /aws/lambda/blockchain-crawlers-BlockchainDiscovery --follow

# Manually trigger discovery
aws lambda invoke \
  --function-name blockchain-crawlers-BlockchainDiscovery \
  --payload '{}' \
  response.json --no-cli-pager
```

---

## Lambda Functions

| Function | Purpose |
|----------|---------|
| `BlockchainDiscovery` | Discovers chains, creates DBs and crawlers with schedules |
| `CrawlerCompletionHandler` | Sends notifications on crawler completion |

---

## Files

| File | Purpose |
|------|---------|
| `data-consumer/aws-public-blockchain-with-crawlers.yaml` | CloudFormation template |
| `utils/blockchain_schema_discovery.py` | Python utility for manual exploration |
| `docs/CRAWLER_DESIGN.md` | Architecture documentation |
