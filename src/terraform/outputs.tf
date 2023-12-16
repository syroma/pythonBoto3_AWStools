output "ami_id" {
  value = data.aws_ami.amazon-linux-image.id
}

output "subnet" {
  value = aws_subnet.myapp-subnet-1
}

output "ec2_public_ip" {
  value = aws_instance.myapp-server-one.public_ip
}