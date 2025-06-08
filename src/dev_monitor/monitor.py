"""Core monitoring functionality for development projects."""
import os
import time
import subprocess
import logging
from pathlib import Path

class DevMonitor:
    def __init__(self, log_dir="logs", interval=15):  # pylint: disable=too-many-arguments
        self.log_dir = Path(log_dir)
        self.interval = interval
        self.logger = logging.getLogger("dev_monitor")
        self.logger.setLevel(logging.INFO)
        self.active_sections = set()
        
    def setup_logging(self):
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
    def capture_command(self, cmd, max_lines=100):  # pylint: disable=too-many-arguments
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60,
                check=False
            )
            return '\n'.join(result.stdout.splitlines()[-max_lines:])
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            return f"Error: {str(e)}"
            
    def _get_section_output(self, section, header, command):  # pylint: disable=too-many-arguments
        """Generate output for a specific section."""
        if section in self.active_sections:
            return f"\n{header}\n{self.capture_command(command)}"
        return ""
            
    def _build_output(self, sections):
        self.active_sections = set(sections)
        output = f"============={time.ctime()}=============\n"
        if "docker" in sections and self._has_docker_compose():
            output += self._get_section_output("docker", "[DOCKER LOGS]", "docker compose logs --tail=40 --no-color")
        if "pytest" in sections:
            output += self._get_section_output("pytest", "[PYTEST OUTPUT]", "pytest --timeout=10")
        if "pylint" in sections:
            output += self._get_section_output("pylint", "[PYLINT OUTPUT]", "pylint --ignore=src/__init__.py src")
        return output
            
    def run(self, sections):
        self.setup_logging()
        while True:
            output = self._build_output(sections)
            with open(self.log_dir / "context.txt", "w", encoding="utf-8") as f:
                f.write(output)
            time.sleep(self.interval)
            
    def _has_docker_compose(self):
        return os.path.exists("docker-compose.yml") or os.path.exists("docker-compose.yaml")
