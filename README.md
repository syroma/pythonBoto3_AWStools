# AWS Docker Website Monitor

## Description

This is a compact demo script designed to monitor a Dockerized AWS website and automatically restarting the container or AWS instance, and send email notifications in the event of site unavailability.

## Table of Contents

1. [Required Environment Variables](#required-environment-variable)
2. [Terraform](#terraform)
3. [Python](#python)
4. [Schedule](#schedule)
5. [Required Tags](#required-tags)

## Required Environment Variables

The AWS connection and email messenging depends on five environment variables:

1. For the first you need to create an AWS IAM. In the AWS Management Console, create an IAM user specifically for Terraform. Once the IAM user is created, generate Access Keys for that user under the user's Security Credentials tab
   - AWS_ACCESS_KEY
   - AWS_SECRET_KEY
2. For the last 3 environment variable you need to use a google email address for the EMAIL_FROM_ADDR and your password for the EMAIL_FROM_PWD. If you use 2-factor authentication you will need to login to https://myaccount.google.com/apppasswords (Opens in new window or tab) to generate a useable password for the environment variable. The EMAIL_TO_ADDR is the address or alias you want to message.
   - EMAIL_FROM_ADDR
   - EMAIL_FROM_PWD
   - EMAIL_TO_ADDR

You can add environmental variables for this part in windows command shell using the below method (replacing the values):

```
setx AWS_ACCESS_KEY "AKIGHRJ7TLPFW5ICORWU"
setx AWS_SECRET_KEY "EA9IDXD+IFlX0byiwCbHp24KftvVy2edUYKsrImH"
setx EMAIL_FROM_ADDR "someone@gmail.com"
setx EMAIL_FROM_PWD "YourPassWord"
setx EMAIL_TO_ADDR "someone@gmail.com"
```

## Terraform

To setup AWS instances using the included Terraform project, you need to:

1. install the binary from Terraform's website (Opens in new window or tab)
2. Open up command line (or powershell) and navigate to `/src/terraform` in the project folder
3. Enter the commands below in order:
   - terraform init
   - terraform plan
   - terraform apply -auto-approve

## S3 Backend provider

If you want to use the S3 backend provider you can modify line 13 in `/src/terraform/main.tf' to indicate your bucket name, else comment out lines 12-16 (the lines shown below):

```
  backend "s3" {
    bucket = "terraform-sy"
    key    = "tf/terraform.tfstate"
    region = "us-east-1"
  }
```

## Python

The python monitor script can be run from `/src/python/AWS_website_monitor.py`

## Schedule

By default, the script checks the website's availability every 5 minutes. You can modify this interval in `/src/python/AWS_website_monitor.py` on line 295 :\

```
schedule.every(5).minutes.do(monitor_web_application)
```

## Required Tags

By default this python script monitors AWS instance websites with the tag "environment::produiction". To change these modify the variables on lines 17-18 in `/src/python/AWS_website_monitor.py`:

```
tag_name = 'environment'
tag_to_filter_on = 'production'
```

## Demo Website access

to access the default NGINX website created in the terraform package, use the public address and port 8080 like: http://54.163.21.67:8080/
