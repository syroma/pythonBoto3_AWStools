#!/bin/bash
sudo yum update -y
sudo yum install docker -y
sudo usermod -aG docker ec2-user
sudo chown -R ec2-user:docker /var/run/docker.sock
sudo chmod 660 /var/run/docker.sock
sudo systemctl start docker
docker run -d -p 8080:80 nginx