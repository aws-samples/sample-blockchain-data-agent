# AWS Glue Crawler User Guide
## Automatic Blockchain Schema Discovery

Automatically discovers and catalogs blockchain data from the AWS Public Blockchain S3 bucket. When new blockchains are added, they're detected, dedicated databases are created, schemas are inferred, and Glue tables are created—all without manual intervention.

**Key Benefits:**
- Zero manual schema definition
- Automatic discovery of new blockchains
- Separate database per blockchain
- Weekly updates for schema changes
- Email notifications on discoveries
- ~$2-5/month total cost

---

## Quick Start

### Prerequisites

```bash
# AWS CLI configured
aws configure

# Python 3.8+ (for utility script)
pip install boto3 pyarrow
```

### 1. Deploy the Stack (5 minutes)

```bash
aws cloudformation create-stack \
  --stack-name blockchain-crawlers \
  --template-body file://utils/aws-public-blockchain-with-crawlers.yaml \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name blockchain-crawlers
```

### 2. Subscribe to Notifications (2 minutes)

```bash
# Get SNS topic ARN
TOPIC_ARN=$(aws cloudformation describe-stacks \
  --stack-name blockchain-crawlers \
  --query 'Stacks[0].Outputs[?OutputKey==`CrawlerNotificationTopicArn`].OutputValue' \
  --output text)

# Subscribe your email
aws sns subscribe \
  --topic-arn $TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription via email
```

### 3. Run Discovery (3 minutes)

```bash
# Get discovery function name
DISCOVERY_FN=$(aws cloudformation describe-stacks \
  --stack-name blockchain-crawlers \
  --query 'Stacks[0].Outputs[?OutputKey==`BlockchainDiscoveryFunction`].OutputValue' \
  --output text)

# Trigger discovery
aws lambda invoke \
  --function-name $DISCOVERY_FN \
  --payload '{}' \
  response.json

cat response.json
```

### 4. Query Discovered Data

```sql
-- In Athena console
SHOW DATABASES;
SHOW TABLES IN btc;

-- Query Bitcoin blocks
SELECT * FROM btc.blocks 
WHERE date = '2024-01-01' 
LIMIT 10;
```

---

## Architecture Overview

The solution uses a two-tier approach:

1. **Lambda Discovery Function**: Scans S3 for new blockchains, creates dedicated databases, creates crawlers, and starts them
2. **Per-Blockchain Crawlers**: Maintain schemas for each blockchain in its own database

```
┌─────────────────────────────────────────────────────────────┐
│                  AWS Public Blockchain S3                    │
│  v1.0/btc/  v1.0/eth/  v1.1/ton/  v1.0/newchain/           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              BlockchainDiscoveryFunction (Lambda)            │
│  - Scans S3 for new blockchains                             │
│  - Creates database per blockchain                          │
│  - Creates and starts crawlers                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    AWS Glue Crawlers                         │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────────┐           │
│  │ BTC  │  │ ETH  │  │ TON  │  │ Auto-created │           │
│  └──────┘  └──────┘  └──────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  AWS Glue Data Catalog                       │
│       btc  |  eth  |  ton  |  newchain (auto-created)       │
└─────────────────────────────────────────────────────────────┘
```

---

## Understanding What Gets Created

### Databases

Each blockchain gets its own dedicated database:

| Database | Purpose | Created By |
|----------|---------|------------|
| `btc` | Bitcoin data | CloudFormation (pre-defined) |
| `eth` | Ethereum data | CloudFormation (pre-defined) |
| `ton` | TON data | CloudFormation (pre-defined) |
| `{newchain}` | New blockchain data | Lambda Discovery Function |

### Crawlers

| Crawler | Scans | Output Database |
|---------|-------|-----------------|
| BTC Crawler | v1.0/btc/ | btc |
| ETH Crawler | v1.0/eth/ | eth |
| TON Crawler | v1.1/ton/ | ton |
| Auto-created | v1.x/{newchain}/ | {newchain} |

---

## Common Tasks

### Manually Trigger Discovery

**Trigger the Lambda function to scan for new blockchains:**

```bash
# Using AWS CLI
aws lambda invoke \
  --function-name blockchain-crawlers-BlockchainDiscovery \
  --payload '{}' \
  response.json

cat response.json
```

### Manually Trigger a Crawler

```bash
# Trigger specific crawler
aws glue start-crawler --name blockchain-crawlers-BTC-Crawler

# Check status
aws glue get-crawler --name blockchain-crawlers-BTC-Crawler \
  --query 'Crawler.State'
```

### Check Crawler Status

