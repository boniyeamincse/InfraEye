# InfraEye

InfraEye is a comprehensive monitoring and observability stack designed for deep security insights. It utilizes Prometheus for metrics collection, Grafana for visualization, Alertmanager for alerting, and various exporters for monitoring system metrics, databases, and external services.

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               InfraEye Monitoring Stack                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │   Targets   │    │  Exporters  │    │ Prometheus  │    │ Alertmanager│   │
│  │             │    │             │    │             │    │             │   │
│  │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────┐ │   │
│  │ │  Linux  │◄┼────┼►│Node Exp │◄┼────┼►│ Metrics │◄┼────┼►│  Rules  │◄┼──┐ │
│  │ │ Servers │ │    │ │         │ │    │ │Collection│ │    │ │Evaluation│ │  │ │
│  │ └─────────┘ │    │ └─────────┘ │    │ └─────────┘ │    │ └─────────┘ │  │ │
│  │             │    │             │    │             │    │             │  │ │
│  │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────┐ │  │ │
│  │ │ Windows │◄┼────┼►│Windows  │◄┼────┼►│  Storage │◄┼────┼►│ Alert    │◄┼──┼►│
│  │ │ Servers │ │    │ │Exporter │ │    │ │  (TSDB)  │ │    │ │ Routing  │ │  │ │
│  │ └─────────┘ │    │ └─────────┘ │    │ └─────────┘ │    │ └─────────┘ │  │ │
│  │             │    │             │    │             │    │             │  │ │
│  │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────┐ │    │ ┌─────────┐ │  │ │
│  │ │Database │◄┼────┼►│Postgres │◄┼────┼►│  Query   │◄┼────┼►│Grouping │◄┼──┼►│
│  │ │Servers  │ │    │ │Exporter │ │    │ │  Engine  │ │    │ │& Silence│ │  │ │
│  │ └─────────┘ │    │ └─────────┘ │    │ └─────────┘ │    │ └─────────┘ │  │ │
│  │             │    │             │    │             │    │             │  │ │
│  │ ┌─────────┐ │    │ ┌─────────┐ │    │             │    │             │  │ │
│  │ │Services │◄┼────┼►│Blackbox │ │    │             │    │             │  │ │
│  │ │& APIs   │ │    │ │Exporter │ │    │             │    │             │  │ │
│  │ └─────────┘ │    │ └─────────┘ │    │             │    │             │  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │ │
│                                                                             │ │
└─────────────────────────────────────────────────────────────────────────────┼─┘
                                                                              │
┌─────────────────────────────────────────────────────────────────────────────┼─┐
│                            Notification Channels                            │ │
│                                                                             │ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │ │
│  │    Slack    │  │    Email    │  │  Telegram   │  │ PagerDuty   │        │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │ │
│                                                                             │ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                          │ │
│  │  Webhooks   │  │     SMS     │  │  Microsoft  │                          │ │
│  │             │  │             │  │   Teams     │                          │ │
│  └─────────────┘  └─────────────┘  └─────────────┘                          │ │
└─────────────────────────────────────────────────────────────────────────────┘
                                                                              │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Visualization Layer                            │
│                                                                             │
│                               ┌─────────────┐                               │
│                               │   Grafana   │                               │
│                               │             │                               │
│                               │ ┌─────────┐ │                               │
│                               │ │Dashboards│ │                               │
│                               │ │& Panels  │ │                               │
│                               │ └─────────┘ │                               │
│                               └─────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Metrics Collection**: Exporters collect metrics from various targets
2. **Data Storage**: Prometheus stores time-series data
3. **Alert Evaluation**: Prometheus evaluates alerting rules
4. **Alert Routing**: Alertmanager routes alerts to appropriate channels
5. **Visualization**: Grafana queries Prometheus for dashboard data
6. **Automated Response**: Webhooks trigger remediation scripts

### Components

