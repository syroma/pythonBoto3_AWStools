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
