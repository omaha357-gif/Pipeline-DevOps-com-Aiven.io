output "pg_service_uri" {
  description = "String de conexão completa do serviço PostgreSQL"
  value       = aiven_pg.dashboard_db.service_uri
  sensitive   = true
}

output "pg_host" {
  value = aiven_pg.dashboard_db.service_host
}

output "pg_port" {
  value = aiven_pg.dashboard_db.service_port
}
