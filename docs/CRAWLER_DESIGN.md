# AWS Glue Crawler Design Document
## Automatic Blockchain Schema Discovery Architecture

### Overview

This document describes the design and architecture of the automated blockchain schema discovery solution using AWS Glue Crawlers. The system automatically discovers new blockchain namespaces in the AWS Public Blockchain S3 bucket, infers schemas from Parquet metadata, and creates queryable Glue tables without manual intervention.

---

## Design Goals

1. **Zero-Touch Discovery**: Automatically detect and catalog new blockchains
2. **Schema Inference**: Read schemas directly from Parquet metadata
3. **Cost Optimization**: Minimize AWS costs while maintaining functionality
4. **Extensibility**: Support any blockchain structure without code changes
5. **Production Ready**: Include monitoring, notifications, and error handling

---

## Architecture Components

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  AWS Public Blockchain S3                    │
│  v1.0/btc/  v1.0/eth/  v1.1/ton/  v1.0/newchain/           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    AWS Glue Crawlers                         │
│  ┌──────────────┐  ┌──────┐  ┌──────┐  ┌──────┐           │
│  │   Master     │  │ BTC  │  │ ETH  │  │ TON  │           │
│  │   Crawler    │  │      │  │      │  │      │           │
│  └──────────────┘  └──────┘  └──────┘  └──────┘           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  AWS Glue Data Catalog                       │
│  blockchain_discovery  |  btc  |  eth  |  ton              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│         EventBridge → Lambda → SNS Notifications             │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Master Discovery Crawler

**Purpose**: Discovers new blockchain namespaces across the entire S3 bucket

**Configuration**:
- **Target**: `s3://aws-public-blockchain/`
- **Exclusions**: Known blockchains (btc, eth, ton)
- **Database**: `blockchain_discovery`
- **Schedule**: Weekly (Sunday 2 AM UTC)
- **Recrawl Policy**: `CRAWL_NEW_FOLDERS_ONLY`
- **Schema Policy**: `UPDATE_IN_DATABASE`, `MergeNewColumns`

**Behavior**:
1. Scans entire S3 bucket structure
2. Identifies new blockchain namespaces (folders not in exclusion list)
3. Reads sample Parquet files from each namespace
4. Infers schema from Parquet metadata
5. Creates tables in `blockchain_discovery` database
6. Detects partitions from S3 path structure

**Why This Design**:
- Single crawler handles unlimited future blockchains
- Exclusion pattern prevents duplicate processing
- `CRAWL_NEW_FOLDERS_ONLY` minimizes costs
- Weekly schedule balances freshness vs cost

#### 2. Per-Blockchain Crawlers

**Purpose**: Maintain schemas for known blockchains with dedicated databases

**Configuration** (example for BTC):
- **Target**: `s3://aws-public-blockchain/v1.0/btc/`
- **Database**: `btc`
- **Schedule**: Weekly
- **Recrawl Policy**: `CRAWL_NEW_FOLDERS_ONLY`
- **Schema Policy**: `UPDATE_IN_DATABASE`, `MergeNewColumns`

**Why Separate Crawlers**:
- Dedicated databases for organizational clarity
- Independent scheduling per blockchain
- Easier to manage permissions per blockchain
- Can customize configuration per blockchain

#### 3. EventBridge Scheduling

**Purpose**: Trigger crawlers on a schedule

**Configuration**:
- **Schedule Expression**: `cron(0 2 ? * SUN *)` (weekly)
- **Target**: Glue Crawler
- **State**: ENABLED (configurable via parameter)

**Why EventBridge**:
- Native AWS service for scheduling
- No additional infrastructure needed
- Easy to modify schedules
- Supports complex cron expressions

#### 4. Lambda Handler

**Purpose**: Process crawler completion events and send notifications

**Trigger**: EventBridge rule on Glue Crawler state changes

**Functionality**:
```python
def handler(event, context):
    # 1. Extract crawler details from event
    crawler_name = event['detail']['crawlerName']
    state = event['detail']['state']
    
    # 2. Get crawler metadata
    crawler = glue.get_crawler(Name=crawler_name)
    database_name = crawler['Crawler']['DatabaseName']
    
    # 3. List discovered tables
    tables = glue.get_tables(DatabaseName=database_name)
    
    # 4. Detect new blockchains
    if database_name == 'blockchain_discovery':
        # New blockchain detected!
        
    # 5. Build notification message
    message = build_notification(crawler_name, tables)
    
    # 6. Publish to SNS
    sns.publish(TopicArn=topic_arn, Message=message)
```

