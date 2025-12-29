# AWS Glue Crawler Design Document
## Automatic Blockchain Schema Discovery Architecture

### Overview

This document describes the architecture of the automated blockchain schema discovery solution. The system automatically discovers new blockchain namespaces in the AWS Public Blockchain S3 bucket, creates dedicated databases per blockchain, infers schemas from Parquet metadata, and creates queryable Glue tables.

---

## Design Goals

1. **Zero-Touch Discovery**: Automatically detect and catalog new blockchains
2. **Database Per Blockchain**: Each blockchain gets its own dedicated Glue database
3. **Schema Inference**: Read schemas directly from Parquet metadata
4. **Cost Optimization**: Minimize AWS costs while maintaining functionality
5. **Extensibility**: Support any blockchain structure without code changes

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│                  AWS Public Blockchain S3                    │
│  v1.0/btc/  v1.0/eth/  v1.1/ton/  v1.0/newchain/           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              BlockchainDiscoveryFunction (Lambda)            │
│  1. Scans S3 for blockchain namespaces                      │
│  2. Compares against known blockchains                      │
│  3. Creates database for new blockchains                    │
│  4. Creates and starts crawler for each new blockchain      │
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
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         EventBridge → Lambda → SNS Notifications             │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. BlockchainDiscoveryFunction (Lambda)

**Purpose**: Discovers new blockchains and creates dedicated databases + crawlers

**Trigger**: EventBridge schedule (weekly) or manual invocation

**Process**:
```python
1. Scan S3 bucket for blockchain namespaces
   - List prefixes under v1.0/, v1.1/, etc.
   - Extract blockchain names (btc, eth, ton, etc.)

2. Compare against known blockchains
   - Known: btc, eth, ton (defined in CloudFormation)
   - New: Any blockchain not in known list

3. For each new blockchain:
   a. Create Glue database (e.g., "sol" for Solana)
   b. Determine S3 path (check schema versions)
   c. Create Glue crawler targeting that path
   d. Start the crawler immediately

4. Send SNS notification with discovery report
```

**Why Lambda Instead of Master Crawler**:
- Glue Crawlers cannot dynamically create databases
- Lambda can create both databases AND crawlers
- More control over naming and configuration
- Can start crawlers immediately after creation

### 2. Per-Blockchain Crawlers

**Purpose**: Maintain schemas for each blockchain in its dedicated database

**Configuration**:
- **Target**: `s3://aws-public-blockchain/{version}/{blockchain}/`
- **Database**: `{blockchain}` (e.g., `btc`, `eth`, `ton`)
- **Schedule**: Weekly (via EventBridge)
- **Recrawl Policy**: `CRAWL_NEW_FOLDERS_ONLY`
- **Schema Policy**: `UPDATE_IN_DATABASE`, `MergeNewColumns`

**Pre-defined Crawlers** (in CloudFormation):
- BTC Crawler → `btc` database
- ETH Crawler → `eth` database
- TON Crawler → `ton` database

**Auto-created Crawlers** (by Lambda):
- Created dynamically when new blockchains are discovered
- Same configuration as pre-defined crawlers

### 3. EventBridge Scheduling

**Discovery Schedule**:
- Triggers `BlockchainDiscoveryFunction` weekly
- Can be invoked manually anytime

**Crawler Schedules**:
- Each pre-defined crawler has its own EventBridge rule
- Auto-created crawlers can be triggered manually or via Lambda

### 4. Notification System

**CrawlerCompletionHandler Lambda**:
- Triggered by EventBridge on crawler state changes
- Sends SNS notifications on completion
- Reports discovered tables and schemas

**BlockchainDiscoveryFunction**:
- Sends SNS notification when new blockchains are discovered
- Reports created databases and crawlers

---

## Design Decisions

### 1. Database Per Blockchain

**Decision**: Each blockchain gets its own Glue database

**Rationale**:
- Clear organizational structure
- Easier permission management per blockchain
- Cleaner Athena queries (`SELECT * FROM btc.blocks`)
- Aligns with data domain boundaries

**Alternative Rejected**: Single `blockchain_discovery` database
- Cons: All tables mixed together, harder to manage

### 2. Lambda for Discovery

**Decision**: Use Lambda to discover blockchains and create resources

**Rationale**:
- Glue Crawlers can only create tables, not databases
- Lambda provides full control over resource creation
- Can implement custom logic (naming, configuration)
- Immediate crawler execution after creation

**Alternative Rejected**: Master Crawler approach
- Cons: Cannot create databases, all tables in one database

### 3. Pre-defined + Auto-created Crawlers

**Decision**: Pre-define crawlers for known blockchains, auto-create for new ones

**Rationale**:
- Known blockchains (BTC, ETH, TON) have stable configurations
- CloudFormation provides version control for known resources
- Lambda handles unknown future blockchains
- Best of both worlds: control + automation

### 4. Weekly Schedule

**Decision**: Weekly discovery and crawling (Sunday 2 AM UTC)

