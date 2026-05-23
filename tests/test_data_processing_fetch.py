"""Tests for the UCI auto-download fallback in build_database()."""
from pathlib import Path
from unittest.mock import patch

import pytest

from src import data_processing


def test_uci_url_is_set():
    assert data_processing.UCI_URL.startswith("https://")
    assert "online" in data_processing.UCI_URL.lower() or "502" in data_processing.UCI_URL


def test_fetch_uci_dataset_skips_when_excel_exists(tmp_path):
    """If the target Excel already exists, fetch is a no-op."""
    target = tmp_path / "online_retail_II.xlsx"
    target.write_bytes(b"existing")

    with patch.object(data_processing, "urlopen") as mock_urlopen:
        data_processing.fetch_uci_dataset(excel_path=target)

    mock_urlopen.assert_not_called()
    assert target.read_bytes() == b"existing"


def test_fetch_uci_dataset_downloads_when_missing(tmp_path, monkeypatch):
    """If the Excel is missing, fetch downloads the zip and extracts the xlsx."""
    import io
    import zipfile

    target = tmp_path / "online_retail_II.xlsx"
    assert not target.exists()

    # Build a fake zip containing one xlsx-named entry
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("online_retail_II.xlsx", b"fake-xlsx-bytes")
    buf.seek(0)

    class _FakeResponse:
        def __init__(self, data: bytes):
            self._data = data
        def read(self) -> bytes:
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *_):
            return False

    monkeypatch.setattr(
        data_processing, "urlopen",
        lambda _url, timeout=60: _FakeResponse(buf.getvalue()),
    )

    data_processing.fetch_uci_dataset(excel_path=target)
    assert target.exists()
    assert target.read_bytes() == b"fake-xlsx-bytes"
