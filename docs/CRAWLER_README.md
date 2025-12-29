# AWS Glue Crawler User Guide
## Automatic Blockchain Schema Discovery

Automatically discovers and catalogs blockchain data from the AWS Public Blockchain S3 bucket. When new blockchains are added, they're detected, dedicated databases are created, schemas are inferred, and Glue tables are created—all without manual intervention.

**Key Benefits:**
- Zero manual schema definition
- Automatic discovery of new blockchains
- Separate database per blockchain
- Configurable per-chain crawler schedules (1min, 10min, hourly, daily)
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
  --template-body file://utils/aws-public-blockchain-with-crawlers.yaml \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation wait stack-create-complete --stack-name blockchain-crawlers
```

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

### 3. Run Initial Discovery

```bash
aws lambda invoke \
  --function-name blockchain-crawlers-BlockchainDiscovery \
  --payload '{}' \
  response.json --no-cli-pager

cat response.json
```

This will discover all blockchains (btc, eth, ton, etc.), create databases, crawlers, and schedules.

### 4. Query Data

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
│  - Creates crawler per blockchain                           │
│  - Creates EventBridge schedule per crawler                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              EventBridge Schedules (per chain)               │
│  BTC: daily | ETH: hourly | TON: 10min | etc.              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    AWS Glue Crawlers                         │
│       BTC-Crawler | ETH-Crawler | TON-Crawler | etc.        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  AWS Glue Data Catalog                       │
│              btc | eth | ton | (auto-created)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Managing Crawler Schedules

Each blockchain crawler has its own configurable schedule. Use the `CrawlerScheduleManager` Lambda to manage them.

### Available Schedules

| Schedule | Expression | Use Case |
|----------|------------|----------|
| `1min` | Every minute | Real-time monitoring (expensive) |
| `10min` | Every 10 minutes | Near real-time |
| `hourly` | Every hour | Balanced |
| `daily` | Every day | Cost-effective (default) |
| `disabled` | No schedule | Manual only |

### List All Schedules

```bash
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "list"}' \
  response.json --no-cli-pager

cat response.json
```

### Get Schedule for a Blockchain

```bash
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "get", "blockchain": "BTC"}' \
  response.json --no-cli-pager
```

### Set Schedule for a Blockchain

```bash
# Set BTC to hourly
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "set", "blockchain": "BTC", "schedule": "hourly"}' \
  response.json --no-cli-pager

# Set ETH to every 10 minutes
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "set", "blockchain": "ETH", "schedule": "10min"}' \
  response.json --no-cli-pager

# Set TON to daily
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "set", "blockchain": "TON", "schedule": "daily"}' \
  response.json --no-cli-pager
```

### Disable Schedule (Manual Only)

```bash
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "disable", "blockchain": "TON"}' \
  response.json --no-cli-pager
```

### Manually Trigger a Crawler

```bash
aws glue start-crawler --name blockchain-crawlers-BTC-Crawler
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
  --template-body file://utils/aws-public-blockchain-with-crawlers.yaml \
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
  --query 'Crawler.State' --no-cli-pager

# Check schedule exists
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "get", "blockchain": "BTC"}' \
  response.json --no-cli-pager
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
| `BlockchainDiscovery` | Discovers chains, creates DBs/crawlers/schedules |
| `CrawlerScheduleManager` | Manages per-chain crawler schedules |
| `CrawlerCompletionHandler` | Sends notifications on crawler completion |

---

## Files

| File | Purpose |
|------|---------|
| `utils/aws-public-blockchain-with-crawlers.yaml` | CloudFormation template |
| `utils/blockchain_schema_discovery.py` | Python utility for manual exploration |
| `docs/CRAWLER_DESIGN.md` | Architecture documentation |
