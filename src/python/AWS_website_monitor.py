import boto3
import os
import paramiko
import requests
import smtplib
import time
import schedule
import base64

EMAIL_FROM_ADDR = os.environ.get('EMAIL_FROM_ADDR')
EMAIL_FROM_PWD = os.environ.get('EMAIL_FROM_PWD')
EMAIL_TO_ADDR = os.environ.get('EMAIL_TO_ADDR')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
base_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ssh_key_file = os.path.join(base_directory, 'terraform', 'ssh-keygen', 'id_rsa')
tag_name = 'environment'
tag_to_filter_on = 'production'


ec2_client = boto3.client('ec2', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name="us-east-1")

expected_user_data = """#!/bin/bash
sudo yum update -y
sudo yum install docker -y
sudo usermod -aG docker ec2-user
sudo chown -R ec2-user:docker /var/run/docker.sock
sudo chmod 660 /var/run/docker.sock
sudo systemctl start docker
docker run -d -p 8080:80 nginx
"""


def production_instances():
    try:
        # Pull the instance info from AWS
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']},
                {'Name': f'tag:{tag_name}', 'Values': [tag_to_filter_on]}
            ]
        )

        # Extract information from the response
        instances_list = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_info = {
                    'instance_id': instance['InstanceId'],
                    'instance_state': instance['State']['Name']
                }

                # Add public_ip only if the instance is running
                if instance_info['instance_state'] == 'running':
                    instance_info['public_ip'] = instance['PublicIpAddress']

                instances_list.append(instance_info)

        return instances_list if instances_list else None

    except Exception as e:
        # Handle exceptions (print or log the error, or take appropriate action)
        print(f"An error occurred: {e}")
        return None


def validate_or_restore_expected_userdata(expected_userdata, current_user_data, instance_id):
    # if expected_userdata != current_user_data:
    if are_scripts_unequal(expected_userdata, current_user_data):
        # Modify the user data
        new_base64_user_data = base64.b64encode(expected_userdata.encode('utf-8')).decode('utf-8')
        response_modify  = ec2_client.modify_instance_attribute(
            InstanceId=instance_id,
            UserData={'Value': new_base64_user_data}
        )
    else:
        pass


def check_user_data(instance_id):
    data = ec2_client.describe_instance_attribute(
        InstanceId=instance_id,
        Attribute='userData'
    )
    base64_encoded_user_data = data['UserData']['Value']
    decoded = base64.b64decode(base64_encoded_user_data).decode('utf-8')
    return decoded


def normalize_script(script_content):
    # Remove trailing whitespaces and normalize line endings
    lines = [line.rstrip() for line in script_content.splitlines()]
    return '\n'.join(lines)


def are_scripts_unequal(script1, script2):
    # Normalize both scripts
    normalized_script1 = normalize_script(script1)
    normalized_script2 = normalize_script(script2)
    # Compare normalized scripts
    return normalized_script1 != normalized_script2


def send_notification(email_msg):
    print('Sending an email...')
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.ehlo()
        smtp.login(EMAIL_FROM_ADDR, EMAIL_FROM_PWD)
        message = f"Subject: SITE DOWN\n{email_msg}"
        smtp.sendmail(EMAIL_FROM_ADDR, EMAIL_TO_ADDR, message)


def retrieve_public_ip_after_restart(instance_id):
    try:
        # Describe instances with specific filters
        response = ec2_client.describe_instances(
            InstanceIds=[instance_id]
        )

        # Extract information from the response
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                public_ip_address = instance['PublicIpAddress']

                return public_ip_address if public_ip_address else None

    except Exception as e:
        # Handle exceptions (print or log the error, or take appropriate action)
        print(f"An error occurred: {e}")
        return None


def wait_until_status_and_instance_up(instance_id, max_attempts=60, sleep_interval=10):
    # Wait until instance state and instance status are ok and available to SSH into
    try:
        for _ in range(max_attempts):
            response = ec2_client.describe_instance_status(InstanceIds=[instance_id])

            if 'InstanceStatuses' in response and response['InstanceStatuses']:
                instance_status = response['InstanceStatuses'][0]

                if 'SystemStatus' in instance_status and 'InstanceStatus' in instance_status:
                    system_status = instance_status['SystemStatus']['Status']
                    instance_status = instance_status['InstanceStatus']['Status']

                    if system_status == 'ok' and instance_status == 'ok':
                        print(f"Instance {instance_id} has 'ok' status.")
                        return True

            print(f"Instance {instance_id} does not have 'ok' status. Waiting...")
            time.sleep(sleep_interval)

        print(f"Instance {instance_id} did not have 'ok' status within the specified time.")
        return False

    except Exception as e:
        # Handle exceptions (print or log the error, or take appropriate action)
        print(f"An error occurred: {e}")
        return None


