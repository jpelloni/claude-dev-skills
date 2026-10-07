resource "aws_security_group" "app" {
  name = "app"
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.app.id
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_db_instance" "app" {
  identifier          = "app"
  engine              = "postgres"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  username            = "app"
  password            = "super-secret-db-password"
  publicly_accessible = true
  skip_final_snapshot = true
  storage_encrypted   = false
}
