import sys
import json
import uuid
import boto3
from botocore.exceptions import ClientError


def list_my_buckets(s3_resource):
    print('Buckets:\n\t', *[b.name for b in s3_resource.buckets.all()], sep="\n\t")

def put_bucket_policy(s3_resource, bucket_name):
    put_rules = [{
        'ID': str(uuid.uuid4()),
        'Filter': {'Prefix': '/'},
        'Status': 'Enabled',
        'Expiration': {'Days': 14}
    }]
    bucket = s3_resource.Bucket(bucket_name)
    try:
        bucket.LifecycleConfiguration().put(
            LifecycleConfiguration={'Rules': put_rules})
    except Exception as e:
        print("Couldn't put lifecycle rules for bucket ", bucket_name)
        print(e)
        raise

def restrict_ip_addresses(bucket_name, ip_range):
    bucket_policy = {
        'Version': '2012-10-17',
        'Statement': [{
            'Sid': 'IPAllow',
            'Effect': 'Deny',
            'Principal': '*',
            'Action': 's3:*',
            'Resource': [
                f'arn:aws:s3:::{bucket_name}',
                f'arn:aws:s3:::{bucket_name}/*'
            ],
            'Condition': {
                'NotIpAddress': {
                    'aws:SourceIp': f'{ip_range}'
                }
            }
        }]
    }
    bucket_policy = json.dumps(bucket_policy)
    try:
        print('\nAttaching bucket policy to bucket:', bucket_name)
        s3 = boto3.client('s3')
        s3.put_bucket_policy(Bucket=bucket_name, Policy=bucket_policy)
    except Exception as e:
        print(f"Couldn't attach policy. Here's why: "
              f"{e.response['Error']['Message']}")
        raise

def create_my_bucket(s3_resource, bucket_name):
    list_my_buckets(s3_resource)

    try:
        print('\nCreating new bucket:', bucket_name)
        bucket = s3_resource.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                'LocationConstraint': s3_resource.meta.client.meta.region_name
            }
        )
    except ClientError as e:
        print(f"Couldn't create a bucket for the demo. Here's why: "
              f"{e.response['Error']['Message']}")
        raise

    bucket.wait_until_exists()
    list_my_buckets(s3_resource)
    print('Bucket created. Attaching policies...')
    restrict_ip_addresses(bucket_name, '103.149.143.82/32')
    print('Policy attached...')
    print('Putting bucket policy...')
    put_bucket_policy(s3_resource, bucket_name)

def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('bucket_name', help='The name of the bucket to create.')
    parser.add_argument('region', help='The region in which to create your bucket.')

    args = parser.parse_args()
    s3_resource = (
        boto3.resource('s3', region_name=args.region) if args.region
        else boto3.resource('s3'))
    try:
        create_my_bucket(s3_resource, args.bucket_name)
    except ClientError:
        print('Exiting bucket creation process.')


if __name__ == '__main__':
    main()
