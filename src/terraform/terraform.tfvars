vpc_cidr_block       = "10.0.0.0/16"
subnet_1_cidr_block  = "10.0.10.0/24"
avail_zone           = "us-east-1a"
env_prefix           = "prod"
my_public_ip         = "172.96.121.233/32" # this will be automatically changed. You can validate here http://ifconfig.me/ip 
subnet_prefix_length = "32"               # you can check and correct the prefix length by entering the public IP address here https://cidr.xyz/ if you are not a single IP home user
instance_type        = "t2.micro"
image_name           = "ami-095819c19b51bc983"
