"""Command-line interface for dev_monitor."""
import argparse
from .monitor import DevMonitor

def parse_args():
    parser = argparse.ArgumentParser(description="Development Environment Monitor")
    parser.add_argument("--log-dir", default="logs", help="Log directory")
    parser.add_argument("--interval", type=int, default=15, help="Update interval (seconds)")
    parser.add_argument("--sections", nargs="+", default=["docker", "pytest", "pylint"],
                        choices=["docker", "pytest", "pylint"],
                        help="Sections to monitor")
    return parser.parse_args()

def main():
    args = parse_args()
    monitor = DevMonitor(
        log_dir=args.log_dir,
        interval=args.interval
    )
    
    print(f"Starting dev-monitor. Monitoring: {', '.join(args.sections)}")
    print(f"Logs directory: {args.log_dir}")
    print(f"Update interval: {args.interval}s")
    print("Press Ctrl+C to exit...")
    
    try:
        monitor.run(args.sections)
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

if __name__ == "__main__":
    main()
