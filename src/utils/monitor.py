"""Pipeline monitoring and metrics collection"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.utils.logger import get_logger


class PipelineMonitor:
    """Pipeline monitoring and metrics collection"""

    def __init__(self, metrics_file: str = "data/metrics.json"):
        """
        Initialize pipeline monitor

        Args:
            metrics_file: File to store metrics
        """
        self.metrics_file = metrics_file
        self.logger = get_logger()

        # Ensure data directory exists
        os.makedirs(os.path.dirname(metrics_file), exist_ok=True)

        # Initialize metrics
        self.metrics = self._load_metrics()

    def _load_metrics(self) -> Dict[str, Any]:
        """Load metrics from file"""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                return self._init_metrics()
        except Exception as e:
            self.logger.error(f"Failed to load metrics: {e}")
            return self._init_metrics()

    def _init_metrics(self) -> Dict[str, Any]:
        """Initialize default metrics"""
        return {
            "pipeline": {
                "total_runs": 0,
                "successful_runs": 0,
                "failed_runs": 0,
                "total_videos_processed": 0,
                "total_videos_successful": 0,
                "total_videos_failed": 0,
                "average_execution_time": 0.0,
                "last_run_time": None,
                "last_success_time": None,
            },
            "stages": {
                "download": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_time": 0.0,
                },
                "upload": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_time": 0.0,
                },
                "transcription": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_time": 0.0,
                },
                "analysis": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_time": 0.0,
                },
                "rendering": {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "average_time": 0.0,
                },
            },
            "errors": [],
            "daily_stats": {},
            "created_at": datetime.now().isoformat(),
        }

    def save_metrics(self):
        """Save metrics to file"""
        try:
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def record_pipeline_run(self, result: Dict[str, Any]):
        """
        Record pipeline run metrics

        Args:
            result: Pipeline run result
        """
        try:
            pipeline_metrics = self.metrics["pipeline"]

            # Update pipeline metrics
            pipeline_metrics["total_runs"] += 1
            pipeline_metrics["last_run_time"] = datetime.now().isoformat()

            execution_time = result.get("execution_time", 0)
            pipeline_metrics["average_execution_time"] = (
                pipeline_metrics["average_execution_time"] * (pipeline_metrics["total_runs"] - 1) + execution_time
            ) / pipeline_metrics["total_runs"]

            # Update video metrics
            total_processed = result.get("total_processed", 0)
            successful_count = result.get("successful_count", 0)
            failed_count = result.get("failed_count", 0)

            pipeline_metrics["total_videos_processed"] += total_processed
            pipeline_metrics["total_videos_successful"] += successful_count
            pipeline_metrics["total_videos_failed"] += failed_count

            if failed_count == 0:
                pipeline_metrics["successful_runs"] += 1
                pipeline_metrics["last_success_time"] = datetime.now().isoformat()
            else:
                pipeline_metrics["failed_runs"] += 1

            # Update daily stats
            self._update_daily_stats(result)

            # Record errors if any
            errors = result.get("errors", [])
            for error in errors:
                self.record_error(error)

            # Save metrics
            self.save_metrics()

            self.logger.info(f"Pipeline run recorded: {successful_count}/{total_processed} videos successful")

        except Exception as e:
            self.logger.error(f"Failed to record pipeline run: {e}")

    def record_stage_metrics(self, stage: str, success: bool, execution_time: float = 0):
        """
        Record stage metrics

        Args:
            stage: Stage name
            success: Whether stage was successful
            execution_time: Stage execution time
        """
        try:
            if stage not in self.metrics["stages"]:
                return

            stage_metrics = self.metrics["stages"][stage]
            stage_metrics["total"] += 1

            if success:
                stage_metrics["successful"] += 1
            else:
                stage_metrics["failed"] += 1

            if execution_time > 0:
                stage_metrics["average_time"] = (
                    stage_metrics["average_time"] * (stage_metrics["total"] - 1) + execution_time
                ) / stage_metrics["total"]

            self.save_metrics()

        except Exception as e:
            self.logger.error(f"Failed to record stage metrics: {e}")

    def record_error(self, error: str):
        """
        Record error

        Args:
            error: Error message
        """
        try:
            error_record = {"timestamp": datetime.now().isoformat(), "error": error}

            self.metrics["errors"].append(error_record)

            # Keep only last 100 errors
            if len(self.metrics["errors"]) > 100:
                self.metrics["errors"] = self.metrics["errors"][-100:]

            self.save_metrics()

        except Exception as e:
            self.logger.error(f"Failed to record error: {e}")

    def _update_daily_stats(self, result: Dict[str, Any]):
        """Update daily statistics"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")

            if today not in self.metrics["daily_stats"]:
                self.metrics["daily_stats"][today] = {
                    "runs": 0,
                    "successful_runs": 0,
                    "videos_processed": 0,
                    "videos_successful": 0,
                    "execution_time": 0.0,
                }

            daily_stats = self.metrics["daily_stats"][today]
            daily_stats["runs"] += 1

            execution_time = result.get("execution_time", 0)
            daily_stats["execution_time"] += execution_time

            total_processed = result.get("total_processed", 0)
            successful_count = result.get("successful_count", 0)

            daily_stats["videos_processed"] += total_processed
            daily_stats["videos_successful"] += successful_count

            if result.get("failed_count", 0) == 0:
                daily_stats["successful_runs"] += 1

            # Clean up old daily stats (keep last 30 days)
            cutoff_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            self.metrics["daily_stats"] = {
                date: stats for date, stats in self.metrics["daily_stats"].items() if date >= cutoff_date
            }

        except Exception as e:
            self.logger.error(f"Failed to update daily stats: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()

    def get_success_rate(self, period: str = "overall") -> float:
        """
        Get success rate for a period

        Args:
            period: Period to calculate success rate for (overall/today/week)

        Returns:
            Success rate as percentage
        """
        try:
            if period == "overall":
                pipeline_metrics = self.metrics["pipeline"]
                total = pipeline_metrics["total_videos_processed"]
                successful = pipeline_metrics["total_videos_successful"]
            elif period == "today":
                today = datetime.now().strftime("%Y-%m-%d")
                if today not in self.metrics["daily_stats"]:
                    return 0.0

                daily_stats = self.metrics["daily_stats"][today]
                total = daily_stats["videos_processed"]
                successful = daily_stats["videos_successful"]
            elif period == "week":
                # Calculate last 7 days
                week_total = 0
                week_successful = 0

                for i in range(7):
                    date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                    if date in self.metrics["daily_stats"]:
                        daily_stats = self.metrics["daily_stats"][date]
                        week_total += daily_stats["videos_processed"]
                        week_successful += daily_stats["videos_successful"]

                total = week_total
                successful = week_successful
            else:
                return 0.0

            if total == 0:
                return 0.0

            return (successful / total) * 100.0

        except Exception as e:
            self.logger.error(f"Failed to calculate success rate: {e}")
            return 0.0

    def get_stage_success_rates(self) -> Dict[str, float]:
        """Get success rates for all stages"""
        success_rates = {}

        try:
            for stage, metrics in self.metrics["stages"].items():
                total = metrics["total"]
                successful = metrics["successful"]

                if total == 0:
                    success_rates[stage] = 0.0
                else:
                    success_rates[stage] = (successful / total) * 100.0

            return success_rates

        except Exception as e:
            self.logger.error(f"Failed to calculate stage success rates: {e}")
            return {}

    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent errors

        Args:
            count: Number of errors to return

        Returns:
            List of recent error records
        """
        try:
            return self.metrics["errors"][-count:] if self.metrics["errors"] else []
        except Exception as e:
            self.logger.error(f"Failed to get recent errors: {e}")
            return []

    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = self._init_metrics()
        self.save_metrics()
        self.logger.info("Metrics reset")
