# AWS Glue Crawler Design Document
## Automatic Blockchain Schema Discovery Architecture

### Overview

This document describes the architecture of the automated blockchain schema discovery solution. The system automatically discovers new blockchain namespaces in the AWS Public Blockchain S3 bucket, creates dedicated databases per blockchain, infers schemas from Parquet metadata, and creates crawlers with built-in schedules.

---

## Design Goals

1. **Zero-Touch Discovery**: Automatically detect and catalog new blockchains
2. **Database Per Blockchain**: Each blockchain gets its own dedicated Glue database
3. **Native Scheduling**: Use Glue's built-in crawler scheduling (cron expressions)
4. **Cost Optimization**: Default to daily crawls, allow fine-tuning per chain
5. **Simplicity**: Minimal Lambda functions, leverage AWS native features

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  AWS Public Blockchain S3                    │
│  v1.0/btc/  v1.0/eth/  v1.1/ton/  v1.0/newchain/           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              BlockchainDiscoveryFunction (Lambda)            │
│  1. Scans S3 for blockchain namespaces                      │
│  2. Creates Glue database per blockchain                    │
│  3. Creates Glue crawler with built-in schedule             │
│  4. Starts crawlers on first creation                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│           AWS Glue Crawlers (with native scheduling)         │
│  {stack}-BTC-Crawler → btc database (daily)                │
│  {stack}-ETH-Crawler → eth database (daily)                │
│  {stack}-TON-Crawler → ton database (daily)                │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  AWS Glue Data Catalog                       │
│       btc  |  eth  |  ton  |  (auto-created)               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              CrawlerCompletionHandler (Lambda)               │
│  - Triggered by Glue crawler state changes                  │
│  - Sends SNS notifications on completion                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. BlockchainDiscoveryFunction

**Purpose**: Discovers blockchains and creates all necessary resources

**Trigger**: 
- EventBridge schedule (weekly by default)
- Manual invocation
- CloudFormation custom resource (on stack creation)

