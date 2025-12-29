# AWS Glue Crawler User Guide
## Automatic Blockchain Schema Discovery

Automatically discovers and catalogs blockchain data from the AWS Public Blockchain S3 bucket. When new blockchains are added, they're detected, schemas are inferred, and Glue tables are created—all without manual intervention.

**Key Benefits:**
- Zero manual schema definition
- Automatic discovery of new blockchains
- Weekly updates for schema changes
- Email notifications on discoveries
- ~$2-5/month total cost

**What This Does:**
- ✅ Automatically discovers new blockchains in S3
- ✅ Infers schemas from Parquet metadata
- ✅ Creates Glue tables for querying in Athena
- ✅ Sends notifications on discoveries
- ✅ Handles schema evolution
- ✅ Costs ~$2-5/month

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

### 3. Run First Crawler (3 minutes)

```bash
# Get master crawler name
CRAWLER=$(aws cloudformation describe-stacks \
  --stack-name blockchain-crawlers \
  --query 'Stacks[0].Outputs[?OutputKey==`MasterCrawlerName`].OutputValue' \
  --output text)

# Start crawler
aws glue start-crawler --name $CRAWLER

# Check status (repeat until READY)
aws glue get-crawler --name $CRAWLER --query 'Crawler.State'
```

### 4. Query Discovered Data

```sql
-- In Athena console
SHOW DATABASES;
SHOW TABLES IN blockchain_discovery;

-- Query discovered blockchain
SELECT * FROM blockchain_discovery.btc_blocks 
WHERE date = '2024-01-01' 
LIMIT 10;
```

---

## Using the Python Utility

### Installation

```bash
pip install -r utils/requirements-discovery.txt
```

### Common Commands

#### List All Blockchains
```bash
python utils/blockchain_schema_discovery.py list-blockchains

# Output:
# 🔍 Scanning S3 bucket: s3://aws-public-blockchain/v1.0/
# ✅ Found 3 blockchain(s): btc, eth, ton
```

#### List Tables for a Blockchain
```bash
python utils/blockchain_schema_discovery.py list-tables eth

# Output:
# 🔍 Discovering tables for eth...
# ✅ Found 6 table(s): blocks, contracts, logs, token_transfers, traces, transactions
```

#### Discover Schema
```bash
python utils/blockchain_schema_discovery.py discover-schema eth blocks \
  --output eth_blocks_schema.json \
  --cloudformation

# Outputs:
# - Schema summary to console
# - JSON file with complete schema
# - CloudFormation template (if --cloudformation flag used)
```

#### Manage Crawlers
```bash
# Trigger crawler manually
python utils/blockchain_schema_discovery.py trigger-crawler MasterCrawler

# Check status
python utils/blockchain_schema_discovery.py crawler-status MasterCrawler
```

---

## Understanding What Gets Created

### Databases

| Database | Purpose | Created By |
|----------|---------|------------|
| `blockchain_discovery` | New/unknown blockchains | Master Crawler |
| `btc` | Bitcoin data | BTC Crawler |
| `eth` | Ethereum data | ETH Crawler |
| `ton` | TON data | TON Crawler |

### Tables

Tables are automatically named: `{blockchain}_{table_type}`

Examples:
- `blockchain_discovery.sol_blocks` (if Solana is added)
- `btc.blocks`
- `eth.transactions`
- `ton.messages`

### Crawlers

| Crawler | Scans | Frequency | Output Database |
|---------|-------|-----------|-----------------|
| Master | Entire bucket (excluding known chains) | Weekly | blockchain_discovery |
| BTC | v1.0/btc/ | Weekly | btc |
| ETH | v1.0/eth/ | Weekly | eth |
| TON | v1.1/ton/ | Weekly | ton |

---

## Common Tasks

### Manually Trigger a Crawler

**You can trigger crawlers anytime without waiting for the weekly schedule:**

```bash
# Using Python utility (easiest)
python utils/blockchain_schema_discovery.py trigger-crawler MasterCrawler

# Using AWS CLI
aws glue start-crawler --name blockchain-crawlers-MasterBlockchainDiscovery

# Trigger all crawlers at once
aws cloudformation describe-stacks \
  --stack-name blockchain-crawlers \
  --query 'Stacks[0].Outputs[?contains(OutputKey, `Crawler`)].OutputValue' \
  --output text | while read crawler; do
    echo "Starting $crawler"
    aws glue start-crawler --name $crawler
done
```

### Check Crawler Status

```bash
# Using Python utility
python utils/blockchain_schema_discovery.py crawler-status MasterCrawler

# Using AWS CLI
aws glue get-crawler --name blockchain-crawlers-MasterBlockchainDiscovery \
  --query 'Crawler.{State:State,LastCrawl:LastCrawl}'
```

