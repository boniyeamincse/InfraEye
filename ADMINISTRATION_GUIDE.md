# InfraEye Administration Guide

This guide provides detailed procedures for administering the InfraEye monitoring stack, including user management, configuration updates, maintenance tasks, and troubleshooting.

## Table of Contents

1. [Grafana Administration](#grafana-administration)
2. [Prometheus Administration](#prometheus-administration)
3. [Alertmanager Administration](#alertmanager-administration)
4. [Automated Alerting & Remediation](#automated-alerting--remediation)
5. [System Maintenance](#system-maintenance)
6. [Agent Deployment](#agent-deployment)
7. [Security](#security)
8. [Troubleshooting](#troubleshooting)
9. [Backup and Recovery](#backup-and-recovery)

## Grafana Administration

### User Management

#### Adding Users

1. Access Grafana at http://localhost:3000
2. Navigate to Configuration → Users
3. Click "Invite" or "New user"
4. Fill in user details and assign appropriate roles
5. Send invitation or set temporary password

#### Roles and Permissions

- **Viewer**: Can view dashboards and panels
- **Editor**: Can view, edit, and create dashboards
- **Admin**: Full access including user management and server settings

#### Organizations

Create separate organizations for multi-tenant setups:

1. Go to Configuration → Organizations
2. Click "New organization"
3. Configure organization settings and assign users

### Dashboard Management

#### Creating Dashboards

1. Click the "+" icon in the sidebar
2. Select "Dashboard"
3. Add panels and configure data sources
4. Set permissions and sharing options

#### Importing Dashboards

1. Go to the dashboard list
2. Click "Import"
3. Upload JSON file or enter Grafana.com dashboard ID
4. Configure data source mappings

### Data Source Configuration

#### Adding Prometheus as Data Source

1. Configuration → Data Sources → Add data source
2. Select "Prometheus"
3. Set URL to `http://prometheus:9090`
4. Configure authentication if needed
5. Test connection and save

## Prometheus Administration

### Configuration Management

#### Updating Scrape Targets

Edit `prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'new-target'
    static_configs:
      - targets: ['new-target:9090']
```

Restart Prometheus:

```bash
docker-compose restart prometheus
```

#### Adding Alert Rules

Create rule files in `prometheus/rules/`:

```yaml
groups:
  - name: example
    rules:
      - alert: HighRequestLatency
        expr: http_request_duration_seconds{quantile="0.5"} > 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High request latency"
```

Update `prometheus.yml` to include rule files.

### Querying and Debugging

#### PromQL Queries

Use the Prometheus web interface at http://localhost:9090 to test queries:

- `up`: Check if targets are up
- `rate(http_requests_total[5m])`: Request rate over 5 minutes
- `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[10m]))`: 95th percentile latency

#### Target Health

Check target status in Status → Targets page.

## Alertmanager Administration

### Alert Routing

#### Configuring Routes

Edit `alertmanager/alertmanager.yml`:

```yaml
route:
  group_by: ['alertname', 'cluster']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 3h
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
    - match:
        team: devops
      receiver: 'devops-pager'
```

#### Notification Channels

Supported receivers:
- Email
- Slack
- PagerDuty
- Webhook
- VictorOps

Example Slack configuration:

```yaml
receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
        send_resolved: true
```

### Silencing Alerts

1. Access Alertmanager UI at http://localhost:9093
2. Go to Silences
3. Create new silence with matchers
4. Set duration and reason

## Automated Alerting & Remediation

### Advanced Alerting

#### Threshold-Based Alerts

Create alerts based on metric thresholds:

```yaml
groups:
  - name: 'system-alerts'
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value }}%"

      - alert: LowDiskSpace
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Low disk space on {{ $labels.instance }}"
          description: "Disk space available: {{ $value }}%"
```

#### Anomaly Detection Alerts

Use statistical functions for anomaly detection:

```yaml
      - alert: UnusualTraffic
        expr: rate(http_requests_total[5m]) > 3 * avg_over_time(rate(http_requests_total[1h])[7d:1h])
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Unusual traffic detected"
          description: "Traffic rate is {{ $value }} req/s, 3x higher than 7-day average"
```

#### Multi-Condition Alerts

Combine multiple conditions:

```yaml
      - alert: ServiceDegradation
        expr: up == 0 AND (rate(http_requests_total[5m]) < 0.1 OR histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5)
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Service degradation detected"
          description: "Service is down or experiencing high latency and low traffic"
```

### Automated Remediation Scripts

#### Setting Up Webhook Receiver

Configure Alertmanager to trigger webhooks:

```yaml
receivers:
  - name: 'webhook'
    webhook_configs:
      - url: 'http://remediation-server:8080/webhook'
        send_resolved: true
```

#### Creating Remediation Scripts

Example remediation server using Python Flask:

```python
from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_alert():
    alert = request.json

    for alert_item in alert.get('alerts', []):
        labels = alert_item.get('labels', {})
        alert_name = labels.get('alertname')

        if alert_name == 'HighCPUUsage':
            # Restart problematic service
            subprocess.run(['docker-compose', 'restart', 'high-cpu-service'])
            log_remediation("Restarted high CPU service")

        elif alert_name == 'LowDiskSpace':
            # Clean up disk space
            subprocess.run(['docker', 'system', 'prune', '-f'])
            subprocess.run(['rm', '-rf', '/tmp/*'])
            log_remediation("Cleaned up disk space")

        elif alert_name == 'ContainerDown':
            # Scale up containers
            subprocess.run(['docker-compose', 'up', '-d', '--scale', f"{labels.get('service')}=2"])
            log_remediation(f"Scaled up {labels.get('service')}")

    return jsonify({"status": "ok"})

def log_remediation(action):
    with open('/var/log/remediation.log', 'a') as f:
        f.write(f"{datetime.now()}: {action}\n")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

#### Bash-Based Remediation

Simple bash script for common remediations:

```bash
#!/bin/bash

# remediation.sh
ALERT_NAME=$1
INSTANCE=$2

case $ALERT_NAME in
    "HighMemoryUsage")
        echo "Restarting memory-intensive service on $INSTANCE"
        ssh user@$INSTANCE "sudo systemctl restart memory-service"
        ;;
    "ServiceDown")
        echo "Attempting to restart service on $INSTANCE"
        ssh user@$INSTANCE "sudo systemctl restart failed-service"
        ;;
    "DiskFull")
        echo "Cleaning logs on $INSTANCE"
        ssh user@$INSTANCE "sudo find /var/log -name '*.log' -exec truncate -s 0 {} \;"
        ;;
esac

echo "$(date): Remediation action taken for $ALERT_NAME on $INSTANCE" >> /var/log/remediation.log
```

### Multiple Alert Channels

#### Slack Integration

```yaml
receivers:
  - name: 'slack-critical'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts-critical'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ .CommonAnnotations.summary }}'
        color: 'danger'
        fields:
          - title: 'Severity'
            value: '{{ .Labels.severity }}'
          - title: 'Instance'
            value: '{{ .Labels.instance }}'

  - name: 'slack-warning'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts-warning'
        color: 'warning'
```

#### Telegram Integration

```yaml
receivers:
  - name: 'telegram'
    telegram_configs:
      - bot_token: 'YOUR_BOT_TOKEN'
        chat_id: 'YOUR_CHAT_ID'
        message: |
          *{{ .GroupLabels.alertname }}*
          {{ .CommonAnnotations.summary }}
          Severity: {{ .Labels.severity }}
          Instance: {{ .Labels.instance }}
        parse_mode: 'Markdown'
```

#### Microsoft Teams Integration

```yaml
receivers:
  - name: 'teams'
    webhook_configs:
      - url: 'YOUR_TEAMS_WEBHOOK_URL'
        http_config:
          headers:
            Content-Type: 'application/json'
        send_resolved: true
```

#### SMS Integration (via Twilio)

```yaml
receivers:
  - name: 'sms'
    webhook_configs:
      - url: 'http://sms-gateway:8080/send'
        http_config:
          basic_auth:
            username: 'twilio_account_sid'
            password: 'twilio_auth_token'
```

#### Email Integration

```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'alerts@company.com'
        from: 'alertmanager@company.com'
        smarthost: 'smtp.company.com:587'
        auth_username: 'alertmanager@company.com'
        auth_password: 'password'
        headers:
          subject: '{{ .GroupLabels.alertname }} - {{ .GroupLabels.severity }}'
        html: |
          <h2>{{ .GroupLabels.alertname }}</h2>
          <p>{{ .CommonAnnotations.summary }}</p>
          <table>
            <tr><td>Severity:</td><td>{{ .Labels.severity }}</td></tr>
            <tr><td>Instance:</td><td>{{ .Labels.instance }}</td></tr>
          </table>
```

### Alert Routing Based on Severity

Configure routing to send different severities to different channels:

```yaml
route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  routes:
    - match:
        severity: critical
      receiver: 'critical-alerts'
      routes:
        - match:
            team: devops
          receiver: 'devops-pager'
    - match:
        severity: warning
      receiver: 'warning-alerts'
    - match:
        severity: info
      receiver: 'info-alerts'
```

### Testing Alert Configurations

#### Manual Alert Testing

Create a test alert rule:

```yaml
      - alert: TestAlert
        expr: vector(1)  # Always true
        for: 0s
        labels:
          severity: info
        annotations:
          summary: "Test alert for configuration validation"
```

#### Alert Simulation

Use `amtool` to test alert routing:

```bash
# Test alert routing
amtool check-config alertmanager.yml

# Send test alert
amtool alert add --alertmanager.url=http://localhost:9093 \
  alertname=TestAlert severity=warning instance=test-server
```

#### Remediation Testing

Test remediation scripts in a safe environment:

```bash
# Test script execution
./remediation.sh TestAlert test-server

# Verify logs
tail -f /var/log/remediation.log
```

## System Maintenance

### Service Management

#### Starting/Stopping Services

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart grafana

# View service logs
docker-compose logs prometheus
```

#### Updating Images

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d
```

### Monitoring the Stack

#### Self-Monitoring Metrics

Prometheus exposes its own metrics at `/metrics`. Configure scraping:

```yaml
scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

#### Resource Usage

Monitor container resource usage:

```bash
docker stats
```

### Log Management

#### Viewing Logs

```bash
# All services
docker-compose logs

# Specific service with follow
docker-compose logs -f grafana

# Last 100 lines
docker-compose logs --tail=100 prometheus
```

#### Log Rotation

Configure Docker log rotation in daemon.json:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## Agent Deployment

### Linux Systems

#### Installing Node Exporter

1. Download the latest Node Exporter release:
   ```bash
   wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
   ```

2. Extract the archive:
   ```bash
   tar xvfz node_exporter-*.tar.gz
   cd node_exporter-*/
   ```

3. Copy the binary to system path:
   ```bash
   sudo cp node_exporter /usr/local/bin/
   ```

4. Create a systemd service user:
   ```bash
   sudo useradd -rs /bin/false node_exporter
   ```

5. Create systemd service file `/etc/systemd/system/node_exporter.service`:
   ```ini
   [Unit]
   Description=Node Exporter
   After=network.target

   [Service]
   User=node_exporter
   Group=node_exporter
   Type=simple
   ExecStart=/usr/local/bin/node_exporter

   [Install]
   WantedBy=multi-user.target
   ```

6. Start and enable the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start node_exporter
   sudo systemctl enable node_exporter
   ```

7. Verify the service is running:
   ```bash
   sudo systemctl status node_exporter
   curl http://localhost:9100/metrics
   ```

#### Connecting to Prometheus

Add the Linux host to Prometheus scrape configuration:

```yaml
scrape_configs:
  - job_name: 'linux-node'
    static_configs:
      - targets: ['linux-server:9100']
        labels:
          environment: 'production'
          server_type: 'linux'
```

Restart Prometheus to apply changes.

### Windows Systems

#### Installing Windows Exporter

1. Download the latest Windows Exporter MSI installer from:
   https://github.com/prometheus-community/windows_exporter/releases

2. Run the installer as Administrator, or install via command line:
   ```powershell
   msiexec /i windows_exporter-0.20.0-amd64.msi
   ```

3. The installer will:
   - Install the binary to `C:\Program Files\windows_exporter\`
   - Create a Windows service
   - Open firewall port 9182

4. Configure collectors (optional). Edit the service parameters to enable specific collectors:
   ```powershell
   # Stop the service first
   Stop-Service windows_exporter

   # Configure with specific collectors
   & "C:\Program Files\windows_exporter\windows_exporter.exe" --collectors.enabled="cpu,memory,disk,net,system"
   ```

5. Start the service:
   ```powershell
   Start-Service windows_exporter
   ```

6. Verify the service is running:
   ```powershell
   Get-Service windows_exporter
   # Or check in services.msc
   ```

7. Test metrics endpoint:
   Open browser to http://localhost:9182/metrics

#### Connecting to Prometheus

Add the Windows host to Prometheus scrape configuration:

```yaml
scrape_configs:
  - job_name: 'windows-node'
    static_configs:
      - targets: ['windows-server:9182']
        labels:
          environment: 'production'
          server_type: 'windows'
          os: 'windows'
```

Restart Prometheus to apply changes.

### Additional Agent Configuration

#### Custom Labels

Add custom labels for better organization:

```yaml
scrape_configs:
  - job_name: 'linux-node'
    static_configs:
      - targets: ['linux-server:9100']
        labels:
          environment: 'production'
          datacenter: 'dc1'
          team: 'infrastructure'
```

#### Service Discovery

For dynamic environments, consider using service discovery instead of static targets:

- DNS-based discovery
- Kubernetes service discovery
- Consul-based discovery
- EC2 service discovery

#### Security Considerations

- Use HTTPS for metric scraping in production
- Implement authentication for exporters
- Configure firewalls to restrict access to exporter ports
- Regularly update exporters for security patches

## Security

### Authentication

#### Grafana Authentication

Enable LDAP/OAuth in `grafana/grafana.ini`:

```ini
[auth.ldap]
enabled = true
config_file = /etc/grafana/ldap.toml
```

#### Basic Auth for Prometheus

Add to prometheus.yml:

```yaml
scrape_configs:
  - job_name: 'secure-endpoint'
    basic_auth:
      username: 'user'
      password: 'password'
    static_configs:
      - targets: ['secure-target:9090']
```

### Network Security

#### Firewall Configuration

Ensure only necessary ports are exposed:

- Grafana: 3000
- Prometheus: 9090 (internal access recommended)
- Alertmanager: 9093 (internal access recommended)
- Exporters: respective ports

#### TLS/SSL

Configure reverse proxy (nginx/traefik) for SSL termination.

### Access Control

#### Prometheus RBAC

Use middleware like prometheus-auth for role-based access.

#### Grafana Permissions

Fine-tune permissions at organization, team, and dashboard levels.

## Troubleshooting

### Common Issues

#### Services Not Starting

1. Check resource availability (CPU, memory)
2. Verify port conflicts
3. Review configuration syntax
4. Check Docker logs

#### Missing Metrics

1. Verify target connectivity
2. Check scrape intervals
3. Validate PromQL syntax
4. Ensure proper labels

#### Alert Fatigue

1. Tune alert thresholds
2. Implement alert grouping
3. Use inhibition rules
4. Regularly review and update rules

#### Performance Issues

1. Monitor resource usage
2. Adjust scrape intervals
3. Implement metric filtering
4. Consider horizontal scaling

### Diagnostic Commands

```bash
# Check container health
docker ps

# Inspect container
docker inspect <container_id>

# Execute commands in container
docker exec -it infraeye_prometheus_1 /bin/sh

# Network connectivity
docker network inspect infraeye_infraeyet
```

## Backup and Recovery

### Data Backup

#### Prometheus Data

```bash
# Stop Prometheus
docker-compose stop prometheus

# Backup data
docker run --rm -v infraeye_prometheus_data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus_backup.tar.gz -C /data .

# Start Prometheus
docker-compose start prometheus
```

#### Grafana Data

```bash
# Backup Grafana database
docker exec infraeye_grafana_1 sqlite3 /var/lib/grafana/grafana.db .dump > grafana_backup.sql
```

### Configuration Backup

```bash
# Backup all configs
tar czf config_backup.tar.gz prometheus/ grafana/ alertmanager/ blackbox_exporter/ docker-compose.yml
```

### Recovery Procedures

#### Restore Prometheus

```bash
docker-compose stop prometheus
docker run --rm -v infraeye_prometheus_data:/data -v $(pwd):/backup alpine sh -c "cd /data && tar xzf /backup/prometheus_backup.tar.gz"
docker-compose start prometheus
```

#### Restore Grafana

```bash
docker exec -i infraeye_grafana_1 sqlite3 /var/lib/grafana/grafana.db < grafana_backup.sql
```

### Disaster Recovery

1. Prepare backup scripts
2. Document recovery procedures
3. Test recovery regularly
4. Maintain offsite backups

## Performance Tuning

### Prometheus Optimization

- Use appropriate scrape intervals
- Implement metric relabeling
- Configure data retention policies
- Use remote write for long-term storage

### Grafana Optimization

- Limit dashboard refresh rates
- Use appropriate panel types
- Implement query caching
- Configure resource limits

### Scaling Considerations

- Horizontal scaling for high availability
- Load balancing
- Federation for multi-region setups
- External storage for large deployments

## Monitoring Best Practices

- Implement service level objectives (SLOs)
- Use the Four Golden Signals (latency, traffic, errors, saturation)
- Regularly review and update alerting rules
- Automate as much as possible
- Document all procedures and runbooks

## Support and Resources

For additional help:
- Prometheus documentation: https://prometheus.io/docs/
- Grafana documentation: https://grafana.com/docs/
- Alertmanager documentation: https://prometheus.io/docs/alerting/latest/alertmanager/
- Community forums and Slack channels

Remember to keep this guide updated as your InfraEye deployment evolves.