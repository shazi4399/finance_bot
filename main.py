#!/usr/bin/env python3
"""
Content Intelligence Pipeline Main Entry Point
企业级自动化内容情报流水线主入口

Usage:
    python main.py [--config config.yaml] [--daemon] [--check-once]
"""

import argparse
import os
import signal
import sys
import time

import schedule

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.pipeline import ContentIntelligencePipeline
from src.utils.config import Config
from src.utils.logger import get_logger, setup_logger


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger = get_logger()
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Content Intelligence Pipeline")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon with scheduled checks")
    parser.add_argument("--check-once", action="store_true", help="Run check once and exit")
    parser.add_argument("--manual", type=str, help="Manually process a specific BVID (e.g. BV1xxxx)")
    parser.add_argument("--validate-config", action="store_true", help="Validate configuration and exit")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logger(name="pipeline", log_file="logs/pipeline.log", level="INFO")

    try:
        # Load configuration
        config = Config(args.config)

        # Validate configuration if requested
        if args.validate_config:
            if config.validate_required():
                logger.info("Configuration validation passed")
                sys.exit(0)
            else:
                logger.error("Configuration validation failed")
                sys.exit(1)

        # Initialize pipeline
        pipeline = ContentIntelligencePipeline(config)

        if args.manual:
            # Run manual processing for specific video
            logger.info(f"Running manual processing for {args.manual}...")
            result = pipeline.run_manual(args.manual)
            if result.get("success"):
                logger.info("Manual processing completed successfully")
                sys.exit(0)
            else:
                logger.error("Manual processing failed")
                sys.exit(1)
        elif args.check_once:
            # Run once and exit
            logger.info("Running single check...")
            pipeline.run_check()
            logger.info("Check completed")
        else:
            # Setup signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            if args.daemon:
                # Run as daemon with scheduled checks
                interval = config.get("monitoring.check_interval", 3600)
                logger.info(f"Starting daemon mode, checking every {interval} seconds...")

                schedule.every(interval).seconds.do(pipeline.run_check)

                while True:
                    schedule.run_pending()
                    time.sleep(1)
            else:
                # Run once (default behavior)
                logger.info("Running pipeline...")
                pipeline.run_check()
                logger.info("Pipeline completed")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
