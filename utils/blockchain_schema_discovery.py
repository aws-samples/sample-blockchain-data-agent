#!/usr/bin/env python3
"""
Blockchain Schema Discovery Utility

This script helps discover and manage blockchain schemas in the AWS Public Blockchain
S3 bucket. It can:
1. List all blockchain namespaces in the bucket
2. Discover schema for a specific blockchain
3. Generate CloudFormation templates for new blockchains
4. Trigger Glue crawlers manually
5. Export discovered schemas to various formats
"""

import boto3
import json
import argparse
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pyarrow.parquet as pq
from io import BytesIO


class BlockchainSchemaDiscovery:
    """Utility class for discovering blockchain schemas from S3."""
    
    def __init__(self, bucket_name: str = "aws-public-blockchain", region: str = "us-east-1"):
        """
        Initialize the discovery utility.
        
        Args:
            bucket_name: S3 bucket containing blockchain data
            region: AWS region
        """
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.glue_client = boto3.client('glue', region_name=region)
        
    def list_blockchain_namespaces(self, schema_version: str = "v1.0") -> List[str]:
        """
        List all blockchain namespaces in the S3 bucket.
        
        Args:
            schema_version: Schema version to scan (e.g., 'v1.0', 'v1.1')
            
        Returns:
            List of blockchain namespace names
        """
        print(f"🔍 Scanning S3 bucket: s3://{self.bucket_name}/{schema_version}/")
        
        blockchains = set()
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=f"{schema_version}/",
                Delimiter='/',
                RequestPayer='requester'
            )
            
            for page in pages:
                for prefix in page.get('CommonPrefixes', []):
                    # Extract blockchain name from prefix
                    # Format: v1.0/blockchain_name/
                    parts = prefix['Prefix'].strip('/').split('/')
                    if len(parts) >= 2:
                        blockchain = parts[1]
                        blockchains.add(blockchain)
            
            blockchain_list = sorted(list(blockchains))
            print(f"✅ Found {len(blockchain_list)} blockchain(s): {', '.join(blockchain_list)}")
            return blockchain_list
            
        except Exception as e:
            print(f"❌ Error listing blockchains: {e}")
            return []
    
    def list_tables_for_blockchain(self, blockchain: str, schema_version: str = "v1.0") -> List[str]:
        """
        List all table types for a specific blockchain.
        
        Args:
            blockchain: Blockchain name (e.g., 'btc', 'eth', 'ton')
            schema_version: Schema version
            
        Returns:
            List of table names
        """
        print(f"🔍 Discovering tables for {blockchain}...")
        
        tables = set()
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            prefix = f"{schema_version}/{blockchain}/"
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/',
                RequestPayer='requester'
            )
            
            for page in pages:
                for prefix_obj in page.get('CommonPrefixes', []):
                    # Extract table name from prefix
                    # Format: v1.0/blockchain/table_name/
                    parts = prefix_obj['Prefix'].strip('/').split('/')
                    if len(parts) >= 3:
                        table = parts[2]
                        tables.add(table)
            
            table_list = sorted(list(tables))
            print(f"✅ Found {len(table_list)} table(s): {', '.join(table_list)}")
            return table_list
            
        except Exception as e:
            print(f"❌ Error listing tables: {e}")
            return []
    
    def discover_schema_from_parquet(
        self, 
        blockchain: str, 
        table: str, 
        schema_version: str = "v1.0"
    ) -> Optional[Dict]:
        """
        Discover schema by reading Parquet file metadata.
        
        Args:
            blockchain: Blockchain name
            table: Table name
            schema_version: Schema version
            
        Returns:
            Dictionary containing schema information
        """
        print(f"📊 Discovering schema for {blockchain}.{table}...")
        
        try:
            # Find a sample parquet file
            prefix = f"{schema_version}/{blockchain}/{table}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=10,
                RequestPayer='requester'
            )
            
            # Find first .parquet file
            parquet_key = None
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.parquet'):
                    parquet_key = obj['Key']
                    break
            
            if not parquet_key:
                print(f"⚠️  No parquet files found in {prefix}")
                return None
            
            print(f"📄 Reading schema from: s3://{self.bucket_name}/{parquet_key}")
            
            # Download and read parquet metadata
            obj = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=parquet_key,
                RequestPayer='requester'
            )
            
            parquet_file = pq.ParquetFile(BytesIO(obj['Body'].read()))
            schema = parquet_file.schema_arrow
            
            # Convert to dictionary format
            columns = []
            for field in schema:
                columns.append({
                    'name': field.name,
                    'type': self._arrow_to_glue_type(str(field.type)),
                    'arrow_type': str(field.type),
                    'nullable': field.nullable
                })
            
            # Check for partitions
            partitions = self._detect_partitions(prefix)
            
            schema_info = {
                'blockchain': blockchain,
                'table': table,
                'schema_version': schema_version,
                'location': f"s3://{self.bucket_name}/{prefix}",
                'columns': columns,
                'partitions': partitions,
                'discovered_at': datetime.now().isoformat(),
                'sample_file': parquet_key
            }
            
            print(f"✅ Discovered {len(columns)} columns")
            return schema_info
            
        except Exception as e:
            print(f"❌ Error discovering schema: {e}")
            return None
    
    def _arrow_to_glue_type(self, arrow_type: str) -> str:
        """Convert Arrow type to Glue/Hive type."""
        type_mapping = {
            'int32': 'int',
            'int64': 'bigint',
            'float': 'float',
            'double': 'double',
            'string': 'string',
            'bool': 'boolean',
            'timestamp': 'timestamp',
            'date32': 'date',
            'binary': 'binary',
        }
        
        # Handle complex types
        if 'list' in arrow_type.lower():
            return f"array<{arrow_type}>"
        elif 'struct' in arrow_type.lower():
            return f"struct<{arrow_type}>"
        elif 'decimal' in arrow_type.lower():
            return arrow_type.replace('decimal128', 'decimal')
        
        # Simple type lookup
        for arrow, glue in type_mapping.items():
            if arrow in arrow_type.lower():
                return glue
        
        return 'string'  # Default fallback
    
    def _detect_partitions(self, prefix: str) -> List[Dict]:
        """Detect partition keys from S3 path structure."""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/',
                MaxKeys=5,
                RequestPayer='requester'
            )
            
            # Look for partition patterns like date=2024-01-01/
            partitions = []
            for prefix_obj in response.get('CommonPrefixes', []):
                path = prefix_obj['Prefix']
                parts = path.strip('/').split('/')
                
                for part in parts:
                    if '=' in part:
                        key, _ = part.split('=', 1)
                        if key not in [p['name'] for p in partitions]:
                            partitions.append({
                                'name': key,
                                'type': 'string'  # Default to string
                            })
            
            return partitions
            
        except Exception as e:
            print(f"⚠️  Could not detect partitions: {e}")
            return []
    
    def generate_cloudformation_table(self, schema_info: Dict) -> str:
        """
        Generate CloudFormation YAML for a Glue table.
        
        Args:
            schema_info: Schema information from discover_schema_from_parquet
            
        Returns:
            CloudFormation YAML string
        """
        blockchain = schema_info['blockchain'].upper()
        table = schema_info['table']
        table_name_cf = ''.join(word.capitalize() for word in table.split('_'))
        
        # Generate columns YAML
        columns_yaml = []
        for col in schema_info['columns']:
            columns_yaml.append(f"            - Name: {col['name']}")
            columns_yaml.append(f"              Type: {col['type']}")
        
        # Generate partitions YAML
        partitions_yaml = []
        for part in schema_info['partitions']:
            partitions_yaml.append(f"          - Name: {part['name']}")
            partitions_yaml.append(f"            Type: {part['type']}")
        
        template = f"""
  GlueTable{table_name_cf}{blockchain}:
    Type: AWS::Glue::Table
    Properties:
      CatalogId: !Ref AWS::AccountId
      DatabaseName: !Ref GlueDatabase{blockchain}
      TableInput:
        Owner: owner
        Retention: 0
        Name: {table}
        StorageDescriptor:
          Columns:
{chr(10).join(columns_yaml)}
          InputFormat: org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat
          Location: !Join
            - ""
            - - s3://
              - !Ref S3Bucket
              - /
              - !Ref SchemaVersion
              - /{schema_info['blockchain']}/{table}
          OutputFormat: org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat
          Compressed: false
          NumberOfBuckets: -1
          SerdeInfo:
            SerializationLibrary: org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe
            Parameters:
              serialization.format: "1"
          BucketColumns: []
          SortColumns: []
          StoredAsSubDirectories: false
        PartitionKeys:
{chr(10).join(partitions_yaml) if partitions_yaml else '          []'}
        TableType: EXTERNAL_TABLE
"""
        return template
    
    def trigger_crawler(self, crawler_name: str) -> bool:
        """
        Manually trigger a Glue crawler.
        
        Args:
            crawler_name: Name of the crawler to trigger
            
        Returns:
            True if successful, False otherwise
        """
        print(f"🚀 Starting crawler: {crawler_name}")
        
        try:
            self.glue_client.start_crawler(Name=crawler_name)
            print(f"✅ Crawler started successfully")
            return True
        except self.glue_client.exceptions.CrawlerRunningException:
            print(f"⚠️  Crawler is already running")
            return False
        except Exception as e:
            print(f"❌ Error starting crawler: {e}")
            return False
    
    def get_crawler_status(self, crawler_name: str) -> Optional[Dict]:
        """
        Get the status of a Glue crawler.
        
        Args:
            crawler_name: Name of the crawler
            
        Returns:
            Dictionary with crawler status information
        """
        try:
            response = self.glue_client.get_crawler(Name=crawler_name)
            crawler = response['Crawler']
            
            status = {
                'name': crawler['Name'],
                'state': crawler['State'],
                'database': crawler.get('DatabaseName', 'N/A'),
                'last_crawl': crawler.get('LastCrawl', {})
            }
            
            return status
        except Exception as e:
            print(f"❌ Error getting crawler status: {e}")
            return None
    
    def export_schema_to_json(self, schema_info: Dict, output_file: str):
        """Export schema information to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(schema_info, f, indent=2)
        print(f"✅ Schema exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Discover and manage blockchain schemas from AWS Public Blockchain S3 bucket'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List blockchains command
    list_parser = subparsers.add_parser('list-blockchains', help='List all blockchain namespaces')
    list_parser.add_argument('--schema-version', default='v1.0', help='Schema version to scan')
    
    # List tables command
    tables_parser = subparsers.add_parser('list-tables', help='List tables for a blockchain')
    tables_parser.add_argument('blockchain', help='Blockchain name (e.g., btc, eth, ton)')
    tables_parser.add_argument('--schema-version', default='v1.0', help='Schema version')
    
    # Discover schema command
    discover_parser = subparsers.add_parser('discover-schema', help='Discover schema for a table')
    discover_parser.add_argument('blockchain', help='Blockchain name')
    discover_parser.add_argument('table', help='Table name')
    discover_parser.add_argument('--schema-version', default='v1.0', help='Schema version')
    discover_parser.add_argument('--output', help='Output file for schema JSON')
    discover_parser.add_argument('--cloudformation', action='store_true', 
                                help='Generate CloudFormation template')
    
    # Trigger crawler command
    crawler_parser = subparsers.add_parser('trigger-crawler', help='Manually trigger a crawler')
    crawler_parser.add_argument('crawler_name', help='Name of the crawler')
    
    # Crawler status command
    status_parser = subparsers.add_parser('crawler-status', help='Get crawler status')
    status_parser.add_argument('crawler_name', help='Name of the crawler')
    
    # Common arguments
    parser.add_argument('--bucket', default='aws-public-blockchain', 
                       help='S3 bucket name')
    parser.add_argument('--region', default='us-east-1', 
                       help='AWS region')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Initialize discovery utility
    discovery = BlockchainSchemaDiscovery(bucket_name=args.bucket, region=args.region)
    
    # Execute command
    if args.command == 'list-blockchains':
        discovery.list_blockchain_namespaces(args.schema_version)
    
    elif args.command == 'list-tables':
        discovery.list_tables_for_blockchain(args.blockchain, args.schema_version)
    
    elif args.command == 'discover-schema':
        schema_info = discovery.discover_schema_from_parquet(
            args.blockchain, 
            args.table, 
            args.schema_version
        )
        
        if schema_info:
            print("\n📋 Schema Summary:")
            print(f"   Blockchain: {schema_info['blockchain']}")
            print(f"   Table: {schema_info['table']}")
            print(f"   Columns: {len(schema_info['columns'])}")
            print(f"   Partitions: {len(schema_info['partitions'])}")
            print(f"   Location: {schema_info['location']}")
            
            if args.output:
                discovery.export_schema_to_json(schema_info, args.output)
            
            if args.cloudformation:
                cf_template = discovery.generate_cloudformation_table(schema_info)
                print("\n📝 CloudFormation Template:")
                print(cf_template)
    
    elif args.command == 'trigger-crawler':
        discovery.trigger_crawler(args.crawler_name)
    
    elif args.command == 'crawler-status':
        status = discovery.get_crawler_status(args.crawler_name)
        if status:
            print(f"\n📊 Crawler Status:")
            print(f"   Name: {status['name']}")
            print(f"   State: {status['state']}")
            print(f"   Database: {status['database']}")
            if status['last_crawl']:
                print(f"   Last Crawl: {status['last_crawl']}")


if __name__ == '__main__':
    main()
