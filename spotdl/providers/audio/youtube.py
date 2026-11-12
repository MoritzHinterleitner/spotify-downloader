"""
YouTube module for downloading and searching songs using yt-dlp.
"""

import re
from typing import Any, Dict, List, Optional

from yt_dlp import YoutubeDL

from spotdl.providers.audio.base import AudioProvider
from spotdl.types.result import Result

__all__ = ["YouTube"]

# Searching more results gives the matcher enough candidates to prefer popular
# official uploads instead of an obscure upload that happens to have a similar title.
SEARCH_RESULT_COUNT = 25


def _channel_to_artist(uploader: Optional[str]) -> Optional[str]:
    """
    Convert a YouTube channel name into an artist name.

    Removes common auto-generated channel suffixes so that an official channel
    can be matched against the Spotify artist.

    ### Arguments
    - uploader: The YouTube channel name.

    ### Returns
    - The artist name, or None if the channel name is empty.
    """

    if not uploader:
        return None

    artist = re.sub(r"\s*-\s*Topic\s*$", "", uploader, flags=re.IGNORECASE)
    artist = re.sub(r"\s*VEVO\s*$", "", artist, flags=re.IGNORECASE)
    artist = artist.strip()

    return artist or None


class YouTube(AudioProvider):
    """
    YouTube audio provider class using yt-dlp.
    """

    SUPPORTS_ISRC = False
    GET_RESULTS_OPTS: List[Dict[str, Any]] = [{}]

    # YouTube has no verified/"song" results, so rely more on popularity to
    # separate official uploads from random re-uploads with matching titles.
    RESULT_SCORE_RANGE = 15
    VIEW_SCORE_WEIGHT = 35

    def get_results(
        self, search_term: str, *_args, **_kwargs
    ) -> List[Result]:  # pylint: disable=W0221
        """
        Get results from YouTube

        ### Arguments
        - search_term: The search term to search for.

        ### Returns
        - A list of YouTube results, or an empty list if no results are found.
        """
        search_opts: Dict[str, Any] = {
            **self.audio_handler.params,
            "skip_download": True,
        }

        with YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(
                f"ytsearch{SEARCH_RESULT_COUNT}:{search_term}", download=False
            )

        if not info or "entries" not in info:
            return []

        results = []
        for entry in info["entries"]:
            if not entry:
                continue

            video_id = entry.get("id")
            if not video_id:
                continue

            uploader = entry.get("uploader") or ""
            channel_artist = _channel_to_artist(uploader)

            results.append(
                Result(
                    source=self.name,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    verified=False,
                    name=entry.get("title", ""),
                    duration=entry.get("duration") or 0,
                    author=uploader,
                    artists=(channel_artist,) if channel_artist else None,
                    search_query=search_term,
                    views=entry.get("view_count") or 0,
                    result_id=video_id,
                )
            )

        return results
