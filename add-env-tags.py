import boto3

ec2_client_virginia = boto3.client('ec2', region_name="us-east-1")
ec2_resource_virginia = boto3.resource('ec2', region_name='us-east-1')

ec2_client_ohio = boto3.client('ec2', region_name="us-east-2")
ec2_resource_ohio = boto3.resource('ec2', region_name='us-east-2')

instance_ids_virginia = []
instance_ids_ohio = []

reservations_virginia = ec2_client_virginia.describe_instances()['Reservations']
for res in reservations_virginia:
    instances = res['Instances']
    for ins in instances:
        instance_ids_virginia.append(ins['InstanceId'])

response = ec2_resource_virginia.create_tags(
    Resources=instance_ids_virginia,
    Tags=[
        {
            'Key': 'environment',
            'Value': 'prod'
        },
    ]
)

reservations_ohio = ec2_client_ohio.describe_instances()['Reservations']
for res in reservations_ohio:
    instances = res['Instances']
    for ins in instances:
        instance_ids_ohio.append(ins['InstanceId'])

response = ec2_resource_ohio.create_tags(
    Resources=instance_ids_ohio,
    Tags=[
        {
            'Key': 'environment',
            'Value': 'dev'
        },
    ]
)
