terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    http = {
      source  = "hashicorp/http"
      version = "3.4.0"
    }
  }
  backend "s3" {
    bucket = "terraform-sy"
    key    = "tf/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = "us-east-1"
}

provider "http" {
  # Configuration options
}

data "http" "public_ip" {
  url = "http://ifconfig.me/ip"
}

# Comment out only 1 of the "public_ip =" lines below
resource "null_resource" "update_public_ip_with_cidr" {
  triggers = {
    # Auto set using "http://ifconfig.me/ip" (uncomment line below)
    # public_ip = data.http.public_ip.response_body
    ##
    ## *OR*
    ##
    ## Set your own IP address
    public_ip = "148.72.171.15"
  }

  provisioner "local-exec" {
    command = <<EOT
      (Get-Content terraform.tfvars) | ForEach-Object {
        if ($_ -match '^my_public_ip\s*=\s*"(.*)"') {
          $_ -replace ('"{0}"' -f $matches[1]), '"${data.http.public_ip.response_body}/${var.subnet_prefix_length}"'
        } else {
          $_
        }
      } | Set-Content terraform.tfvars
    EOT

    interpreter = ["PowerShell", "-Command"]
  }
}

data "aws_ami" "amazon-linux-image" {
  most_recent = true
  #owners      = ["137112412989"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.2.20231113.0-kernel-6.1-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_vpc" "myapp-vpc" {
  cidr_block = var.vpc_cidr_block
  tags = {
    Name = "${var.env_prefix}-vpc"
  }
}

resource "aws_subnet" "myapp-subnet-1" {
  vpc_id            = aws_vpc.myapp-vpc.id
  cidr_block        = var.subnet_1_cidr_block
  availability_zone = var.avail_zone
  tags = {
    Name = "${var.env_prefix}-subnet-1"
  }
}

resource "aws_security_group" "myapp-sg" {
  name   = "myapp-sg"
  vpc_id = aws_vpc.myapp-vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_public_ip]
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port       = 0
    to_port         = 0
    protocol        = "-1"
    cidr_blocks     = ["0.0.0.0/0"]
    prefix_list_ids = []
  }

  tags = {
    Name = "${var.env_prefix}-security-group"
  }
}

resource "aws_internet_gateway" "myapp-igw" {
  vpc_id = aws_vpc.myapp-vpc.id
  tags = {
    Name = "${var.env_prefix}-igw"
  }
}

resource "aws_route_table" "myapp-route-table" {
  vpc_id = aws_vpc.myapp-vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.myapp-igw.id
  }

  # default route

  tags = {
    Name = "${var.env_prefix}-route-table"
  }
}

# Associate subnet with Route Table
resource "aws_route_table_association" "a-rtb-subnet" {
  subnet_id      = aws_subnet.myapp-subnet-1.id
  route_table_id = aws_route_table.myapp-route-table.id
}

resource "aws_key_pair" "ssh-key" {
  key_name   = "server-key"
  public_key = file("${path.module}/ssh-keygen/id_rsa.pub")
}

resource "aws_instance" "myapp-server-one" {
  ami           = data.aws_ami.amazon-linux-image.id
  instance_type = var.instance_type

  subnet_id              = aws_subnet.myapp-subnet-1.id
  vpc_security_group_ids = [aws_security_group.myapp-sg.id]
  availability_zone      = var.avail_zone

  associate_public_ip_address = true
  key_name                    = aws_key_pair.ssh-key.key_name

  user_data = file("entry-script.sh")

  tags = {
    Name        = "${var.env_prefix}-server-one"
    environment = "production"
  }
}

resource "aws_instance" "myapp-server-two" {
  ami           = data.aws_ami.amazon-linux-image.id
  instance_type = var.instance_type

  subnet_id              = aws_subnet.myapp-subnet-1.id
  vpc_security_group_ids = [aws_security_group.myapp-sg.id]
  availability_zone      = var.avail_zone

  associate_public_ip_address = true
  key_name                    = aws_key_pair.ssh-key.key_name

  user_data = file("entry-script.sh")

  tags = {
    Name        = "${var.env_prefix}-server-two"
    environment = "production"
  }
}

resource "aws_instance" "myapp-server-three" {
  ami           = data.aws_ami.amazon-linux-image.id
  instance_type = var.instance_type

  subnet_id              = aws_subnet.myapp-subnet-1.id
  vpc_security_group_ids = [aws_security_group.myapp-sg.id]
  availability_zone      = var.avail_zone

  associate_public_ip_address = true
  key_name                    = aws_key_pair.ssh-key.key_name

  user_data = file("entry-script.sh")

  tags = {
    Name        = "${var.env_prefix}-server-three",
    environment = "production"
  }
}