```bash
# Using AWS CLI
aws glue get-crawler --name blockchain-crawlers-ETH-Crawler \
  --query 'Crawler.{State:State,LastCrawl:LastCrawl}'
```

**Possible States:**
- `READY` - Available to run
- `RUNNING` - Currently executing
- `STOPPING` - Being stopped

### Change Crawler Schedule

Update the CloudFormation parameter:

```bash
aws cloudformation update-stack \
  --stack-name blockchain-crawlers \
  --template-body file://utils/aws-public-blockchain-with-crawlers.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters ParameterKey=CrawlerSchedule,ParameterValue="cron(0 2 * * ? *)"
```

Common schedules:
- Daily: `cron(0 2 * * ? *)`
- Weekly: `cron(0 2 ? * SUN *)` (default)
- Monthly: `cron(0 2 1 * ? *)`

### View Discovered Tables

```bash
# List all databases
aws glue get-databases --query 'DatabaseList[].Name'

# List tables in a database
aws glue get-tables --database-name btc --query 'TableList[].Name'
```

### Query Data in Athena

```sql
-- List all databases
SHOW DATABASES;

-- List tables in a database
SHOW TABLES IN eth;

-- Describe table schema
DESCRIBE eth.blocks;

-- Query data
SELECT 
  date,
  COUNT(*) as block_count
FROM btc.blocks
WHERE date >= '2024-01-01'
GROUP BY date
ORDER BY date;
```

---

## Using the Python Utility

### Installation

```bash
pip install -r utils/requirements-discovery.txt
```

### Common Commands

```bash
# List all blockchains in S3
python utils/blockchain_schema_discovery.py list-blockchains

# List tables for a blockchain
python utils/blockchain_schema_discovery.py list-tables eth

# Discover schema for a specific table
python utils/blockchain_schema_discovery.py discover-schema eth blocks

# Trigger a crawler
python utils/blockchain_schema_discovery.py trigger-crawler BTC-Crawler

# Check crawler status
python utils/blockchain_schema_discovery.py crawler-status BTC-Crawler
```

---

## Troubleshooting

### Crawler Fails with Access Denied

```bash
# Check IAM role permissions
aws iam get-role-policy \
  --role-name blockchain-crawlers-GlueCrawlerRole \
  --policy-name S3AccessPolicy

# Verify S3 access
aws s3 ls s3://aws-public-blockchain/v1.0/ --request-payer requester
```

### No Tables Created After Crawler Run

```bash
# Check if data exists
aws s3 ls s3://aws-public-blockchain/v1.0/btc/blocks/ --request-payer requester

# Check crawler logs
aws logs tail /aws-glue/crawlers --follow
```

### Discovery Lambda Not Finding New Blockchains

```bash
# Check Lambda logs
aws logs tail /aws/lambda/blockchain-crawlers-BlockchainDiscovery --follow

# Verify S3 structure
aws s3 ls s3://aws-public-blockchain/v1.0/ --request-payer requester
```

### Crawler Stuck in RUNNING State

```bash
# Stop crawler
aws glue stop-crawler --name blockchain-crawlers-BTC-Crawler

# Wait, then restart
aws glue start-crawler --name blockchain-crawlers-BTC-Crawler
```

---

## Cost Optimization

### Monthly Costs (~$2-5/month)

| Component | Monthly Cost |
|-----------|--------------|
| Glue Crawlers | ~$1.50 |
| Lambda | ~$0.00 (free tier) |
| SNS | ~$0.00 |
| Glue Data Catalog | ~$1.00 |

### Tips

1. Use weekly schedule (default) instead of daily
2. `CRAWL_NEW_FOLDERS_ONLY` is enabled by default
3. Use on-demand triggers for urgent updates

---

## FAQ

**Q: How long does discovery take?**
A: Lambda discovery runs in ~30 seconds. Crawlers take 2-5 minutes per blockchain.

**Q: What happens when a new blockchain is added to S3?**
A: On the next scheduled run (or manual trigger), the Lambda discovers it, creates a dedicated database, creates a crawler, and starts it automatically.

**Q: Can I trigger discovery manually?**
A: Yes, invoke the Lambda function directly or wait for the weekly schedule.

**Q: Do I need to update the template for new blockchains?**
A: No, the Lambda function handles everything automatically.

**Q: Why separate databases per blockchain?**
A: Better organization, easier permissions management, and cleaner Athena queries.

---

## Files and Resources

| File | Purpose |
|------|---------|
| `utils/aws-public-blockchain-with-crawlers.yaml` | CloudFormation template |
| `utils/blockchain_schema_discovery.py` | Python discovery utility |
| `utils/requirements-discovery.txt` | Python dependencies |
| `docs/CRAWLER_DESIGN.md` | Architecture documentation |
