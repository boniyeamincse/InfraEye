#!/usr/bin/env python3
"""
InfraEye Security Exporter
A lightweight Prometheus exporter for network and security monitoring.
"""

import time
import subprocess
import re
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import argparse

class SecurityMetrics:
    def __init__(self):
        self.previous_ports = set()
        self.failed_login_count = 0
        self.last_log_check = 0
        self.network_connections = 0
        self.log_positions = {}  # Track file positions for incremental reading

    def get_open_ports(self):
        """Get currently open listening ports"""
        try:
            # Use ss for better IPv6 support
            result = subprocess.run(['ss', '-tln'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                # Fallback to netstat
                result = subprocess.run(['netstat', '-tln'], capture_output=True, text=True, timeout=10)

            ports = set()
            for line in result.stdout.split('\n'):
                if 'LISTEN' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        addr = parts[3]
                        # Handle IPv4:port and [IPv6]:port formats
                        if addr.startswith('[') and ']:' in addr:
                            # IPv6 format: [::1]:80
                            port_part = addr.split(']:')[-1]
                        elif ':' in addr:
                            # IPv4 format: 0.0.0.0:80 or ::1:80
                            port_part = addr.split(':')[-1]
                        else:
                            # Fallback
                            port_part = addr

                        try:
                            port = int(port_part)
                            if 1 <= port <= 65535:  # Valid port range
                                ports.add(port)
                        except ValueError:
                            continue
            return ports
        except Exception as e:
            print(f"Error getting open ports: {e}")
            return set()

    def check_port_changes(self):
        """Check for changes in open ports"""
        current_ports = self.get_open_ports()
        added = current_ports - self.previous_ports
        removed = self.previous_ports - current_ports
        self.previous_ports = current_ports
        return added, removed

    def get_failed_logins(self):
        """Parse auth logs for failed login attempts (incremental counting)"""
        try:
            log_files = ['/var/log/auth.log', '/var/log/secure']
            new_failed_count = 0
            current_time = time.time()

            for log_file in log_files:
                try:
                    if not os.path.exists(log_file):
                        continue

                    # Get current file size
                    current_size = os.path.getsize(log_file)
                    last_position = self.log_positions.get(log_file, 0)

                    # If file was truncated or this is first run, start from beginning
                    if current_size < last_position:
                        last_position = 0

                    with open(log_file, 'r') as f:
                        if last_position > 0:
                            f.seek(last_position)

                        for line in f:
                            if 'Failed password' in line or 'authentication failure' in line:
                                # Check if this is a recent failure (within last 5 minutes)
                                # This prevents recounting old failures on restart
                                try:
                                    # Extract timestamp if available (basic check)
                                    if current_time - self.last_log_check < 300:  # Within 5 minutes
                                        new_failed_count += 1
                                except:
                                    new_failed_count += 1

                    # Update position for next check
                    self.log_positions[log_file] = current_size

                except (FileNotFoundError, OSError) as e:
                    print(f"Error reading {log_file}: {e}")
                    continue

            self.last_log_check = current_time
            return new_failed_count
        except Exception as e:
            print(f"Error reading auth logs: {e}")
            return 0

    def get_network_connections(self):
        """Get basic network connection metrics"""
        try:
            result = subprocess.run(['ss', '-t'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                result = subprocess.run(['netstat', '-t'], capture_output=True, text=True, timeout=10)

            connections = 0
            for line in result.stdout.split('\n'):
                if 'ESTAB' in line:
                    connections += 1
            return connections
        except Exception as e:
            print(f"Error getting network connections: {e}")
            return 0

    def collect_metrics(self):
        """Collect all security metrics"""
        added_ports, removed_ports = self.check_port_changes()
        current_failed = self.get_failed_logins()
        connections = self.get_network_connections()

        return {
            'ports_current': len(self.previous_ports),
            'ports_added': len(added_ports),
            'ports_removed': len(removed_ports),
            'failed_logins': current_failed,
            'network_connections': connections
        }

class MetricsHandler(BaseHTTPRequestHandler):
    def __init__(self, metrics_collector, *args, **kwargs):
        self.metrics_collector = metrics_collector
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()

            metrics = self.metrics_collector.collect_metrics()

            output = []
            output.append('# HELP infraeye_security_open_ports_current Current number of open listening ports')
            output.append('# TYPE infraeye_security_open_ports_current gauge')
            output.append(f'infraeye_security_open_ports_current {metrics["ports_current"]}')

            output.append('# HELP infraeye_security_ports_added Ports opened since last check')
            output.append('# TYPE infraeye_security_ports_added gauge')
            output.append(f'infraeye_security_ports_added {metrics["ports_added"]}')

            output.append('# HELP infraeye_security_ports_removed Ports closed since last check')
            output.append('# TYPE infraeye_security_ports_removed gauge')
            output.append(f'infraeye_security_ports_removed {metrics["ports_removed"]}')

            output.append('# HELP infraeye_security_failed_logins Failed login attempts')
            output.append('# TYPE infraeye_security_failed_logins counter')
            output.append(f'infraeye_security_failed_logins {metrics["failed_logins"]}')

            output.append('# HELP infraeye_security_network_connections Current established connections')
            output.append('# TYPE infraeye_security_network_connections gauge')
            output.append(f'infraeye_security_network_connections {metrics["network_connections"]}')

            self.wfile.write('\n'.join(output).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        return  # Suppress log messages

def run_server(metrics_collector, port=8000):
    def handler(*args, **kwargs):
        MetricsHandler(metrics_collector, *args, **kwargs)

    server = HTTPServer(('0.0.0.0', port), handler)
    print(f"Security exporter listening on port {port}")
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser(description='InfraEye Security Exporter')
    parser.add_argument('--port', type=int, default=8001, help='Port to listen on')
    args = parser.parse_args()

    metrics = SecurityMetrics()

    # Initialize previous ports
    metrics.previous_ports = metrics.get_open_ports()

    # Start HTTP server in a thread
    server_thread = threading.Thread(target=run_server, args=(metrics, args.port))
    server_thread.daemon = True
    server_thread.start()

    print("InfraEye Security Exporter started")
    print("Metrics available at: http://localhost:{}/metrics".format(args.port))

    try:
        while True:
            time.sleep(30)  # Update metrics every 30 seconds
    except KeyboardInterrupt:
        print("Shutting down...")

if __name__ == '__main__':
    main()