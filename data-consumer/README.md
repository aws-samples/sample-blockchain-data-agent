# Blockchain Data Consumer Architecture

CloudFormation templates for deploying the AWS infrastructure to consume and query blockchain data from the [AWS Public Blockchain Datasets](https://registry.opendata.aws/aws-public-blockchain/).

## Templates

| Template | Description |
|----------|-------------|
| `aws-public-blockchain-with-crawlers.yaml` | **Recommended** - Automatic schema discovery with Glue Crawlers |
| `aws-public-blockchain.yaml` | Original template with pre-defined schemas |

## Quick Start

### Deploy with Automatic Schema Discovery (Recommended)

```bash
aws cloudformation create-stack \
  --stack-name blockchain-crawlers \
  --template-body file://data-consumer/aws-public-blockchain-with-crawlers.yaml \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation wait stack-create-complete --stack-name blockchain-crawlers
```

The stack automatically:
- Discovers all blockchains in the S3 bucket
- Creates a dedicated database per blockchain (btc, eth, ton, etc.)
- Creates and starts crawlers to infer schemas
- Sets up configurable schedules per chain

### Subscribe to Notifications

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

### Query Data in Athena

```sql
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

Each blockchain crawler has its own configurable schedule.

### Available Schedules

| Schedule | Expression | Est. Cost/Chain/Month |
|----------|------------|----------------------|
| `1min` | Every minute | $50-100+ |
| `10min` | Every 10 minutes | $5-10 |
| `hourly` | Every hour | $1-2 |
| `daily` | Every day | $0.50 (default) |

### List All Schedules

```bash
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "list"}' \
  response.json --no-cli-pager && cat response.json
```

### Set Schedule for a Blockchain

```bash
# Set BTC to hourly
aws lambda invoke \
  --function-name blockchain-crawlers-CrawlerScheduleManager \
  --payload '{"action": "set", "blockchain": "BTC", "schedule": "hourly"}' \
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

---

## Documentation

- [Crawler Design](../docs/CRAWLER_DESIGN.md) - Architecture and implementation details
- [Crawler User Guide](../docs/CRAWLER_README.md) - Detailed usage and troubleshooting
