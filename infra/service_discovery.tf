resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "${var.project_name}.local"
  description = "Private service discovery namespace for PenFlow."
  vpc         = aws_vpc.main.id
}

resource "aws_service_discovery_service" "backend" {
  name = "penflow-backend"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id


    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }
}