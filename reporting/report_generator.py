#!/usr/bin/env python3
"""
InfraEye Automated Reporting Service
Generates weekly/monthly reports on system health, trends, and security metrics.
"""

import time
import requests
import json
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import schedule
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InfraEyeReporter:
    def __init__(self):
        self.prometheus_url = os.getenv('PROMETHEUS_URL', 'http://localhost:9090')
        self.victoriametrics_url = os.getenv('VICTORIAMETRICS_URL', 'http://localhost:8428')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_pass = os.getenv('SMTP_PASS', '')
        self.report_recipients = os.getenv('REPORT_RECIPIENTS', '').split(',')

        # Report output directory
        self.report_dir = '/tmp/reports'
        os.makedirs(self.report_dir, exist_ok=True)

    def query_prometheus(self, query, start=None, end=None, step='15s'):
        """Query Prometheus for metrics"""
        try:
            params = {'query': query}
            if start and end:
                params.update({
                    'start': start.timestamp(),
                    'end': end.timestamp(),
                    'step': step
                })

            response = requests.get(f"{self.prometheus_url}/api/v1/query{'_range' if start else ''}",
                                  params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error querying Prometheus: {e}")
            return None

    def query_victoriametrics(self, query, start=None, end=None, step='1h'):
        """Query VictoriaMetrics for long-term data"""
        try:
            params = {'query': query}
            if start and end:
                params.update({
                    'start': start.timestamp(),
                    'end': end.timestamp(),
                    'step': step
                })

            response = requests.get(f"{self.victoriametrics_url}/api/v1/query{'_range' if start else ''}",
                                  params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error querying VictoriaMetrics: {e}")
            return None

    def generate_weekly_report(self):
        """Generate weekly system health report"""
        logger.info("Generating weekly report...")

        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)

        report = {
            'report_type': 'weekly',
            'period': f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}",
            'generated_at': datetime.now().isoformat(),
            'metrics': {}
        }

        # System Metrics
        queries = {
            'cpu_usage_avg': '100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            'memory_usage_avg': '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100',
            'disk_usage': '(node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100',
            'service_uptime': 'up',
            'failed_logins': 'infraeye_security_failed_logins',
            'network_connections': 'infraeye_security_network_connections'
        }

        for metric_name, query in queries.items():
            data = self.query_victoriametrics(query, start_time, end_time, '1h')
            if data and 'data' in data and 'result' in data['data']:
                report['metrics'][metric_name] = data['data']['result']

        # Generate HTML report
        html_content = self.generate_html_report(report)

        # Save report
        filename = f"weekly_report_{end_time.strftime('%Y%m%d')}.html"
        filepath = os.path.join(self.report_dir, filename)

        with open(filepath, 'w') as f:
            f.write(html_content)

        logger.info(f"Weekly report saved to {filepath}")

        # Send email if configured
        self.send_email_report(html_content, "InfraEye Weekly Report", filename)

        return filepath

    def generate_monthly_report(self):
        """Generate monthly trend analysis report"""
        logger.info("Generating monthly report...")

        end_time = datetime.now()
        start_time = end_time - timedelta(days=30)

        report = {
            'report_type': 'monthly',
            'period': f"{start_time.strftime('%Y-%m-%d')} to {end_time.strftime('%Y-%m-%d')}",
            'generated_at': datetime.now().isoformat(),
            'trends': {},
            'anomalies': []
        }

        # Trend Analysis Queries - use actual values instead of rates for trend analysis
        trend_queries = {
            'cpu_trend': '100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            'memory_trend': '(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100',
            'disk_trend': '(node_filesystem_used_bytes / node_filesystem_size_bytes) * 100',
            'network_rx': 'rate(node_network_receive_bytes_total[5m]) / 1024 / 1024',  # MB/s
            'network_tx': 'rate(node_network_transmit_bytes_total[5m]) / 1024 / 1024',  # MB/s
        }

        for trend_name, query in trend_queries.items():
            data = self.query_victoriametrics(query, start_time, end_time, '6h')
            if data and 'data' in data and 'result' in data['data']:
                report['trends'][trend_name] = data['data']['result']

        # Simple anomaly detection (basic threshold-based)
        anomalies = self.detect_anomalies(report['trends'])
        report['anomalies'] = anomalies

        # Generate HTML report
        html_content = self.generate_html_trend_report(report)

        # Save report
        filename = f"monthly_trend_report_{end_time.strftime('%Y%m%d')}.html"
        filepath = os.path.join(self.report_dir, filename)

        with open(filepath, 'w') as f:
            f.write(html_content)

        logger.info(f"Monthly trend report saved to {filepath}")

        # Send email if configured
        self.send_email_report(html_content, "InfraEye Monthly Trend Report", filename)

        return filepath

    def detect_anomalies(self, trends):
        """Simple anomaly detection based on statistical thresholds"""
        anomalies = []

        # CPU usage anomaly detection
        if 'cpu_trend' in trends and trends['cpu_trend']:
            for series in trends['cpu_trend']:
                if 'values' in series['values']:
                    values = []
                    for timestamp, value_str in series['values']:
                        try:
                            value = float(value_str)
                            values.append(value)
                        except (ValueError, TypeError):
                            continue

                    if values:
                        avg_cpu = sum(values) / len(values)
                        max_cpu = max(values)
                        # Flag if average > 70% or peak > 90%
                        if avg_cpu > 70 or max_cpu > 90:
                            severity = 'critical' if max_cpu > 95 else 'warning'
                            anomalies.append({
                                'type': 'high_cpu_usage',
                                'metric': 'cpu_trend',
                                'severity': severity,
                                'description': f"CPU usage anomaly - Avg: {avg_cpu:.1f}%, Peak: {max_cpu:.1f}%",
                                'timestamp': datetime.now().isoformat()
                            })

        # Memory usage anomaly detection
        if 'memory_trend' in trends and trends['memory_trend']:
            for series in trends['memory_trend']:
                if 'values' in series['values']:
                    values = []
                    for timestamp, value_str in series['values']:
                        try:
                            value = float(value_str)
                            values.append(value)
                        except (ValueError, TypeError):
                            continue

                    if values:
                        avg_memory = sum(values) / len(values)
                        max_memory = max(values)
                        # Flag high memory usage (assuming MB values)
                        if max_memory > 1000:  # More than 1GB sustained usage
                            anomalies.append({
                                'type': 'high_memory_usage',
                                'metric': 'memory_trend',
                                'severity': 'warning',
                                'description': f"High memory usage - Avg: {avg_memory:.0f}MB, Peak: {max_memory:.0f}MB",
                                'timestamp': datetime.now().isoformat()
                            })

        # Disk growth anomaly detection
        if 'disk_trend' in trends and trends['disk_trend']:
            for series in trends['disk_trend']:
                if 'values' in series['values']:
                    values = []
                    for timestamp, value_str in series['values']:
                        try:
                            value = float(value_str)
                            values.append(value)
                        except (ValueError, TypeError):
                            continue

                    if values and len(values) > 1:
                        # Calculate growth rate trend
                        recent_avg = sum(values[-10:]) / len(values[-10:]) if len(values) >= 10 else sum(values) / len(values)
                        overall_avg = sum(values) / len(values)

                        # Flag if recent growth is significantly higher
                        if recent_avg > overall_avg * 1.5 and recent_avg > 0.1:  # 0.1 GB/hour increase
                            anomalies.append({
                                'type': 'disk_growth_spike',
                                'metric': 'disk_trend',
                                'severity': 'warning',
                                'description': f"Disk growth spike detected - Recent: {recent_avg:.2f}GB/h, Overall: {overall_avg:.2f}GB/h",
                                'timestamp': datetime.now().isoformat()
                            })

        return anomalies

    def generate_html_report(self, report):
        """Generate HTML report for weekly metrics"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>InfraEye Weekly Report - {report['period']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .metric {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric h3 {{ margin-top: 0; color: #333; }}
                .status-good {{ color: #28a745; }}
                .status-warning {{ color: #ffc107; }}
                .status-critical {{ color: #dc3545; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>InfraEye Weekly Report</h1>
                <p><strong>Period:</strong> {report['period']}</p>
                <p><strong>Generated:</strong> {report['generated_at']}</p>
            </div>

            <div class="metric">
                <h3>System Health Overview</h3>
                <p>This report summarizes key system metrics and security events for the past week.</p>
            </div>

            <div class="metric">
                <h3>Key Metrics</h3>
                <ul>
                    <li><strong>Services Monitored:</strong> {sum([len(m.get('values', [])) for m in report['metrics'].get('service_uptime', []) if m.get('values')])} service checks</li>
                    <li><strong>Security Events:</strong> {sum([sum([1 for v in m.get('values', []) if len(v) > 1 and float(v[1]) > 0]) for m in report['metrics'].get('failed_logins', [])])} failed login attempts</li>
                </ul>
            </div>
        </body>
        </html>
        """
        return html

    def generate_html_trend_report(self, report):
        """Generate HTML report for monthly trends"""
        anomalies_html = ""
        if report['anomalies']:
            anomalies_html = "<h3>Detected Anomalies</h3><ul>"
            for anomaly in report['anomalies']:
                anomalies_html += f"<li class='status-{anomaly['severity']}'>{anomaly['description']} ({anomaly['timestamp']})</li>"
            anomalies_html += "</ul>"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>InfraEye Monthly Trend Report - {report['period']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .metric {{ margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .metric h3 {{ margin-top: 0; color: #333; }}
                .trend-up {{ color: #28a745; }}
                .trend-down {{ color: #dc3545; }}
                .trend-stable {{ color: #6c757d; }}
                .status-good {{ color: #28a745; }}
                .status-warning {{ color: #ffc107; }}
                .status-critical {{ color: #dc3545; }}
                .anomalies {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>InfraEye Monthly Trend Analysis</h1>
                <p><strong>Period:</strong> {report['period']}</p>
                <p><strong>Generated:</strong> {report['generated_at']}</p>
            </div>

            <div class="metric">
                <h3>Trend Analysis Summary</h3>
                <p>This report analyzes system trends and detects potential anomalies over the past month.</p>
                {anomalies_html}
            </div>

            <div class="metric">
                <h3>Performance Trends</h3>
                <p>Key performance indicators show system behavior patterns and resource utilization trends.</p>
            </div>
        </body>
        </html>
        """
        return html

    def send_email_report(self, html_content, subject, filename):
        """Send report via email"""
        if not all([self.smtp_user, self.smtp_pass, self.report_recipients]):
            logger.info("Email not configured, skipping email send")
            return

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(self.report_recipients)

            part = MIMEText(html_content, 'html')
            msg.attach(part)

            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.smtp_user, self.report_recipients, msg.as_string())
            server.quit()

            logger.info(f"Report emailed to {self.report_recipients}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")

def main():
    reporter = InfraEyeReporter()

    # Schedule reports
    schedule.every().monday.at("09:00").do(reporter.generate_weekly_report)
    # Note: schedule library doesn't support monthly scheduling, using weekly for now
    # For production, consider using cron jobs or a more advanced scheduler
    schedule.every(30).days.at("09:00").do(reporter.generate_monthly_report)

    logger.info("InfraEye Reporting Service started")
    logger.info("Weekly reports: Every Monday at 09:00")
    logger.info("Monthly reports: Every 30 days at 09:00")

    # Run initial report for testing
    reporter.generate_weekly_report()

    # Keep the service running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == '__main__':
    main()