**Why Lambda**:
- Event-driven processing
- No servers to manage
- Minimal cost (free tier covers usage)
- Easy to extend with custom logic

#### 5. SNS Notifications

**Purpose**: Alert stakeholders of discoveries and changes

**Configuration**:
- **Encryption**: KMS
- **Subscriptions**: Email (extensible to Slack, Lambda, etc.)

**Notification Content**:
- Crawler name and status
- Database name
- List of discovered tables
- Column counts
- S3 locations
- New blockchain alerts

**Why SNS**:
- Simple pub/sub model
- Multiple subscription types
- Reliable delivery
- Easy to add new subscribers

---

## Data Flow

### Discovery Flow for New Blockchain

```
1. New Blockchain Added to S3
   s3://aws-public-blockchain/v1.0/sol/blocks/
   s3://aws-public-blockchain/v1.0/sol/transactions/

2. Master Crawler Runs (Weekly Schedule)
   EventBridge → Glue Crawler

3. Crawler Scans S3
   - Lists objects in bucket
   - Identifies new prefix: v1.0/sol/
   - Not in exclusion list → Process

4. Schema Inference
   - Downloads sample Parquet file
   - Reads Parquet metadata
   - Extracts schema (columns, types)
   - Detects partitions from path

5. Table Creation
   - Creates sol_blocks in blockchain_discovery
   - Creates sol_transactions in blockchain_discovery
   - Sets location, schema, partitions

6. Event Processing
   - Crawler completes → EventBridge event
   - Lambda handler triggered
   - Analyzes tables
   - Detects new blockchain

7. Notification
   - Lambda publishes to SNS
   - Email sent to subscribers
   - "New Blockchain Detected: sol"

8. Data Available
   - Tables queryable in Athena
   - Zero manual work required
```

### Schema Update Flow

```
1. Schema Change in Existing Blockchain
   - New column added to eth.blocks
   - blob_gas_used field

2. ETH Crawler Runs (Weekly Schedule)
   - Scans s3://aws-public-blockchain/v1.0/eth/

3. Schema Detection
   - Reads latest Parquet files
   - Compares with existing table schema
   - Detects new column

4. Table Update
   - Schema Policy: MergeNewColumns
   - Adds blob_gas_used to eth.blocks
   - Preserves existing columns
   - Backward compatible

5. Notification
   - Lambda detects schema change
   - Sends notification
   - "Schema Updated: ETH"

6. Queries Continue Working
   - Old queries: Still work (ignore new column)
   - New queries: Can use new column
```

---

## Design Decisions

### 1. Master Crawler vs Individual Crawlers

**Decision**: Use both

**Rationale**:
- Master crawler: Handles unknown future blockchains
- Individual crawlers: Provide dedicated databases for known chains
- Exclusion pattern prevents duplication
- Best of both worlds: automation + organization

**Alternative Considered**: Single master crawler only
- Pros: Simpler
- Cons: All blockchains in one database, less organizational clarity

### 2. Weekly Schedule

**Decision**: Weekly crawling (Sunday 2 AM UTC)

**Rationale**:
- Balances freshness vs cost
- Blockchain data typically stable day-to-day
- New blockchains added infrequently
- 75% cost savings vs daily

**Alternative Considered**: Daily crawling
- Pros: More up-to-date
- Cons: 4× cost, minimal benefit

### 3. CRAWL_NEW_FOLDERS_ONLY

**Decision**: Only scan new folders

