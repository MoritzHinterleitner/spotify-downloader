import json

from spotdl.console.sync import (
    _get_songs_from_sync_data,
    _load_songs_from_sync_file,
)
from spotdl.types.song import Song


def _song() -> Song:
    return Song.from_missing_data(
        name="Test Song",
        artists=["Test Artist"],
        artist="Test Artist",
        url="https://open.spotify.com/track/test",
    )


def test_get_songs_from_sync_data():
    song = _song()

    songs = _get_songs_from_sync_data(
        {"type": "sync", "query": ["query"], "songs": [song.json]}
    )

    assert songs == {song.url: song}


def test_get_songs_from_sync_data_ignores_invalid_data():
    assert _get_songs_from_sync_data(None) == {}
    assert _get_songs_from_sync_data({"songs": []}) == {}
    assert _get_songs_from_sync_data({"type": "sync", "songs": "invalid"}) == {}


def test_load_songs_from_sync_file(tmp_path):
    song = _song()
    sync_file = tmp_path / "test.spotdl"
    sync_file.write_text(
        json.dumps({"type": "sync", "query": ["query"], "songs": [song.json]}),
        encoding="utf-8",
    )

    songs = _load_songs_from_sync_file(str(sync_file))

    assert songs == {song.url: song}


def test_load_songs_from_sync_file_returns_empty_for_missing_or_invalid_file(tmp_path):
    assert _load_songs_from_sync_file(str(tmp_path / "missing.spotdl")) == {}

    invalid_file = tmp_path / "invalid.spotdl"
    invalid_file.write_text("not json", encoding="utf-8")

    assert _load_songs_from_sync_file(str(invalid_file)) == {}