- **Prometheus**: Time-series database and monitoring system that collects metrics from configured targets.
- **Grafana**: Analytics and monitoring platform for creating dashboards and visualizations.
- **Alertmanager**: Handles alerts from Prometheus and routes them to various notification channels.
- **Node Exporter**: Collects hardware and OS metrics from the host system.
- **Postgres Exporter**: Monitors PostgreSQL database performance and health.
- **Blackbox Exporter**: Probes endpoints over HTTP, HTTPS, DNS, TCP, ICMP, and more.
- **Windows Exporter**: Collects Windows system metrics and WMI data.
- **Security Exporter**: Monitors network security metrics including open ports, failed login attempts, and network connections (lightweight IDS functionality).
- **VictoriaMetrics**: Long-term time-series database for storing metrics for months/years with high performance and efficient storage.
- **Reporting Service**: Automated generation of weekly and monthly reports with trend analysis and anomaly detection.

## Advanced Features

### Long-term Metrics Storage

InfraEye includes VictoriaMetrics for scalable long-term storage of monitoring data. VictoriaMetrics provides:

- **12-month data retention** by default (configurable)
- **High ingestion rates** and query performance
- **Efficient storage compression** reducing disk usage by up to 70%
- **Horizontal scaling** capabilities for large deployments
- **Prometheus-compatible API** for seamless integration

### Automated Reporting

The reporting service generates comprehensive reports automatically:

- **Weekly Reports**: System health summaries, CPU/RAM usage, service uptime, security events
- **Monthly Reports**: Trend analysis, growth forecasts, anomaly detection
- **Email Integration**: Optional email delivery for stakeholders
- **HTML Format**: Professional reports with charts and insights

Configure email reporting with environment variables:
```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
REPORT_RECIPIENTS=admin@company.com,team@company.com
```

### Trend Analysis & Forecasting

Advanced dashboards provide predictive analytics:

- **CPU/Memory Forecasting**: Predict resource usage 24 hours ahead
- **Growth Trend Analysis**: Monitor disk and network usage trends
- **Anomaly Detection**: Automated identification of unusual patterns
- **Capacity Planning**: Forecast future resource requirements

Access the Trend Analysis dashboard in Grafana for comprehensive insights into system behavior and future projections.

## Prerequisites

- Docker and Docker Compose installed on your system
- At least 4GB of available RAM (recommended for basic setup), 8GB+ for long-term storage
- Ports 3000 (Grafana), 9090 (Prometheus), 9093 (Alertmanager), 9100 (Node Exporter), 9187 (Postgres Exporter), 9115 (Blackbox Exporter), 8001 (Security Exporter), and 8428 (VictoriaMetrics) available

## Quick Start

1. Clone or navigate to the project directory.

2. Configure environment variables (optional):
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

3. Ensure all configuration files are in place:
   - `prometheus/prometheus.yml` and `prometheus/rules/`
   - `grafana/grafana.ini`
   - `alertmanager/alertmanager.yml`
   - `blackbox_exporter/blackbox.yml`

4. Start the monitoring stack:
   ```bash
   docker-compose up -d
   ```

5. Access the services:
   - Grafana: http://localhost:3000 (default: admin/admin)
   - Prometheus: http://localhost:9090
   - Alertmanager: http://localhost:9093
   - Node Exporter: http://localhost:9100
   - Blackbox Exporter: http://localhost:9115
   - Postgres Exporter: http://localhost:9187

## Configuration

### Prometheus

The Prometheus configuration (`prometheus/prometheus.yml`) includes scrape jobs for all exporters. Key settings:
- Global scrape interval: 15 seconds
- Jobs configured for Prometheus itself, Node Exporter, Postgres Exporter, and Blackbox Exporter

### Grafana

Grafana configuration (`grafana/grafana.ini`) sets up basic authentication and paths. Default credentials:
- Username: admin
- Password: admin

### Alertmanager