**Possible States:**
- `READY` - Available to run
- `RUNNING` - Currently executing
- `STOPPING` - Being stopped
- `STOPPED` - Manually stopped

### Change Crawler Schedule

Edit CloudFormation parameter and update stack:

```yaml
# In template
CrawlerSchedule: "cron(0 2 * * ? *)"  # Daily at 2 AM UTC
```

Common schedules:
- Daily: `cron(0 2 * * ? *)`
- Weekly: `cron(0 2 ? * SUN *)` (default)
- Monthly: `cron(0 2 1 * ? *)`

Update the stack:
```bash
aws cloudformation update-stack \
  --stack-name blockchain-crawlers \
  --template-body file://utils/aws-public-blockchain-with-crawlers.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameters ParameterKey=CrawlerSchedule,ParameterValue="cron(0 2 * * ? *)"
```

### View Discovered Tables

```bash
# List all tables in discovery database
aws glue get-tables --database-name blockchain_discovery \
  --query 'TableList[].Name'

# Get table details
aws glue get-table --database-name blockchain_discovery --name sol_blocks
```

### Query Data in Athena

```sql
-- List all databases
SHOW DATABASES;

-- List tables in a database
SHOW TABLES IN blockchain_discovery;

-- Describe table schema
DESCRIBE blockchain_discovery.btc_blocks;

-- Query data
SELECT 
  date,
  COUNT(*) as block_count,
  AVG(transaction_count) as avg_txs
FROM blockchain_discovery.btc_blocks
WHERE date >= '2024-01-01'
GROUP BY date
ORDER BY date;
```

---

## Troubleshooting

### Crawler Fails with Access Denied

**Problem**: IAM permissions issue

**Solution**:
```bash
# Check IAM role permissions
aws iam get-role-policy \
  --role-name blockchain-crawlers-GlueCrawlerRole \
  --policy-name S3AccessPolicy

# Verify S3 access
aws s3 ls s3://aws-public-blockchain/v1.0/ --request-payer requester
```

### No Tables Created After Crawler Run

**Problem**: No Parquet files found or crawler configuration issue

**Solution**:
```bash
# Check if data exists
aws s3 ls s3://aws-public-blockchain/v1.0/btc/blocks/ --request-payer requester

# Check crawler logs
aws logs tail /aws-glue/crawlers --follow

# Verify crawler configuration
aws glue get-crawler --name blockchain-crawlers-MasterBlockchainDiscovery
```

### Schema Not Updating

**Problem**: Schema change policy or crawler not running

**Solution**:
```bash
# Check schema change policy
aws glue get-crawler --name blockchain-crawlers-ETH-Crawler \
  --query 'Crawler.SchemaChangePolicy'

# Force full recrawl (temporary)
aws glue update-crawler \
  --name blockchain-crawlers-ETH-Crawler \
  --recrawl-policy '{"RecrawlBehavior":"CRAWL_EVERYTHING"}'

# Trigger crawler
aws glue start-crawler --name blockchain-crawlers-ETH-Crawler
```

### Crawler Stuck in RUNNING State

**Problem**: Crawler hung or taking too long

**Solution**:
```bash
# Stop crawler
aws glue stop-crawler --name blockchain-crawlers-MasterBlockchainDiscovery

# Wait a moment, then restart
aws glue start-crawler --name blockchain-crawlers-MasterBlockchainDiscovery
```

### High Costs

**Problem**: Crawlers running too frequently or scanning too much data

**Solution**:
```bash
# Check crawler metrics
aws glue get-crawler-metrics \
  --crawler-name-list blockchain-crawlers-MasterBlockchainDiscovery

# Review CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Glue \
  --metric-name glue.driver.aggregate.numBytes \
  --dimensions Name=CrawlerName,Value=blockchain-crawlers-MasterBlockchainDiscovery \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum

# Reduce frequency (change to monthly)
# Update CloudFormation parameter: CrawlerSchedule="cron(0 2 1 * ? *)"
```

---

## Monitoring

### CloudWatch Metrics

Key metrics to monitor:
- `glue.driver.aggregate.numBytes` - Data scanned
- `glue.driver.aggregate.elapsedTime` - Crawler runtime
- `glue.ALL.s3.listRequest.count` - S3 API calls

### Crawler Logs

```bash
# View crawler logs
aws logs tail /aws-glue/crawlers --follow

# Filter for specific crawler
aws logs filter-log-events \
  --log-group-name /aws-glue/crawlers \
  --filter-pattern "MasterBlockchainDiscovery"
```

### SNS Notifications

You'll receive email notifications for:
- Crawler completion (success/failure)
- New blockchain discoveries
- Schema updates
- Error conditions

