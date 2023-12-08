# AWS Docker Website Monitor

## Description

This is a compact demo script designed to monitor a Dockerized AWS website, automatically restarting the container or AWS instance, and sending email notifications in the event of site unavailability.

## Table of Contents

1. [Usage](#usage)
2. [Email Notification](#email-notification)
3. [Schedule](#schedule)

## Usage

This script is run from PyCharm and relies on four user environment variables for connecting to AWS and sending email notifications:

1. `AWS_ACCESS_KEY`
2. `AWS_SECRET_KEY`
3. `EMAIL_ADDRESS`
4. `EMAIL_PASSWORD`

## Email Notification

By default, the script sends notifications to the same email address listed as the sender. You can customize this behavior on [line 59](#) by changing the second parameter in the `smtp.sendmail(<emailtoSendFrom>, <emailToSendTo>, message)`.

## Schedule

By default, the script checks the website's availability every 5 minutes. You can modify this interval on [line 185](#).
