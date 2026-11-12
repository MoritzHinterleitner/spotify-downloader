import time

import pytest

from spotdl.types.playlist import Playlist
from spotdl.types.saved import SavedError
from spotdl.types.song import Song, SongListError
from spotdl.utils.search import get_search_results, get_simple_songs, parse_query

SONG = ["https://open.spotify.com/track/2Ikdgh3J5vCRmnCL3Xcrtv"]
PLAYLIST = ["https://open.spotify.com/playlist/78Lg6HmUqlTnmipvNxc536"]
ALBUM = ["https://open.spotify.com/album/4MQnUDGXmHOvnsWCpzeqWT"]
YT = [
    "https://www.youtube.com/watch?v=BZKwsPIhVO8|https://open.spotify.com/track/4B2kkxg3wKSTZw5JPaUtzQ"
]
ARTIST = ["https://open.spotify.com/artist/1FPC2zwfMHhrP3frOfaai6"]
ALBUM_SEARCH = ["album: yeezus"]

QUERY = SONG + PLAYLIST + ALBUM + YT + ARTIST

SAVED = ["saved"]


@pytest.mark.vcr()
def test_parse_song():
    songs = parse_query(SONG)

    song = songs[0]
    assert len(songs) == 1
    assert song.download_url == None


@pytest.mark.vcr()
def test_parse_album():
    songs = parse_query(ALBUM)

    assert len(songs) > 1
    assert songs[0].url == "https://open.spotify.com/track/2Ikdgh3J5vCRmnCL3Xcrtv"


@pytest.mark.vcr()
def test_parse_yt_link():
    songs = parse_query(YT)

    assert len(songs) == 1
    assert songs[0].url == "https://open.spotify.com/track/4B2kkxg3wKSTZw5JPaUtzQ"
    assert songs[0].download_url == "https://www.youtube.com/watch?v=BZKwsPIhVO8"


@pytest.mark.vcr()
def test_parse_artist():
    songs = parse_query(ARTIST)

    assert len(songs) > 1


@pytest.mark.xfail(
    raises=SongListError,
    strict=True,
    reason="SpotipyFree's search() ignores type= and only returns tracks",
)
@pytest.mark.vcr()
def test_parse_album_search():
    songs = parse_query(ALBUM_SEARCH)

    assert len(songs) > 0


@pytest.mark.vcr()
def test_parse_saved():
    with pytest.raises(SavedError):
        parse_query(SAVED)


@pytest.mark.vcr()
def test_parse_query():
    songs = parse_query(QUERY)

    assert len(songs) > 1


@pytest.mark.vcr()
def test_get_search_results():
    results = get_search_results("test")
    assert len(results) > 1


def test_create_empty_song():
    song = Song.from_missing_data(name="test")
    assert song.name == "test"
    assert song.url == None
    assert song.download_url == None
    assert song.duration == None
    assert song.artists == None


@pytest.mark.vcr()
def test_get_simple_songs():
    songs = get_simple_songs(QUERY)
    assert len(songs) > 1


def test_get_simple_songs_skips_missing_video_details(monkeypatch):
    class FakeYTMClient:
        def get_song(self, video_id):
            return {"playabilityStatus": {"status": "ERROR"}}

    monkeypatch.setattr("spotdl.utils.search.get_ytm_client", lambda: FakeYTMClient())

    songs = get_simple_songs(["https://music.youtube.com/watch?v=dQw4w9WgXcQ"])

    assert songs == []


def test_parse_query_preserves_song_order(monkeypatch):
    songs = [
        Song.from_missing_data(
            name=f"Song {index}",
            artists=["Artist"],
            artist="Artist",
            song_id=str(index),
            url=f"https://open.spotify.com/track/{index}",
        )
        for index in range(10)
    ]

    monkeypatch.setattr(
        "spotdl.utils.search.get_simple_songs",
        lambda *_args, **_kwargs: songs,
    )

    def fake_reinit_song(song):
        # Make later songs finish before earlier ones
        time.sleep(0.01 * (10 - int(song.name.split()[-1])))
        return song

    monkeypatch.setattr("spotdl.utils.search.reinit_song", fake_reinit_song)

    result = parse_query(["ignored"], threads=4)

    assert [song.name for song in result] == [song.name for song in songs]


def test_parse_query_reuses_existing_song_metadata(monkeypatch):
    old_url = "https://open.spotify.com/track/old"
    new_url = "https://open.spotify.com/track/new"
    existing = Song.from_missing_data(
        name="Old Song",
        artists=["Artist"],
        artist="Artist",
        genres=["metal"],
        disc_count=2,
        disc_number=1,
        song_id="old",
        url=old_url,
    )
    current_songs = [
        Song.from_missing_data(
            name="Old Song",
            artists=["Artist"],
            artist="Artist",
            song_id="old",
            url=old_url,
            list_name="Playlist",
            list_position=1,
            list_length=2,
        ),
        Song.from_missing_data(
            name="New Song",
            artists=["Artist"],
            artist="Artist",
            song_id="new",
            url=new_url,
            list_name="Playlist",
            list_position=2,
            list_length=2,
        ),
    ]

    monkeypatch.setattr(
        "spotdl.utils.search.get_simple_songs",
        lambda *_args, **_kwargs: current_songs,
    )

    reinitialized = []

    def fake_reinit_song(song):
        reinitialized.append(song.url)
        return song

    monkeypatch.setattr("spotdl.utils.search.reinit_song", fake_reinit_song)

    result = parse_query(["ignored"], existing_songs={old_url: existing})

    assert reinitialized == [new_url]
    assert [song.url for song in result] == [old_url, new_url]
    assert result[0].genres == ["metal"]
    assert result[0].disc_count == 2
    assert result[0].list_name == "Playlist"
    assert result[0].list_position == 1


def test_custom_mapping_does_not_duplicate_playlist_songs(monkeypatch):
    track_url = "https://open.spotify.com/track/4B2kkxg3wKSTZw5JPaUtzQ"
    mapped_url = "https://www.youtube.com/watch?v=BZKwsPIhVO8"
    playlist_song = Song.from_missing_data(
        name="Test song",
        artists=["Test artist"],
        artist="Test artist",
        song_id="4B2kkxg3wKSTZw5JPaUtzQ",
        url=track_url,
    )
    playlist = Playlist(
        name="Test playlist",
        url=PLAYLIST[0],
        urls=[track_url],
        songs=[playlist_song],
        description="",
        author_url="",
        author_name="",
        cover_url="",
    )

    monkeypatch.setattr(
        "spotdl.utils.search.Playlist.from_url",
        lambda *_args, **_kwargs: playlist,
    )

    songs = get_simple_songs(
        [PLAYLIST[0], f"{mapped_url}|{track_url}?si=b5c0790edc8f4904"]
    )

    assert len(songs) == 1
    assert songs[0].url == track_url
    assert songs[0].list_name == playlist.name
    assert songs[0].download_url == mapped_url
