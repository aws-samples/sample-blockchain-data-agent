# AWS Glue Crawler Design Document
## Automatic Blockchain Schema Discovery Architecture

### Overview

This document describes the architecture of the automated blockchain schema discovery solution. The system automatically discovers new blockchain namespaces in the AWS Public Blockchain S3 bucket, creates dedicated databases per blockchain, infers schemas from Parquet metadata, creates crawlers, and sets up configurable schedules.

---

## Design Goals

1. **Zero-Touch Discovery**: Automatically detect and catalog new blockchains
2. **Database Per Blockchain**: Each blockchain gets its own dedicated Glue database
3. **Configurable Schedules**: Per-chain crawler schedules (1min, 10min, hourly, daily)
4. **Cost Optimization**: Default to daily crawls, allow fine-tuning per chain
5. **Extensibility**: Support any blockchain structure without code changes

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
│  3. Creates Glue crawler per blockchain                     │
│  4. Creates EventBridge schedule per crawler                │
│  5. Starts crawlers on first creation                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              CrawlerScheduleManager (Lambda)                 │
│  - List all schedules                                       │
│  - Get/Set schedule per blockchain                          │
│  - Disable schedules                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              EventBridge Schedules (per chain)               │
│  {stack}-BTC-Schedule: rate(1 day)                         │
│  {stack}-ETH-Schedule: rate(1 hour)                        │
│  {stack}-TON-Schedule: rate(10 minutes)                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    AWS Glue Crawlers                         │
│  {stack}-BTC-Crawler → btc database                        │
│  {stack}-ETH-Crawler → eth database                        │
│  {stack}-TON-Crawler → ton database                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  AWS Glue Data Catalog                       │
│       btc  |  eth  |  ton  |  (auto-created)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. BlockchainDiscoveryFunction

**Purpose**: Discovers blockchains and creates all necessary resources

**Trigger**: 
- EventBridge schedule (weekly by default)
- Manual invocation

