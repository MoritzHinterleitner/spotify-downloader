from spotdl.providers.audio.youtube import YouTube
from spotdl.types.result import Result
from spotdl.types.song import Song


def test_yt_search(mocker):
    mocker.patch(
        "spotdl.providers.audio.youtube.YoutubeDL.extract_info",
        return_value={
            "entries": [
                {
                    "id": "test_video_id",
                    "title": "Abstrakt - Nobody Else",
                    "duration": 162,
                    "uploader": "Abstrakt",
                    "view_count": 123456,
                }
            ]
        },
    )

    provider = YouTube()

    assert (
        provider.search(
            Song.from_dict(
                {
                    "name": "Nobody Else",
                    "artists": ["Abstrakt"],
                    "artist": "Abstrakt",
                    "album_id": "0kx3ml8bdAYrQtcIwvkhp8",
                    "album_name": "Nobody Else",
                    "album_artist": "Abstrakt",
                    "album_type": "single",
                    "genres": [],
                    "disc_number": 1,
                    "disc_count": 1,
                    "duration": 162.406,
                    "year": 2022,
                    "date": "2022-03-17",
                    "track_number": 1,
                    "tracks_count": 1,
                    "isrc": "GB2LD2210007",
                    "song_id": "0kx3ml8bdAYrQtcIwvkhp8",
                    "cover_url": "https://i.scdn.co/image/ab67616d0000b27345f5ba253b9825efc88bc236",
                    "explicit": False,
                    "publisher": "NCS",
                    "url": "https://open.spotify.com/track/0kx3ml8bdAYrQtcIwvkhp8",
                    "copyright_text": "2022 NCS",
                    "download_url": None,
                }
            )
        )
        is not None
    )


def test_yt_get_results(mocker):
    mocker.patch(
        "spotdl.providers.audio.youtube.YoutubeDL.extract_info",
        return_value={
            "entries": [
                {
                    "id": f"video_{index}",
                    "title": f"Lost Identities Moments {index}",
                    "duration": 180 + index,
                    "uploader": "Lost Identities",
                    "view_count": 1000 + index,
                }
                for index in range(6)
            ]
        },
    )

    provider = YouTube()

    results = provider.get_results("Lost Identities Moments")

    assert results and len(results) > 5
    assert results[0].url == "https://www.youtube.com/watch?v=video_0"
    assert results[0].duration == 180
    assert results[0].author == "Lost Identities"
    assert results[0].artists == ("Lost Identities",)


def test_yt_get_results_normalizes_null_metadata(mocker):
    mocker.patch(
        "spotdl.providers.audio.youtube.YoutubeDL.extract_info",
        return_value={
            "entries": [
                {
                    "id": "video_0",
                    "title": "Live Stream",
                    "duration": None,
                    "uploader": None,
                    "view_count": None,
                }
            ]
        },
    )

    provider = YouTube()

    results = provider.get_results("live stream")

    assert len(results) == 1
    assert results[0].duration == 0
    assert results[0].author == ""
    assert results[0].views == 0
    assert results[0].artists is None


def test_yt_get_results_cleans_channel_names(mocker):
    mocker.patch(
        "spotdl.providers.audio.youtube.YoutubeDL.extract_info",
        return_value={
            "entries": [
                {
                    "id": "video_0",
                    "title": "Test Song",
                    "duration": 100,
                    "uploader": "Test Artist - Topic",
                    "view_count": 1000,
                },
                {
                    "id": "video_1",
                    "title": "Another Song",
                    "duration": 100,
                    "uploader": "Another ArtistVEVO",
                    "view_count": 1000,
                },
            ]
        },
    )

    provider = YouTube()
    results = provider.get_results("Test Song")

    assert results[0].artists == ("Test Artist",)
    assert results[1].artists == ("Another Artist",)


def test_yt_search_excludes_failed_urls(mocker):
    provider = YouTube()
    results = [
        Result(
            source="YouTube",
            url="https://www.youtube.com/watch?v=first",
            verified=False,
            name="Abstrakt - Nobody Else",
            duration=162,
            author="Abstrakt",
            artists=("Abstrakt",),
            views=1000,
            result_id="first",
        ),
        Result(
            source="YouTube",
            url="https://www.youtube.com/watch?v=second",
            verified=False,
            name="Abstrakt - Nobody Else",
            duration=162,
            author="Abstrakt",
            artists=("Abstrakt",),
            views=1000,
            result_id="second",
        ),
    ]
    mocker.patch.object(provider, "get_results", return_value=results)

    song = Song.from_missing_data(
        name="Nobody Else",
        artists=["Abstrakt"],
        artist="Abstrakt",
        album_name="Nobody Else",
        album_artist="Abstrakt",
        duration=162,
        explicit=False,
    )

    first_url = provider.search(song)
    assert first_url == results[0].url

    second_url = provider.search(song, exclude_urls={first_url})
    assert second_url == results[1].url


def test_yt_get_best_result_prefers_popular_upload(mocker):
    mocker.patch("spotdl.providers.audio.youtube.YoutubeDL.extract_info")
    provider = YouTube()

    obscure = Result(
        source="YouTube",
        url="https://www.youtube.com/watch?v=obscure",
        verified=False,
        name="Abstrakt - Nobody Else",
        duration=162,
        author="Random Uploads",
        artists=("Random Uploads",),
        views=500,
        result_id="obscure",
    )
    official = Result(
        source="YouTube",
        url="https://www.youtube.com/watch?v=official",
        verified=False,
        name="Abstrakt - Nobody Else",
        duration=162,
        author="Abstrakt",
        artists=("Abstrakt",),
        views=10_000_000,
        result_id="official",
    )

    best_result, _ = provider.get_best_result({obscure: 100.0, official: 90.0})

    assert best_result == official


def test_yt_get_best_result_keeps_higher_match_when_views_are_equal(mocker):
    mocker.patch("spotdl.providers.audio.youtube.YoutubeDL.extract_info")
    provider = YouTube()

    better_match = Result(
        source="YouTube",
        url="https://www.youtube.com/watch?v=better",
        verified=False,
        name="Abstrakt - Nobody Else",
        duration=162,
        author="Abstrakt",
        artists=("Abstrakt",),
        views=1000,
        result_id="better",
    )
    worse_match = Result(
        source="YouTube",
        url="https://www.youtube.com/watch?v=worse",
        verified=False,
        name="Abstrakt - Nobody Else (Live)",
        duration=162,
        author="Abstrakt",
        artists=("Abstrakt",),
        views=1000,
        result_id="worse",
    )

    best_result, _ = provider.get_best_result({better_match: 95.0, worse_match: 85.0})

    assert best_result == better_match
