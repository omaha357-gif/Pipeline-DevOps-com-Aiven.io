variable "aiven_api_token" {
  description = "Token de API da Aiven (Aiven Console > Profile > Authentication tokens)"
  type        = string
  sensitive   = true
}

variable "aiven_project" {
  description = "Nome do projeto na Aiven"
  type        = string
}

variable "cloud_name" {
  description = "Região/nuvem da Aiven, ex: google-southamerica-east1, aws-sa-east-1"
  type        = string
  default     = "google-southamerica-east1"
}

variable "pg_plan" {
  description = "Plano do serviço PostgreSQL (free tier disponível em algumas contas: 'hobbyist')"
  type        = string
  default     = "hobbyist"
}

variable "service_name" {
  description = "Nome do serviço PostgreSQL"
  type        = string
  default     = "dashboard-pg"
}

variable "database_name" {
  description = "Nome do banco de dados"
  type        = string
  default     = "dashboard"
}

variable "db_username" {
  description = "Usuário de aplicação para o Postgres"
  type        = string
  default     = "dashboard_app"
}

variable "kafka_plan" {
  description = "Plano do serviço Kafka (normalmente pago — verifique disponibilidade na conta)"
  type        = string
  default     = "startup-2"
}

variable "kafka_service_name" {
  description = "Nome do serviço Kafka"
  type        = string
  default     = "bcb-kafka"
}

variable "kafka_topic_name" {
  description = "Nome do tópico usado para os eventos de indicadores do BCB"
  type        = string
  default     = "bcb-indicadores"
}

variable "grafana_plan" {
  description = "Plano do serviço Grafana"
  type        = string
  default     = "startup-1"
}

variable "grafana_service_name" {
  description = "Nome do serviço Grafana"
  type        = string
  default     = "bcb-grafana"
}
