"""Bilibili video monitoring and new video detection"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, List

import yt_dlp

from src.utils.logger import get_logger
from src.utils.retry import NetworkError, with_retry


class BilibiliMonitor:
    """Monitor Bilibili user for new videos"""

    def __init__(
        self,
        uid: str,
        history_db: str = "data/video_history.db",
        cookies_file: str = None,
    ):
        """
        Initialize Bilibili monitor

        Args:
            uid: Bilibili user ID to monitor
            history_db: SQLite database path for storing video history
            cookies_file: Optional path to cookies file for authentication
        """
        self.uid = uid
        self.history_db = history_db
        self.cookies_file = cookies_file
        self.logger = get_logger()

        # Ensure data directory exists
        os.makedirs(os.path.dirname(history_db), exist_ok=True)

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for video history"""
        with sqlite3.connect(self.history_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_history (
                    bvid TEXT PRIMARY KEY,
                    title TEXT,
                    upload_time TEXT,
                    processed_time TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)
            conn.commit()

    @with_retry(max_attempts=3, exceptions=(NetworkError, Exception))
    def get_video_list(self, limit: int = 20) -> List[Dict[str, str]]:
        """
        Get list of videos from Bilibili user

        Args:
            limit: Maximum number of videos to fetch

        Returns:
            List of video dictionaries with bvid, title, upload_time
        """
        self.logger.info(f"Fetching video list for UID: {self.uid}")

        # First try using Bilibili API
        try:
            return self._get_video_list_via_api(limit)
        except Exception as e:
            self.logger.warning(f"API method failed: {e}, trying yt-dlp method")
            # Fallback to yt-dlp method
            return self._get_video_list_via_ytdlp(limit)

    def _get_cookies_dict(self) -> Dict[str, str]:
        """Parse Netscape cookie file into a dictionary for requests"""
        cookies = {}
        if not self.cookies_file or not os.path.exists(self.cookies_file):
            return cookies

        try:
            with open(self.cookies_file, "r") as f:
                for line in f:
                    if not line.startswith("#") and line.strip():
                        parts = line.strip().split("\t")
                        if len(parts) >= 7:
                            # domain, domain_specified, path, secure, expires, name, value
                            cookies[parts[5]] = parts[6]
        except Exception as e:
            self.logger.warning(f"Failed to parse cookies file: {e}")

        return cookies

    def _get_video_list_via_api(self, limit: int = 20) -> List[Dict[str, str]]:
        """Get video list using Bilibili API"""
        import requests

        # Bilibili API endpoint
        url = "https://api.bilibili.com/x/space/arc/search"
        params = {"mid": self.uid, "ps": limit, "pn": 1, "order": "pubdate"}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": f"https://space.bilibili.com/{self.uid}/video",
        }

        # Use cookies if available to avoid rate limiting
        cookies = self._get_cookies_dict()

        response = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get("code") != 0:
            raise Exception(f"API error: {data.get('message', 'Unknown error')}")

        videos = []
        for item in data.get("data", {}).get("list", {}).get("vlist", []):
            # Convert timestamp to YYYYMMDD format
            created_timestamp = item.get("created", 0)
            upload_date = datetime.fromtimestamp(created_timestamp).strftime("%Y%m%d")

            videos.append(
                {
                    "bvid": item.get("bvid", ""),
                    "title": item.get("title", ""),
                    "upload_time": upload_date,
                    "url": f"https://www.bilibili.com/video/{item.get('bvid', '')}",
                    "duration": item.get("length", ""),
                }
            )

        self.logger.info(f"Found {len(videos)} videos via API")
        return videos

    def _get_video_list_via_ytdlp(self, limit: int = 20) -> List[Dict[str, str]]:
        """Get video list using yt-dlp (fallback method)"""
        url = f"https://space.bilibili.com/{self.uid}/video"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,  # Only get metadata, no download
        }

        # Add cookies configuration if available
        if self.cookies_file and os.path.exists(self.cookies_file):
            ydl_opts["cookiefile"] = self.cookies_file
            self.logger.info(f"Using cookies file: {self.cookies_file}")
        else:
            # Try to use browser cookies as fallback
            ydl_opts["cookies_from_browser"] = "chrome"
            self.logger.info("Using Chrome browser cookies")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                videos = []
                for entry in info.get("entries", [])[:limit]:
                    videos.append(
                        {
                            "bvid": entry.get("id", ""),
                            "title": entry.get("title", ""),
                            "upload_time": entry.get("upload_date", ""),  # YYYYMMDD format
                            "url": entry.get("webpage_url", ""),
                            "duration": entry.get("duration", 0),
                        }
                    )

                self.logger.info(f"Found {len(videos)} videos via yt-dlp")
                return videos

        except Exception as e:
            self.logger.error(f"Failed to fetch video list: {e}")
            raise NetworkError(f"Bilibili API error: {e}")

    def get_new_videos(self, limit: int = 20) -> List[Dict[str, str]]:
        """
        Get new videos that haven't been processed

        Args:
            limit: Maximum number of videos to check

        Returns:
            List of new video dictionaries
        """
        self.logger.info("Checking for new videos...")

        # Get all videos
        all_videos = self.get_video_list(limit)

        # Get processed videos
        with sqlite3.connect(self.history_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT bvid FROM video_history WHERE status = 'processed'")
            processed_bvids = {row[0] for row in cursor.fetchall()}

        # Filter new videos
        new_videos = [video for video in all_videos if video["bvid"] not in processed_bvids]

        self.logger.info(f"Found {len(new_videos)} new videos")
        return new_videos

    def mark_video_processed(self, bvid: str, title: str = "", upload_time: str = ""):
        """
        Mark a video as processed

        Args:
            bvid: Video BVID
            title: Video title
            upload_time: Video upload time
        """
        with sqlite3.connect(self.history_db) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO video_history
                (bvid, title, upload_time, processed_time, status)
                VALUES (?, ?, ?, ?, 'processed')
            """,
                (bvid, title, upload_time, datetime.now().isoformat()),
            )
            conn.commit()

        self.logger.info(f"Marked video as processed: {bvid}")

    def get_video_url(self, bvid: str) -> str:
        """
        Get video URL from BVID

        Args:
            bvid: Video BVID

        Returns:
            Video URL
        """
        return f"https://www.bilibili.com/video/{bvid}"

    def get_processed_count(self) -> int:
        """
        Get count of processed videos

        Returns:
            Number of processed videos
        """
        with sqlite3.connect(self.history_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM video_history WHERE status = 'processed'")
            return cursor.fetchone()[0]


if __name__ == "__main__":
    # Example usage
    monitor = BilibiliMonitor("322005137")
    videos = monitor.get_video_list()
    print(f"Found {len(videos)} videos")
    for video in videos[:5]:
        print(f"{video['bvid']}: {video['title']}")
