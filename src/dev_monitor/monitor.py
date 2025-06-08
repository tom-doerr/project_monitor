"""Core monitoring functionality for development projects."""
import os
import time
import subprocess
import logging
from pathlib import Path

class DevMonitor:
    def __init__(self, log_dir="logs", interval=15):
        self.log_dir = Path(log_dir)
        self.interval = interval
        self.logger = logging.getLogger("dev_monitor")
        self.logger.setLevel(logging.INFO)
        
    def setup_logging(self):
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
    def capture_command(self, cmd, max_lines=100):
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60
            )
            return '\n'.join(result.stdout.splitlines()[-max_lines:])
        except Exception as e:
            return f"Error: {str(e)}"
            
    def run(self, sections):
        self.setup_logging()
        while True:
            output = f"============={time.ctime()}=============\n"
            
            if "docker" in sections and self._has_docker_compose():
                output += "\n[DOCKER LOGS]\n"
                output += self.capture_command("docker compose logs --tail=40 --no-color")
                
            if "pytest" in sections:
                output += "\n[PYTEST OUTPUT]\n"
                output += self.capture_command("pytest --timeout=10")
                
            if "pylint" in sections:
                output += "\n[PYLINT OUTPUT]\n"
                output += self.capture_command("pylint $(git ls-files '*.py')")
                
            with open(self.log_dir / "context.txt", "w") as f:
                f.write(output)
                
            time.sleep(self.interval)
            
    def _has_docker_compose(self):
        return os.path.exists("docker-compose.yml") or os.path.exists("docker-compose.yaml")
