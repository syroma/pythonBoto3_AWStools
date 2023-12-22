import boto3
import os
import paramiko
import requests
import smtplib
import time
import schedule

EMAIL_FROM_ADDR = os.environ.get('EMAIL_FROM_ADDR')
EMAIL_FROM_PWD = os.environ.get('EMAIL_FROM_PWD')
EMAIL_TO_ADDR = os.environ.get('EMAIL_TO_ADDR')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
ssh_key_file = 'C:/Users/Zool/PycharmProjects/pythonBoto3_AWStools/src/terraform/ssh-keygen/id_rsa'
# ssh_key_file = '../terraform/ssh-keygen/id_rsa'

ec2_client = boto3.client('ec2', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name="us-east-1")

# List of commands to execute
commands_to_run = [
    'sudo chown -R ec2-user:docker /var/run/docker.sock',
    'sudo chmod 660 /var/run/docker.sock',
    'sudo docker run -d -p 8080:80 nginx'
]


def production_instances():
    try:
        # Pull the instance info from AWS
        response = ec2_client.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']},
                {'Name': 'tag:environment', 'Values': ['production']}
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


def send_notification(email_msg):
    print('Sending an email...')
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.ehlo()
        smtp.login(EMAIL_FROM_ADDR, EMAIL_FROM_PWD)
        message = f"Subject: SITE DOWN\n{email_msg}"
        # smtp.sendmail(EMAIL_FROM_ADDR, EMAIL_TO_ADDR, message)
        smtp.sendmail(EMAIL_FROM_ADDR, EMAIL_FROM_ADDR, message)


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


def check_instance_status(instance_id, max_attempts=60, sleep_interval=10):
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


def restart_container(public_ip, username='ec2-user', key_filename=ssh_key_file, commands=commands_to_run):
    # Establish an SSH connection
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(public_ip, username=username, key_filename=key_filename)

    # # If the AWS instance is up but the website is unavailable restart docker instance
    for command in commands:
        # Execute the command on the remote server
        stdin, stdout, stderr = ssh.exec_command(command)

        # Check if stdout has data and print it
        stdout_data = stdout.read().decode().strip()
        if stdout_data:
            print(f"Command output for '{command}': ")
            print(stdout_data)

        # Check if stderr has data and print it
        stderr_data = stderr.read().decode().strip()
        if stderr_data:
            print(f"Command error for '{command}': ")
            print(stderr_data)

    # Close the SSH connection
    ssh.close()


def restart_instance_and_container(instance_id, instance_state):
    # print(f'Instance {instance_id} is currently {instance_state} and has an ip address of {public_ip}')

    # Start the AWS instance
    ec2_client.start_instances(InstanceIds=[instance_id])

    # Wait until the AWS instance is running
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print(f"Instance {instance_id} has started successfully.")

    # check if instance has an IP address and if so change to running
    public_ip = retrieve_public_ip_after_restart(instance_id)
    if public_ip is not None:
        instance_state = 'running'

    print(f'Instance {instance_id} is currently {instance_state} and has an ip address of {public_ip}')

    # wait until AWS status is passed
    instance_is_up = check_instance_status(instance_id)

    # If the AWS instance is up but the website is unavailable restart docker instance
    if instance_is_up:
        # Restart the Docker container
        restart_container(public_ip)

    return instance_id, instance_state, public_ip


def is_website_accessible(url, retry_attempts=5, retry_interval=20):
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
    # Retrieve Instances information and isee if anything is wrong
    global aws_info
    aws_info = production_instances()

    # iterate through each instance
    for aws_instance in aws_info:
        instance_id = aws_instance.get('instance_id')
        instance_state = aws_instance.get('instance_state')
        public_ip = aws_instance.get('public_ip')

        try:
            # If we cannot access the website restart the container
            response = requests.get(f"http://{public_ip}:8080")
            if response.status_code == 200:
                print("Application is running successfully!")
            else:
                restart_container(public_ip)
                message = f'Application response {response.status_code}'
                send_notification(message)
        except Exception as ex:
            print(f'Connection error happened: {ex}')
            message = 'Application not accessible at all.'
            send_notification(message)

            # Restart AWS server
            print('Restarting the server...')
            instance_id, instance_state, public_ip= restart_instance_and_container(instance_id, instance_state)
            if instance_state == 'running' and public_ip is not None:
                print(f'Instance {instance_id} is currently {instance_state} and has an ip address of {public_ip}')


aws_info = production_instances()
schedule.every(10).seconds.do(monitor_web_application)

while True:
    schedule.run_pending()
    time.sleep(1)
