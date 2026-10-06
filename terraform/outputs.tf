output "pg_service_uri" {
  description = "String de conexão completa do serviço PostgreSQL (marcada como sensível)"
  value       = aiven_pg.dashboard_db.service_uri
  sensitive   = true
}

output "pg_host" {
  value = aiven_pg.dashboard_db.service_host
}

output "pg_port" {
  value = aiven_pg.dashboard_db.service_port
}

output "kafka_bootstrap_servers" {
  description = "host:port para KAFKA_BOOTSTRAP_SERVERS"
  value       = "${aiven_kafka.events.service_host}:${aiven_kafka.events.service_port}"
}

output "kafka_username" {
  value     = aiven_kafka.events.service_username
  sensitive = true
}

output "kafka_password" {
  value     = aiven_kafka.events.service_password
  sensitive = true
}

output "kafka_ca_cert" {
  description = "Certificado CA — cole em KAFKA_CA_CERT_PEM no GitHub/Render"
  value       = aiven_kafka.events.ca_cert
  sensitive   = true
}

output "grafana_uri" {
  description = "URL pública do Grafana provisionado"
  value       = aiven_grafana.dashboards.service_uri
  sensitive   = true
}
