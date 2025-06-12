"""Command-line interface for dev_monitor."""
import argparse
import sys
from .monitor import DevMonitor

def parse_args(args=None):
    """Parse command line arguments.

    When *args* is ``None`` an empty list is used so that pytest's own command
    line options do not interfere during testing.  The :func:`main` function
    passes ``sys.argv[1:]`` to parse the real command line when executed as a
    script.
    """
    parser = argparse.ArgumentParser(description="Development Environment Monitor")
    parser.add_argument("--log-dir", default="logs", help="Log directory")
    parser.add_argument("--interval", type=int, default=1, help="Update interval (seconds) [default: 1]")
    parser.add_argument("--sections", nargs="+", default=["docker", "pytest", "pylint"],
                        choices=["docker", "pytest", "pylint"],
                        help="Sections to monitor [default: all]")
    return parser.parse_args([] if args is None else args)

def print_startup_message(args):
    """Print startup message with configuration details."""
    print(f"Starting dev-monitor. Monitoring: {', '.join(args.sections)}")
    print(f"Logs directory: {args.log_dir}")
    print(f"Update interval: {args.interval}s")
    print("Press Ctrl+C to exit...")

def main():
    args = parse_args(sys.argv[1:])
    monitor = DevMonitor(
        log_dir=args.log_dir,
        interval=args.interval
    )
    
    print_startup_message(args)
    
    try:
        monitor.run(args.sections)
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

if __name__ == "__main__":
    main()
