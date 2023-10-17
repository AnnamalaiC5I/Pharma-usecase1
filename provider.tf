terraform {
  required_providers {
    databricks = {
      source = "databricks/databricks"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.15.0"
    }
    github = {
      source  = "integrations/github"
      version = "~> 5.0"
    }
  }
}

variable "db_host" {
}

variable "db_token" {
}

variable "git_token"{
}

variable "aws_access_key"{
}


variable "aws_secret_key"{
}


provider "databricks" {
  host  = "${var.db_host}"
  token = "${var.db_token}"
}

provider "github" {
    token = "${var.git_token}"
}

provider "aws" {
    access_key = "${var.aws_access_key}"
    secret_key = "${var.aws_secret_key}"
    region = "us-west-2"
}