Alertmanager configuration (`alertmanager/alertmanager.yml`) defines routing rules and notification channels. Currently configured with a webhook receiver as an example.

### Blackbox Exporter

Blackbox configuration (`blackbox_exporter/blackbox.yml`) defines various probing modules for different protocols and services.

## Configuration

### Environment Variables

InfraEye uses environment variables for flexible configuration. Copy `.env.example` to `.env` and modify as needed:

```bash
# Grafana settings
GF_SECURITY_ADMIN_PASSWORD=your_secure_password
GF_AUTH_ANONYMOUS_ENABLED=false

# Alertmanager integrations
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
TELEGRAM_BOT_TOKEN=your_bot_token
SMTP_HOST=smtp.gmail.com:587

# Database connections
POSTGRES_DSN=postgresql://user:pass@host:5432/db
```

### Alerting Rules

Pre-configured alerting rules are available in `prometheus/rules/alert_rules.yml`, including:
- System health monitoring (CPU, memory, disk)
- Service availability checks
- Database monitoring
- Blackbox probe monitoring
- Security monitoring (unauthorized port changes, failed login attempts, unusual network traffic)

### Security Features

- Configurable authentication
- Environment-based secrets
- Network isolation
- Health checks for all services
- Automatic service restart policies

## Usage

### Adding Dashboards

1. Access Grafana at http://localhost:3000
2. Log in with admin/admin
3. Add Prometheus as a data source (URL: http://prometheus:9090)
4. Import or create dashboards to visualize metrics from exporters

### Monitoring Postgres Database

The Postgres Exporter requires database connection details. Update the `DATA_SOURCE_NAME` environment variable in `docker-compose.yml` with your actual database credentials:

```yaml
environment:
  - DATA_SOURCE_NAME=postgresql://username:password@host:port/database?sslmode=disable
```

### Scaling Node Exporters

For monitoring multiple servers, you can scale the node-exporter service or define separate services in docker-compose.yml for each target server.

### Automated Alerting & Remediation

InfraEye includes advanced alerting capabilities:

#### Alert Types
- **Threshold-based**: CPU > 80%, Memory > 80%, Disk < 10%
- **Anomaly detection**: Unusual traffic patterns
- **Multi-condition**: Combined metrics evaluation

#### Notification Channels
- Slack (critical, warning, info channels)
- Email
- Telegram
- PagerDuty
- Webhooks for automated remediation

#### Automated Remediation
Configure webhooks to trigger scripts for:
- Service restarts
- Disk cleanup
- Container scaling
- Custom remediation actions

See [ADMINISTRATION_GUIDE.md](ADMINISTRATION_GUIDE.md#automated-alerting--remediation) for detailed configuration.

## Maintenance

### Updating Configurations

After modifying configuration files, restart the affected services:

```bash
docker-compose restart <service_name>
```

### Viewing Logs

Check logs for troubleshooting:

```bash
docker-compose logs <service_name>
```

### Data Persistence

Persistent data is stored in Docker volumes:
- `prometheus_data`: Prometheus metrics data
- `grafana_data`: Grafana dashboards and configurations

## Security Considerations

- Change default Grafana credentials in production
- Configure proper authentication and authorization
- Use HTTPS in production environments
- Regularly update Docker images for security patches
- Configure network isolation as needed

## Troubleshooting

- Ensure all required ports are available
- Check Docker logs if services fail to start
- Verify configuration file syntax (YAML/INI)
- Confirm database connectivity for Postgres Exporter

## Administration

For detailed administration procedures including user management, configuration updates, security hardening, and troubleshooting, see [ADMINISTRATION_GUIDE.md](ADMINISTRATION_GUIDE.md).

## Contributing

To contribute to InfraEye:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Author

**Boni Yeamin**
Cybersecurity Engineer
Akij Group
Email: boni@akijgroup.co

## License

This project is licensed under the MIT License - see the LICENSE file for details.