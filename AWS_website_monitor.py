import boto3
import os
import paramiko
import requests
import smtplib
import time
import schedule

EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
ssh_key_file = 'C:/Users/Zool/boogpk.pem'
aws_info = []

ec2_client = boto3.client('ec2', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY, region_name="us-east-1")


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
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        message = f"Subject: SITE DOWN\n{email_msg}"
        smtp.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, message)


def establish_ssh_connection(public_ip, username, key_filename, retry_attempts=5, retry_interval=20):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for attempt in range(1, retry_attempts + 1):
        try:
            print(f"Attempting SSH connection (Attempt {attempt})")
            ssh.connect(aws_info['public_ip'], username=username, key_filename=key_filename)
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


def restart_container(ssh):
    print('Restarting the application')
    command = f'docker run -d -p 8080:80 nginx'
    stdin, stdout, stderr = ssh.exec_command(command)
    # print("Command output:")
    # print(stdout.read().decode())
    # print("Command error:")
    # print(stderr.read().decode())


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
        try:
            response = requests.get(url)
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


def monitor_web_application():
    try:
        # Retrieve InstanceId, and PublicIpAddress
        aws_info = production_instances()[0]
        print(aws_info)

        # If instance is stopped restart it
        if aws_info['instance_state'] == 'stopped':
            restart_instance(aws_info['instance_id'])

        # Establish SSH connection
        ssh = establish_ssh_connection(aws_info['public_ip'], 'ec2-user', ssh_key_file)

        # If server instance is up but website is unavailable restart docker instance
        if ssh is not None and aws_info['instance_state'] == 'running':
            # Restart the Docker container
            restart_container(ssh)

            # Wait for the website to be accessible
            website_url = f"http://{aws_info['public_ip']}:8080"
            if is_website_accessible(website_url):
                print('Operation completed')
        ssh.close()


    except Exception as ex:
        print(f'Connection error happened: {ex}')
        msg = 'Application not accessible at all.'
        send_notification(msg)

        # Restart AWS server
        print('Restarting the server...')
        response = ec2_client.reboot_instances(InstanceIds=[aws_info['instance_id']])

        # Wait for the server to be running again
        while True:
            # state_response = ec2_client.describe_instances(InstanceIds=[aws_info['instance_id']])
            # inst_state = state_response['Reservations'][0]['Instances'][0]['State']['Name']
            aws_info = production_instances()[0]

            if aws_info['instance_state'] == 'stopped':
                restart_instance(aws_info['instance_id'])

            print(aws_info['instance_state'])
            if aws_info['instance_state'] == 'running':
                # Establish SSH connection again
                ssh = establish_ssh_connection(aws_info['public_ip'], 'ec2-user', ssh_key_file)
                print(aws_info['public_ip'])

                if ssh is not None:
                    # Restart the Docker container
                    restart_container(ssh)

                    # Close the SSH connection
                    ssh.close()

                    break  # Exit the loop once the container is restarted

            time.sleep(60)  # Adjust the sleep duration based on your specific case

aws_info = production_instances()[0]
schedule.every(5).seconds.do(monitor_web_application)

while True:
    schedule.run_pending()