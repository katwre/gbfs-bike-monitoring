output "instance_public_ip" {
  value       = aws_instance.gbfs.public_ip
  description = "Public IP of the GBFS instance"
}

output "kestra_url" {
  value       = "http://${aws_instance.gbfs.public_ip}:8080"
  description = "Kestra UI URL"
}

output "streamlit_url" {
  value       = "http://${aws_instance.gbfs.public_ip}:8501"
  description = "Streamlit dashboard URL"
}

output "minio_console_url" {
  value       = "http://${aws_instance.gbfs.public_ip}:9001"
  description = "MinIO console URL"
}