**Rationale**:
- Massive cost savings (90%+ reduction)
- Blockchain data is immutable (historical data doesn't change)
- New data appears in new date partitions
- Schema changes detected in new files

**Alternative Considered**: CRAWL_EVERYTHING
- Pros: Catches all changes
- Cons: Scans terabytes unnecessarily, high cost

### 4. Schema Change Policy: MergeNewColumns

**Decision**: Merge new columns, log deletions

**Rationale**:
- Backward compatible (existing queries don't break)
- Captures schema evolution
- Deletions logged but not applied (safety)
- Aligns with blockchain data patterns (additive changes)

**Alternative Considered**: LOG only
- Pros: No automatic changes
- Cons: Manual intervention required for updates

### 5. Discovery Database

**Decision**: Separate `blockchain_discovery` database for new blockchains

**Rationale**:
- Clear separation: known vs unknown blockchains
- Easy to identify new discoveries
- Can promote to dedicated database later
- Doesn't pollute existing databases

**Alternative Considered**: All in one database
- Pros: Simpler
- Cons: Harder to identify new blockchains, organizational issues

### 6. Lambda for Notifications

**Decision**: Lambda processes crawler events

**Rationale**:
- Event-driven (only runs when needed)
- Can add custom logic (Slack, PagerDuty, etc.)
- Minimal cost
- Easy to extend

**Alternative Considered**: SNS directly from EventBridge
- Pros: Simpler
- Cons: Limited notification customization, can't detect new blockchains

---

## Schema Inference

### How It Works

1. **Parquet Metadata Reading**
   ```
   Parquet File Structure:
   ├── Metadata
   │   ├── Schema (column names, types)
   │   ├── Row count
   │   └── Compression info
   └── Data blocks
   ```

2. **Type Mapping**
   ```
   Arrow Type → Glue Type
   int32      → int
   int64      → bigint
   float      → float
   double     → double
   string     → string
   bool       → boolean
   timestamp  → timestamp
   list       → array<type>
   struct     → struct<fields>
   ```

3. **Partition Detection**
   ```
   S3 Path: s3://bucket/v1.0/btc/blocks/date=2024-01-01/file.parquet
   Detected Partition: date (string)
   ```

4. **Complex Type Handling**
   ```
   Nested structures automatically inferred:
   - Arrays: array<string>
   - Structs: struct<field1:type1,field2:type2>
   - Maps: map<key_type,value_type>
   ```

### Why This Works

- **Parquet is self-describing**: Metadata includes complete schema
- **No guessing required**: Types are explicit in metadata
- **Handles complexity**: Nested structures preserved
- **Blockchain agnostic**: Works for any data structure

---

## Cost Analysis

### Monthly Cost Breakdown

| Component | Usage | Unit Cost | Monthly Cost |
|-----------|-------|-----------|--------------|
| Master Crawler | 4 runs × 5 min | $0.44/DPU-hour | $0.44 |
| BTC Crawler | 4 runs × 3 min | $0.44/DPU-hour | $0.26 |
| ETH Crawler | 4 runs × 3 min | $0.44/DPU-hour | $0.26 |
| TON Crawler | 4 runs × 3 min | $0.44/DPU-hour | $0.26 |
| Lambda | 16 invocations × 128MB | $0.0000002/request | $0.00 |
| SNS | 16 notifications | $0.50/million | $0.00 |
| S3 Requests | ~1000 GET | $0.0004/1000 | $0.01 |
| Glue Catalog | ~50 tables | $1.00/100k objects | $1.00 |
| EventBridge | 4 rules | Free | $0.00 |
| **Total** | | | **$2.23/month** |

### Cost Optimization Strategies

1. **Weekly vs Daily**: 75% savings
2. **CRAWL_NEW_FOLDERS_ONLY**: 90% savings on data scanned
3. **Exclusion patterns**: Prevents duplicate scanning
4. **Requester pays**: S3 costs borne by requester
5. **Minimal Lambda**: Free tier covers usage

### Scaling Costs

- **10 blockchains**: ~$4-5/month (linear scaling)
- **100 blockchains**: ~$30-40/month (still minimal)
- **Cost per blockchain**: ~$0.50/month

---

## Security Design

### IAM Roles

#### GlueCrawlerRole
```yaml
Permissions:
  - s3:GetObject, s3:ListBucket (read-only on public bucket)
  - glue:*Database*, glue:*Table* (catalog management)
  - logs:CreateLogGroup, logs:CreateLogStream (CloudWatch)

Trust Policy:
  - Service: glue.amazonaws.com
```

#### EventBridgeGlueRole
```yaml
Permissions:
  - glue:StartCrawler (trigger only)

Trust Policy:
  - Service: events.amazonaws.com
```

#### LambdaExecutionRole
```yaml
Permissions:
  - glue:GetCrawler, glue:GetTables (read-only)
  - sns:Publish (notifications)
  - logs:* (CloudWatch)

Trust Policy:
  - Service: lambda.amazonaws.com
```

### Encryption

- **S3**: AES256 (bucket default)
- **Athena Results**: SSE-S3
- **SNS**: KMS encryption
- **Data in Transit**: HTTPS only (enforced by bucket policy)

### Network Security

- **VPC Endpoints**: Optional (for private connectivity)
- **Security Groups**: Not required (serverless services)
- **Bucket Policy**: Force HTTPS, deny unencrypted

### Audit Trail

- **CloudTrail**: All API calls logged
- **CloudWatch**: Crawler execution logs
- **EventBridge**: State change events
- **SNS**: Notification history

---

## Extensibility

### Adding Custom Processing

Extend Lambda handler:
```python
def handler(event, context):
    # Existing logic...
    
    if new_blockchain_detected:
        # Custom logic
        send_slack_notification()
        trigger_data_pipeline()
        create_athena_views()
        update_documentation()
```

### Adding New Blockchain Crawler

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

# Add to master crawler exclusions
MasterBlockchainCrawler:
  Properties:
    Targets:
      S3Targets:
        - Exclusions:
            - "v1.0/sol/**"  # Exclude from master
```

### Custom Notification Channels

Add to SNS topic:
```bash
# Slack
aws sns subscribe --topic-arn $TOPIC_ARN \
  --protocol https \
  --notification-endpoint https://hooks.slack.com/...

# Lambda
aws sns subscribe --topic-arn $TOPIC_ARN \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:...
```

---

## Limitations and Considerations

### Current Limitations

1. **Requester Pays**: S3 bucket requires requester pays
2. **Parquet Only**: Assumes data is in Parquet format
3. **Weekly Schedule**: Not real-time (configurable)
4. **Single Region**: Crawlers run in one region

### Design Constraints

1. **S3 Structure**: Assumes blockchain/table/partition structure
2. **Partition Format**: Expects Hive-style partitions (key=value)
3. **Schema Stability**: Assumes schemas don't change drastically
4. **Naming Convention**: Table names derived from S3 paths

### Scalability Considerations

1. **Crawler Concurrency**: Limited by AWS Glue quotas
2. **Table Count**: Glue Data Catalog has soft limits
3. **S3 Listing**: Large buckets may take longer to scan
4. **Lambda Timeout**: 5 minutes max for notification processing

### Mitigation Strategies

1. **Quotas**: Request increases if needed
2. **Pagination**: Handle large result sets
3. **Timeouts**: Increase Lambda timeout if needed
4. **Monitoring**: CloudWatch alarms on failures

---

## Monitoring and Observability

### CloudWatch Metrics

**Crawler Metrics**:
- `glue.driver.aggregate.numBytes` - Data scanned
- `glue.driver.aggregate.elapsedTime` - Runtime
- `glue.ALL.s3.listRequest.count` - S3 API calls

**Lambda Metrics**:
- `Invocations` - Handler executions
- `Errors` - Failed invocations
- `Duration` - Processing time

### CloudWatch Logs

**Log Groups**:
- `/aws-glue/crawlers` - Crawler execution logs
- `/aws/lambda/CrawlerCompletionHandler` - Lambda logs

**Log Retention**: 7 days (configurable)

### Alarms (Recommended)

```yaml
CrawlerFailureAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    MetricName: glue.driver.aggregate.numFailedTasks
    Threshold: 1
    AlarmActions:
      - !Ref SNSTopicArn
```

---

## Comparison with Alternatives

### Manual CloudFormation

**Pros**:
- Full control over schema
- Version controlled
- Explicit definitions

**Cons**:
- 2-4 hours per blockchain
- Error-prone
- Doesn't scale
- Manual updates required

### AWS Glue Crawlers (This Design)

**Pros**:
- Automatic discovery
- Zero manual work
- Scales infinitely
- Always up-to-date

**Cons**:
- Less control
- ~$2-5/month cost
- Weekly latency

### Hybrid Approach

**Pros**:
- Automation + version control
- Best of both worlds

**Cons**:
- More complex
- Requires discipline

---

## Future Enhancements

### Potential Improvements

1. **Real-time Discovery**: S3 event notifications → Lambda → Crawler
2. **Schema Validation**: Automated testing of discovered schemas
3. **Data Quality Checks**: Validate data after discovery
4. **Dashboard Generation**: Auto-create QuickSight dashboards
5. **Multi-Region**: Replicate catalog across regions
6. **Schema Registry**: Version history and comparison
7. **Breaking Change Detection**: Alert on incompatible changes
8. **Cost Optimization**: ML-based schedule optimization

### Integration Opportunities

1. **Data Pipelines**: Trigger ETL on new blockchain
2. **CI/CD**: Automated testing of new schemas
3. **Documentation**: Auto-generate schema docs
4. **Governance**: Integrate with data catalog tools
5. **Analytics**: Feed discovery events to analytics platform

---

## Conclusion

This design provides a scalable, cost-effective solution for automatically discovering and cataloging blockchain data. Key design principles:

1. **Automation First**: Minimize manual intervention
2. **Cost Conscious**: Optimize for minimal AWS spend
3. **Extensible**: Support any blockchain structure
4. **Production Ready**: Include monitoring and notifications
5. **Future Proof**: Handle unknown blockchains automatically

The architecture balances automation with control, providing a foundation that scales from 3 blockchains to 100+ without modification.
