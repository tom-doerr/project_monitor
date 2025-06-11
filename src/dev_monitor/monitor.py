"""Core monitoring functionality for development projects."""
import os
import time
import subprocess
import logging
from pathlib import Path

class DevMonitor:
    SECTIONS = {
        "docker": {
            "command": "docker compose logs --tail=40 --no-color",
            "condition": lambda self: self.has_docker_compose(),
            "max_lines": 40,
        },
        "pytest": {
            "command": "pytest --timeout=10",
            "condition": lambda self: True,
            "max_lines": 100,
        },
        "pylint": {
            "command": "pylint --ignore=src/__init__.py .",
            "condition": lambda self: True,
            "max_lines": 100,
        },
    }

    def __init__(self, **kwargs):
        self.log_dir = Path(kwargs.get("log_dir", "logs"))
        self.interval = kwargs.get("interval", 15)
        self.logger = logging.getLogger("dev_monitor")
        self.logger.setLevel(logging.INFO)
        self.active_sections = set()

    def setup_logging(self):
        self.log_dir.mkdir(exist_ok=True, parents=True)

    def capture_command(self, command_config):
        try:
            result = subprocess.run(
                command_config["command"],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60,
                check=False,
            )
            return "\n".join(
                result.stdout.splitlines()[-command_config.get("max_lines", 100):]
            )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
            return f"Error: {str(e)}"

    def _get_section_output(self, section):
        """Generate output for a specific section."""
        output_str = ""
        section_config = self.SECTIONS.get(section)

        if section_config and section_config["condition"](self):
            output = self.capture_command(section_config)
            if output.strip():
                output_str = f"[{time.ctime()}] \n{output}\n"
        return output_str

    def has_docker_compose(self):
        return os.path.exists("docker-compose.yml") or os.path.exists(
            "docker-compose.yaml"
        )

    def _build_output(self, sections):
        self.active_sections = set(sections)
        output_parts = [f"============={time.ctime()}=============\n"]
        for section in self.SECTIONS:
            if section in self.active_sections:
                output_parts.append(self._get_section_output(section))
        return "".join(output_parts)

    def run(self, sections):
        self.setup_logging()
        while True:
            output = self._build_output(sections)
            with open(self.log_dir / "context.txt", "w", encoding="utf-8") as f:
                f.write(output)
            time.sleep(self.interval)
