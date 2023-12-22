variable "vpc_cidr_block" {}
variable "subnet_1_cidr_block" {}
variable "avail_zone" {}
variable "env_prefix" {}
variable "instance_type" {}

variable "my_public_ip" {}
variable "subnet_prefix_length" {
  default = "32"
}

variable "image_name" {}

# variable "key_name" {}
# variable "public_key_location" {}