---

## Cost Optimization

### Current Costs (~$2-5/month)

| Component | Monthly Cost |
|-----------|--------------|
| Glue Crawlers (4 × 4 runs) | $1.22 |
| Lambda Invocations | $0.00 |
| SNS Notifications | $0.00 |
| S3 Requests | $0.01 |
| Glue Data Catalog | $1.00 |

### Optimization Tips

1. **Use weekly schedule** (default) instead of daily
2. **Enable CRAWL_NEW_FOLDERS_ONLY** (already enabled)
3. **Add exclusion patterns** for data you don't need
4. **Monitor crawler runtime** and adjust if needed
5. **Use on-demand triggers** for urgent updates instead of frequent schedules

---

## Best Practices

### 1. Start with Default Configuration
- Weekly schedule is sufficient for most use cases
- Master crawler handles all new blockchains
- Per-blockchain crawlers maintain known chains

### 2. Subscribe Multiple Stakeholders
```bash
# Add multiple email subscriptions
aws sns subscribe --topic-arn $TOPIC_ARN --protocol email --notification-endpoint team@example.com
aws sns subscribe --topic-arn $TOPIC_ARN --protocol email --notification-endpoint manager@example.com
```

### 3. Test Before Production
```bash
# Use Python utility to explore first
python utils/blockchain_schema_discovery.py list-blockchains
python utils/blockchain_schema_discovery.py discover-schema btc blocks

# Deploy crawlers once confident
aws cloudformation create-stack ...
```

### 4. Review Discovered Schemas
```sql
-- Check schema before using in production
DESCRIBE blockchain_discovery.newchain_blocks;

-- Test queries on small date ranges
SELECT * FROM blockchain_discovery.newchain_blocks 
WHERE date = '2024-01-01' 
LIMIT 10;
```

### 5. Keep Exclusions Updated
If you add dedicated crawlers for specific blockchains, update the master crawler exclusions:

```yaml
MasterBlockchainCrawler:
  Properties:
    Targets:
      S3Targets:
        - Path: s3://aws-public-blockchain/
          Exclusions:
            - "v1.0/btc/**"
            - "v1.0/eth/**"
            - "v1.1/ton/**"
            - "v1.0/sol/**"  # Add new exclusions here
```

---

## FAQ

**Q: How long does the initial crawler run take?**
A: 5-10 minutes for the master crawler, 2-5 minutes per blockchain crawler.

**Q: What happens when a new blockchain is added?**
A: The master crawler automatically discovers it on the next scheduled run (weekly), creates tables, and sends a notification.

**Q: Can I query data immediately after deployment?**
A: Yes, once the crawlers complete their first run (10-15 minutes after deployment).

**Q: Can I trigger crawlers manually instead of waiting for weekly schedule?**
A: Yes! Use `python utils/blockchain_schema_discovery.py trigger-crawler MasterCrawler` or AWS CLI commands shown above.

**Q: Do I need to update the template when new blockchains are added?**
A: No, the master crawler handles all new blockchains automatically.

**Q: What if I want a dedicated database for a new blockchain?**
A: Add a dedicated crawler and database to the CloudFormation template, then add the blockchain to the master crawler's exclusion list.

**Q: How do I know when new blockchains are discovered?**
A: You'll receive an SNS email notification with details about the discovered tables.

**Q: Can I use this with my own S3 bucket?**
A: Yes, change the `S3Bucket` parameter when deploying the stack.

**Q: What's the difference between the crawlers and the Python utility?**
A: Crawlers run automatically in AWS and create Glue tables. The Python utility is for manual exploration and debugging on your laptop.

---

## Files and Resources

| File | Purpose |
|------|---------|
| `utils/aws-public-blockchain-with-crawlers.yaml` | CloudFormation template |
| `utils/blockchain_schema_discovery.py` | Python discovery utility |
| `utils/requirements-discovery.txt` | Python dependencies |
| `docs/CRAWLER_DESIGN.md` | Architecture documentation |

---

## Next Steps

1. ✅ Deploy the CloudFormation stack
2. ✅ Subscribe to notifications
3. ✅ Run first crawler
4. ✅ Query data in Athena
5. ⏳ Set up QuickSight dashboards
6. ⏳ Integrate with data pipelines
7. ⏳ Create automated reports

---

## Support Resources

- **Architecture questions**: See `CRAWLER_DESIGN.md` for detailed architecture
- **AWS Glue docs**: https://docs.aws.amazon.com/glue/
- **AWS Public Blockchain**: https://registry.opendata.aws/aws-public-blockchain/
- **Python Utility**: `utils/blockchain_schema_discovery.py --help`