**Process**:
1. Scan S3 bucket for blockchain namespaces (v1.0/*, v1.1/*)
2. For each discovered blockchain:
   - Create Glue database if not exists
   - Create Glue crawler with built-in schedule if not exists
   - Start crawler on first creation
3. Send SNS notification with discovery report

**Environment Variables**:
- `S3_BUCKET`: Source bucket
- `SCHEMA_VERSION`: Default schema version
- `SCHEMA_VERSION_TON`: TON schema version
- `CRAWLER_ROLE_ARN`: IAM role for crawlers
- `STACK_NAME`: CloudFormation stack name
- `SNS_TOPIC_ARN`: Notification topic
- `DEFAULT_CRAWLER_SCHEDULE`: Default schedule (1min/10min/hourly/daily/disabled)

**Schedule Mapping**:
```python
SCHEDULE_MAP = {
    '1min': 'cron(0/1 * * * ? *)',
    '10min': 'cron(0/10 * * * ? *)',
    'hourly': 'cron(0 * * * ? *)',
    'daily': 'cron(0 0 * * ? *)',
    'disabled': None
}
```

### 2. CrawlerCompletionHandler

**Purpose**: Send notifications when crawlers complete

**Trigger**: EventBridge rule on Glue Crawler State Change events

**Process**:
1. Receive crawler completion event
2. Query Glue for crawler and table details
3. Send SNS notification with discovered tables

### 3. Glue Crawlers

**Naming**: `{stack-name}-{BLOCKCHAIN}-Crawler`

**Configuration**:
- `Schedule`: Cron expression set at creation time
- `RecrawlBehavior`: CRAWL_NEW_FOLDERS_ONLY (cost optimization)
- `SchemaChangePolicy.UpdateBehavior`: LOG (required for CRAWL_NEW_FOLDERS_ONLY)
- `SchemaChangePolicy.DeleteBehavior`: LOG (required for CRAWL_NEW_FOLDERS_ONLY)

**Note**: When using `CRAWL_NEW_FOLDERS_ONLY`, AWS Glue requires both `UpdateBehavior` and `DeleteBehavior` to be set to `LOG`.

---

## Data Flow

### New Blockchain Discovery

```
1. New blockchain added to S3: s3://aws-public-blockchain/v1.0/sol/

2. Discovery Lambda runs (weekly or manual)
   - Scans S3, finds "sol" namespace
   
3. Creates resources:
   - Database: sol
   - Crawler: {stack}-SOL-Crawler (with daily schedule)
   
4. Starts crawler immediately

5. Crawler infers schema from Parquet metadata
   - Creates tables: sol.blocks, sol.transactions, etc.
   
6. SNS notification sent

7. Data queryable in Athena:
   SELECT * FROM sol.blocks LIMIT 10;
```

### Schedule Management

Schedules are managed directly via AWS CLI or Console:

```bash
# Update to hourly
aws glue update-crawler \
  --name {stack}-SOL-Crawler \
  --schedule "cron(0 * * * ? *)"

# Disable schedule
aws glue update-crawler \
  --name {stack}-SOL-Crawler \
  --schedule ""
```

---

## Design Decisions

### 1. Native Glue Scheduling

**Decision**: Use Glue's built-in crawler scheduling instead of EventBridge

**Rationale**:
- Simpler architecture (no separate EventBridge rules)
- Schedule is set at crawler creation time
- Standard AWS tooling for management (Console, CLI)
- Fewer IAM roles and permissions required

### 2. Default Daily Schedule

**Decision**: New crawlers default to daily

**Rationale**:
- Cost-effective baseline
- Blockchain data is append-only (historical doesn't change)
- Users can upgrade specific chains as needed via CLI

### 3. CRAWL_NEW_FOLDERS_ONLY with LOG Policies

**Decision**: Use incremental crawling with LOG-only schema policies

**Rationale**:
- Cost optimization (only crawl new data)
- AWS requirement: CRAWL_NEW_FOLDERS_ONLY requires LOG for both UpdateBehavior and DeleteBehavior
- Schema changes are logged but don't modify existing tables

### 4. No Separate Schedule Manager Lambda

**Decision**: Remove dedicated Lambda for schedule management

**Rationale**:
- AWS CLI/Console provides same functionality
- Reduces complexity and maintenance
- Fewer resources to deploy and monitor

---

## Cost Analysis

### Per-Chain Monthly Costs

| Schedule | Runs/Month | Est. Glue Cost |
|----------|------------|----------------|
| 1min | 43,200 | $50-100+ |
| 10min | 4,320 | $5-10 |
| hourly | 720 | $1-2 |
| daily | 30 | $0.50 |

### Recommendations

- **Production**: Use `daily` for most chains
- **Active development**: Use `hourly` for chains under active query
- **Real-time dashboards**: Use `10min` or `1min` (monitor costs)
- **Inactive chains**: Disable schedule and trigger manually

---

## Security

### IAM Roles

| Role | Purpose | Key Permissions |
|------|---------|-----------------|
| GlueCrawlerRole | Crawler execution | S3 read, Glue catalog |
| BlockchainDiscoveryRole | Discovery Lambda | S3 list, Glue create/start |
| CrawlerCompletionHandlerRole | Completion Lambda | Glue read, SNS publish |

### Resource Scoping

All crawlers are scoped to `{stack-name}-*` pattern.

---

## Extensibility

### Adding Custom Schedules

Modify `SCHEDULE_MAP` in BlockchainDiscoveryFunction:
```python
SCHEDULE_MAP = {
    '1min': 'cron(0/1 * * * ? *)',
    '5min': 'cron(0/5 * * * ? *)',  # Add new option
    '10min': 'cron(0/10 * * * ? *)',
    'hourly': 'cron(0 * * * ? *)',
    'daily': 'cron(0 0 * * ? *)',
    'weekly': 'cron(0 0 ? * SUN *)',  # Add new option
    'disabled': None
}
```

### Custom Processing

Extend `CrawlerCompletionHandler` to:
- Trigger data pipelines
- Update dashboards
- Send Slack notifications
- Create Athena views

---

## Limitations

1. **Minimum schedule**: 1 minute (Glue cron limit)
2. **Parquet only**: Assumes data is in Parquet format
3. **S3 structure**: Assumes `{version}/{blockchain}/` structure
4. **Concurrent crawlers**: AWS Glue has soft limits on concurrent crawlers
5. **Schema changes**: With CRAWL_NEW_FOLDERS_ONLY, schema changes are logged but not applied

---

## Monitoring

### CloudWatch Metrics

- Crawler: `glue.driver.aggregate.numBytes`, `elapsedTime`
- Lambda: `Invocations`, `Errors`, `Duration`

### Logs

- `/aws-glue/crawlers` - Crawler execution
- `/aws/lambda/{stack}-BlockchainDiscovery` - Discovery
- `/aws/lambda/{stack}-CrawlerCompletionHandler` - Completions

### Alerts

Subscribe to SNS topic for:
- New blockchain discoveries
- Crawler completions
- Error notifications