def ssh_and_restart_container(public_ip, username='ec2-user', key_filename=ssh_key_file):
    # Establish an SSH connection
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(public_ip, 22, username=username, key_filename=key_filename)

        # # If the AWS instance is up but the website is unavailable restart docker instance
        stdin, stdout, stderr = ssh.exec_command('docker ps --latest --format "{{.ID}}"')
        container_id = stdout.read().decode().strip()

        if container_id:
            ssh.exec_command(f'docker restart {container_id}')
            print(f'NGINX container restarted: {container_id}')
            ssh.close()
            return True
        else:
            print('No docker container found')
            ssh.close()
            return False
    except Exception as e:
        print(f"An error occurred while connecting via SSH: {e}")
        raise


def restart_instances(instance_ids):
    for instance_id in instance_ids:
        # grab userdata from existing AWS instance to compare
        current_user_data = check_user_data(instance_id)
        # Check if userdata is different and if it is not then replace userdata on the instance being restarted
        validate_or_restore_expected_userdata(expected_user_data, current_user_data, instance_id)

        # Start the AWS instance
        ec2_client.start_instances(InstanceIds=[instance_id])


def is_website_accessible(public_ip, retry_attempts=5, retry_interval=20):
    url = f"http://{public_ip}:8080"
    for attempt in range(1, retry_attempts + 1):
        response = requests.get(url)
        try:
            if response.status_code == 200:
                print("Application is running successfully!")
                return True
            else:
                print(f"Failed to access the website. Retrying... (Attempt {attempt})")
        except Exception as e:
            print(f"Application returned {response.status_code}. Error while accessing the website: {e}")
        time.sleep(retry_interval)

    print("Exceeded maximum retry attempts. Website is not accessible.")
    return False


# ------- *MAIN* ---------#########################################
def monitor_web_application():
    stopped_list = []
    ok_list = []

    # Retrieve AWS instance information for all EC2 instances
    global aws_info
    aws_info = production_instances()

    if aws_info is not None:

        # Make a list of stopped AWS instances and then restart them
        for stopped_instance in aws_info:
            instance_state = stopped_instance.get('instance_state')
            if instance_state == 'stopped':
                instance_id = stopped_instance.get('instance_id')
                stopped_list.append(instance_id)
                # Restart stopped AWS instances
                if len(stopped_list) > 0:
                    restart_instances(stopped_list)

        # Iterate through all AWS instances
        for aws_instance in aws_info:
            instance_id = aws_instance.get('instance_id')
            instance_state = aws_instance.get('instance_state')
            public_ip = aws_instance.get('public_ip')

            try:
                # Check if started instance websites are accessible and if not accessible restart docker container
                if instance_state == 'running' and public_ip is not None and instance_id not in stopped_list:
                    if is_website_accessible(public_ip):
                        print(f"InstanceID {instance_id} is up and running normally")
                        ok_list.append(instance_id)
                    else:
                        # if website not accessible, restart the container and test it
                        fixed = ssh_and_restart_container(public_ip)
                        if fixed and is_website_accessible(public_ip):
                            print(f"Container on instance {instance_id} has been restarted successfully")
                            ok_list.append(instance_id)
                        else:
                            msg = f"unable to restart instance: {instance_id}"
                            send_notification(msg)

                else:
                    #  If website not accessible and instance was restarted at the start of this function
                    if instance_id in stopped_list:
                        # restart container
                        # # Wait until the AWS instance is running
                        # waiter = ec2_client.get_waiter('instance_running')
                        # waiter.wait(InstanceIds=[instance_id])
                        print(f"Instance {instance_id} has started successfully.")
                        public_ip = retrieve_public_ip_after_restart(instance_id)
                        if public_ip:
                            aws_instance['instance_state'] = 'running'
                            # pause until instance status/state / ready to ssh
                            instance_restart_success = wait_until_status_and_instance_up(instance_id)
                            if instance_restart_success:
                                # Restart the Docker container
                                fixed = ssh_and_restart_container(public_ip)
                                if fixed and is_website_accessible(public_ip):
                                    print(f"Container on instance {instance_id} has been restarted")
                                    ok_list.append (instance_id)
                                else:
                                    print(f"Was unable to ssh into {public_ip}")
                            pass
                        else:
                            msg = f"Unable to retrieve IP address from instance {instance_id}. Please investigate"
                            # send_notification(msg)
                    print(f"Nothing else to do... sleeping until next monitoring cycle")
            except Exception as ex:
                print(f'Connection error happened: {ex}')
                msg = 'Application not accessible at all.'
                # send_notification(msg)
    else:
        print(f"No instances with the environment tag '{tag_to_filter_on}' available")


aws_info = production_instances()
schedule.every(5).minutes.do(monitor_web_application)

while True:
    schedule.run_pending()
    time.sleep(1)
