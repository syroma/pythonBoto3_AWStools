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
# ssh_key_file = 'C:/Users/Zool/PycharmProjects/pythonBoto3_AWStools/src/terraform/ssh-keygen/id_rsa'
ssh_key_file = '../terraform/ssh-keygen/id_rsa'

# Define aws dictionary list

ec2_client = boto3.client('ec2', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name="us-east-1")

# Pull the instance info from AWS
def production_instances():
    try:
        # Describe instances with specific filters
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


def establish_ssh_connection(public_ip, username, key_filename, retry_attempts=5, retry_interval=20):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for attempt in range(1, retry_attempts + 1):
        try:
            print(f"Attempting SSH connection (Attempt {attempt})")
            ssh.connect(public_ip, username=username, key_filename=key_filename)
            print("SSH connection established successfully")
            return ssh

        except paramiko.AuthenticationException:
            print("Authentication failed. Please check your credentials.")
            return None

        except Exception as e:
            print(f"Failed to connect: {e}")
            time.sleep(retry_interval)

    print("Exceeded maximum retry attempts. Unable to establish SSH connection.")
    return None


# def restart_container(ssh):
#     print('Restarting the application')
#     command_one = 'sudo chown -R ec2-user:docker /var/run/docker.sock'
#     command_two = 'sudo chmod 660 /var/run/docker.sock'
#     command_three = f'sudo docker run -d -p 8080:80 nginx'
#     stdin, stdout, stderr = ssh.exec_command(command)
#
#     # Check if stdout has data and print it
#     stdout_data = stdout.read().decode().strip()
#     if stdout_data:
#         print("Command output:")
#         print(stdout_data)
#
#     # Check if stderr has data and print it
#     stderr_data = stderr.read().decode().strip()
#     if stderr_data:
#         print("Command error:")
#         print(stderr_data)


def execute_ssh_commands(ssh, commands):
    # Establish an SSH connection
    ssh.connect('hostname', username='username', password='password')

    for command in commands:
        # Execute the command on the remote server
        stdin, stdout, stderr = ssh.exec_command(command)

        # Check if stdout has data and print it
        stdout_data = stdout.read().decode().strip()
        if stdout_data:
            print(f"Command output for '{command}':")
            print(stdout_data)

        # Check if stderr has data and print it
        stderr_data = stderr.read().decode().strip()
        if stderr_data:
            print(f"Command error for '{command}':")
            print(stderr_data)

    # Close the SSH connection
    ssh.close()


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


def restart_instance(instance_id):
    # Start the instance
    ec2_client.start_instances(InstanceIds=[instance_id])

    # Wait until the instance is running
    waiter = ec2_client.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])

    # Continue with your logic after the instance is running
    print(f"Instance {instance_id} has started successfully.")


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
    # Retrieve InstanceId, and PublicIpAddress
    global aws_info
    aws_info = production_instances()

    for aws_instance in aws_info:
        instance_id = aws_instance.get('instance_id')
        instance_state = aws_instance.get('instance_state')
        public_ip = aws_instance.get('public_ip')

        try:
            # If the AWS instance is stopped restart it
            if instance_state == 'stopped':
                print(f'Instance {instance_id} is currently {instance_state} and has an ip address of {public_ip}')
                restart_instance(instance_id)
                public_ip = retrieve_public_ip_after_restart(instance_id)
                if public_ip is not None:
                    instance_state = 'running'

                print(f'Instance {instance_id} is currently {instance_state} and has an ip address of {public_ip}')

            # wait until AWS status is passed
            check_instance_status(instance_id)

            # Next connect to it over SSH
            ssh = establish_ssh_connection(public_ip, 'ec2-user', ssh_key_file)

            # If the AWS instance is up but the website is unavailable restart docker instance
            if ssh is not None and instance_state == 'running':
                # Restart the Docker container
                restart_container(ssh, commands)

                # Wait for the website to be accessible
                website_url = f"http://{public_ip}:8080"
                if is_website_accessible(website_url):
                    print('Operation completed')
            ssh.close()

        except Exception as ex:
            print(f'Connection error happened: {ex}')
            msg = 'Application not accessible at all.'
            send_notification(msg)

            # Restart AWS server
            print('Restarting the server...')
            response = ec2_client.reboot_instances(InstanceIds=[instance_id])

            # Wait for the server to be running again
            while True:

                if instance_state == 'stopped':
                    restart_instance(instance_id)

                print(instance_state)
                if instance_state == 'running':
                    # Establish SSH connection again
                    ssh = establish_ssh_connection(public_ip, 'ec2-user', ssh_key_file)
                    print(public_ip)

                    if ssh is not None:
                        # Restart the Docker container
                        restart_container(ssh)

                        # Close the SSH connection
                        ssh.close()

                        break  # Exit the loop once the container is restarted

                time.sleep(60)  # Adjust the sleep duration based on your specific case


aws_info = production_instances()
schedule.every(10).seconds.do(monitor_web_application())

while True:
    schedule.run_pending()