**Process**:
1. Scan S3 bucket for blockchain namespaces (v1.0/*, v1.1/*)
2. For each discovered blockchain:
   - Create Glue database if not exists
   - Create Glue crawler if not exists
   - Create EventBridge schedule if crawler is new
   - Start crawler on first creation
3. Send SNS notification with discovery report

**Environment Variables**:
- `S3_BUCKET`: Source bucket
- `SCHEMA_VERSION`: Default schema version
- `SCHEMA_VERSION_TON`: TON schema version
- `CRAWLER_ROLE_ARN`: IAM role for crawlers
- `STACK_NAME`: CloudFormation stack name
- `SNS_TOPIC_ARN`: Notification topic
- `DEFAULT_CRAWLER_SCHEDULE`: Default schedule (1min/10min/hourly/daily)
- `EVENTBRIDGE_ROLE_ARN`: Role for EventBridge to start crawlers

### 2. CrawlerScheduleManager

**Purpose**: Manage per-chain crawler schedules

**Actions**:
- `list`: List all crawler schedules
- `get`: Get schedule for specific blockchain
- `set`: Set schedule (1min, 10min, hourly, daily)
- `disable`: Remove schedule (manual-only mode)

**Schedule Mapping**:
```python
SCHEDULE_MAP = {
    '1min': 'rate(1 minute)',
    '10min': 'rate(10 minutes)',
    'hourly': 'rate(1 hour)',
    'daily': 'rate(1 day)'
}
```

### 3. EventBridge Schedules

**Naming**: `{stack-name}-{BLOCKCHAIN}-Schedule`

**Target**: Glue crawler ARN with EventBridgeGlueRole

**States**: ENABLED or deleted (for disabled)

### 4. Glue Crawlers

**Naming**: `{stack-name}-{BLOCKCHAIN}-Crawler`

**Configuration**:
- `RecrawlBehavior`: CRAWL_NEW_FOLDERS_ONLY (cost optimization)
- `UpdateBehavior`: UPDATE_IN_DATABASE
- `DeleteBehavior`: LOG

### 5. EventBridgeGlueRole

**Purpose**: Allow EventBridge to start Glue crawlers

**Permissions**: `glue:StartCrawler` on stack crawlers

---

## Data Flow

### New Blockchain Discovery

```
1. New blockchain added to S3: s3://aws-public-blockchain/v1.0/sol/

2. Discovery Lambda runs (weekly or manual)
   - Scans S3, finds "sol" namespace
   
3. Creates resources:
   - Database: sol
   - Crawler: {stack}-SOL-Crawler
   - Schedule: {stack}-SOL-Schedule (daily by default)
   
4. Starts crawler immediately

5. Crawler infers schema from Parquet metadata
   - Creates tables: sol.blocks, sol.transactions, etc.
   
6. SNS notification sent

7. Data queryable in Athena:
   SELECT * FROM sol.blocks LIMIT 10;
```

### Schedule Change

```
1. User invokes CrawlerScheduleManager:
   {"action": "set", "blockchain": "SOL", "schedule": "hourly"}

2. Lambda updates EventBridge rule:
   - Rule: {stack}-SOL-Schedule
   - Expression: rate(1 hour)
   
3. Crawler now runs hourly
```

---

## Design Decisions

### 1. Per-Chain Schedules

**Decision**: Each blockchain has its own configurable schedule

**Rationale**:
- Different chains have different update frequencies
- Cost optimization (don't over-crawl inactive chains)
- Flexibility for real-time vs batch use cases

### 2. EventBridge for Scheduling

**Decision**: Use EventBridge rules instead of Glue native scheduling

**Rationale**:
- Dynamic creation/modification via API
- Consistent naming convention
- Easy to list/manage all schedules
- Can be disabled without deleting crawler

### 3. Default Daily Schedule

**Decision**: New crawlers default to daily

**Rationale**:
- Cost-effective baseline
- Blockchain data is append-only (historical doesn't change)
- Users can upgrade specific chains as needed

### 4. Discovery Creates Schedules

**Decision**: Discovery Lambda creates schedules for new crawlers only

**Rationale**:
- Existing schedules are preserved (user customizations)
- New chains get sensible defaults
- Idempotent operation

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
- **Inactive chains**: Use `disable` and trigger manually

---

## Security

### IAM Roles

| Role | Purpose | Key Permissions |
|------|---------|-----------------|
| GlueCrawlerRole | Crawler execution | S3 read, Glue catalog |
| BlockchainDiscoveryRole | Discovery Lambda | S3 list, Glue create, Events create |
| CrawlerScheduleManagerRole | Schedule Lambda | Events CRUD |
| EventBridgeGlueRole | Start crawlers | glue:StartCrawler |

### Resource Scoping

All EventBridge rules and crawlers are scoped to `{stack-name}-*` pattern.

---

## Extensibility

### Adding Custom Schedules

Modify `SCHEDULE_MAP` in both Lambdas:
```python
SCHEDULE_MAP = {
    '1min': 'rate(1 minute)',
    '5min': 'rate(5 minutes)',  # Add new option
    '10min': 'rate(10 minutes)',
    'hourly': 'rate(1 hour)',
    'daily': 'rate(1 day)',
    'weekly': 'rate(7 days)'  # Add new option
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

1. **Minimum schedule**: 1 minute (EventBridge limit)
2. **Parquet only**: Assumes data is in Parquet format
3. **S3 structure**: Assumes `{version}/{blockchain}/` structure
4. **Concurrent crawlers**: AWS Glue has soft limits on concurrent crawlers

---

## Monitoring

### CloudWatch Metrics

- Crawler: `glue.driver.aggregate.numBytes`, `elapsedTime`
- Lambda: `Invocations`, `Errors`, `Duration`
- EventBridge: `TriggeredRules`, `FailedInvocations`

### Logs

- `/aws-glue/crawlers` - Crawler execution
- `/aws/lambda/{stack}-BlockchainDiscovery` - Discovery
- `/aws/lambda/{stack}-CrawlerScheduleManager` - Schedule changes
- `/aws/lambda/{stack}-CrawlerCompletionHandler` - Completions

### Alerts

Subscribe to SNS topic for:
- New blockchain discoveries
- Crawler completions
- Error notifications