**Rationale**:
- Blockchain data is immutable (historical data doesn't change)
- New blockchains added infrequently
- 75% cost savings vs daily
- Manual trigger available for urgent needs

---

## Data Flow: New Blockchain Discovery

```
1. New Blockchain Added to S3
   s3://aws-public-blockchain/v1.0/sol/blocks/
   s3://aws-public-blockchain/v1.0/sol/transactions/

2. Discovery Lambda Runs (Weekly or Manual)
   - Scans S3: finds "sol" namespace
   - Compares: "sol" not in known list
   - Action: Process new blockchain

3. Database Creation
   glue.create_database(Name="sol", Description="Solana blockchain data")

4. Crawler Creation
   glue.create_crawler(
       Name="blockchain-crawlers-SOL-Crawler",
       DatabaseName="sol",
       Targets={"S3Targets": [{"Path": "s3://aws-public-blockchain/v1.0/sol/"}]}
   )

5. Crawler Execution
   glue.start_crawler(Name="blockchain-crawlers-SOL-Crawler")

6. Schema Inference
   - Crawler reads Parquet metadata
   - Creates tables: sol.blocks, sol.transactions
   - Detects partitions from S3 path

7. Notification
   SNS: "New Blockchain Discovered: sol"
   - Database created: sol
   - Crawler created: blockchain-crawlers-SOL-Crawler
   - Tables will be available after crawler completes

8. Data Available
   SELECT * FROM sol.blocks WHERE date = '2024-01-01';
```

---

## Schema Inference

### How Crawlers Infer Schemas

1. **Parquet Metadata**: Schemas embedded in file metadata
2. **Type Mapping**: Arrow types → Glue types
3. **Partition Detection**: Hive-style paths (key=value)
4. **Complex Types**: Nested structures preserved

### Type Mapping

| Parquet/Arrow | Glue Type |
|---------------|-----------|
| int32 | int |
| int64 | bigint |
| string | string |
| bool | boolean |
| timestamp | timestamp |
| list | array<type> |
| struct | struct<fields> |

---

## Cost Analysis

### Monthly Costs (~$2-5/month)

| Component | Cost |
|-----------|------|
| Lambda (Discovery + Completion) | ~$0.00 (free tier) |
| Glue Crawlers (4 × weekly) | ~$1.50 |
| Glue Data Catalog | ~$1.00 |
| SNS Notifications | ~$0.00 |
| EventBridge | ~$0.00 |

### Cost Optimization

1. **CRAWL_NEW_FOLDERS_ONLY**: 90% reduction in data scanned
2. **Weekly schedule**: 75% savings vs daily
3. **Lambda free tier**: Covers all invocations

---

## Security

### IAM Roles

**GlueCrawlerRole**:
- S3: GetObject, ListBucket (read-only)
- Glue: Database/Table management

**BlockchainDiscoveryRole**:
- S3: ListBucket, GetObject
- Glue: CreateDatabase, CreateCrawler, StartCrawler
- IAM: PassRole (for crawler role)
- SNS: Publish

**EventBridgeGlueRole**:
- Glue: StartCrawler only

### Encryption

- S3: AES256
- Athena Results: SSE-S3
- SNS: KMS encryption

---

## Extensibility

### Adding Custom Processing

Extend the Lambda handlers to:
- Send Slack notifications
- Trigger data pipelines
- Create Athena views
- Update documentation

### Manual Crawler Addition

For blockchains needing special configuration:

```yaml
SOLBlockchainCrawler:
  Type: AWS::Glue::Crawler
  Properties:
    Name: !Sub ${AWS::StackName}-SOL-Crawler
    Role: !GetAtt GlueCrawlerRole.Arn
    DatabaseName: !Ref GlueDatabaseSOL
    Targets:
      S3Targets:
        - Path: !Sub s3://${S3Bucket}/v1.0/sol/
```

---

## Limitations

1. **Parquet Only**: Assumes data is in Parquet format
2. **Weekly Latency**: Not real-time (configurable)
3. **S3 Structure**: Assumes blockchain/table/partition structure
4. **Naming Convention**: Database names derived from S3 paths

---

## Monitoring

### CloudWatch Metrics

- Crawler: `glue.driver.aggregate.numBytes`, `elapsedTime`
- Lambda: `Invocations`, `Errors`, `Duration`

### Logs

- `/aws-glue/crawlers` - Crawler execution
- `/aws/lambda/BlockchainDiscovery` - Discovery function
- `/aws/lambda/CrawlerCompletionHandler` - Completion handler

### Alerts

Subscribe to SNS topic for:
- New blockchain discoveries
- Crawler completions
- Error notifications

---

## Conclusion

This architecture provides automatic discovery and cataloging of blockchain data with:

1. **Separate database per blockchain** for clean organization
2. **Lambda-based discovery** for dynamic resource creation
3. **Pre-defined crawlers** for known blockchains
4. **Auto-created crawlers** for new blockchains
5. **Cost-effective** weekly scheduling with manual override
