output "ami_id" {
  value = data.aws_ami.amazon-linux-image.id
}

# output "subnet" {
#   value = aws_subnet.myapp-subnet-1
# }

output "ec2_server_one_public_ip" {
  value = aws_instance.myapp-server-one.public_ip
}

output "ec2_server_two_public_ip" {
  value = aws_instance.myapp-server-two.public_ip
}

output "ec2_server_three_public_ip" {
  value = aws_instance.myapp-server-three.public_ip
}

output "nginx_web_address_one" {
  value = "http://${aws_instance.myapp-server-one.public_ip}:8080/"
}

output "nginx_web_address_two" {
  value = "http://${aws_instance.myapp-server-two.public_ip}:8080/"
}

output "nginx_web_address_three" {
  value = "http://${aws_instance.myapp-server-three.public_ip}:8080/"
}

output "current_public_ip" {
  value = data.http.public_ip.response_body
}