variable "branch_name"{
}

resource "databricks_job" "this" {
  name = "Stag_terraform_job"

#   job_cluster {
#     job_cluster_key = "job_cluster_terra"
#     new_cluster {
#       num_workers   = 2
#       spark_version = "11.3.x-cpu-ml-scala2.12"
#       node_type_id  = "m5d.large"
#     }
#   }

    task {
        task_key = "first_task"

        new_cluster {
        num_workers   = 1
        spark_version = "11.3.x-cpu-ml-scala2.12"
        node_type_id  = "m5d.large"
        }

        spark_python_task {
            python_file = "demo_project/tasks/deploy.py"
            source = "GIT"
        }

        library {
                pypi {
                    package = ["mlflow","databricks","databricks-sdk"]
                    // repo can also be specified here
                }
        }
    }

    git_source {
            url = "https://github.com/AnnamalaiC5I/Pharma-usecase1.git"
            provider = "gitHub"
            branch="${var.branch_name}"
        }


}


output "job_id" {
  value = databricks_job.this.id
}



resource "aws_s3_object" "object" {
  bucket  = "pharma-usecase1"
  key     = "terraform.json"
  content = jsonencode({"id":databricks_job.this.id})

  depends_on = [databricks_job.this]
}