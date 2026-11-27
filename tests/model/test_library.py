"""Tests for the music library.

:copyright: Copyright (C) 2026 Alberto Pettarin
:license: GNU General Public License v3.0 (see the LICENSE file for details)
"""

import pytest

from mocassino.model.library import Library, LibraryEntry, list_directories


@pytest.fixture
def root(tmp_path):
    """Create a small music root directory."""
    root = tmp_path / "music"
    (root / "beta" / "Album").mkdir(parents=True)
    (root / "Alpha").mkdir()
    (root / ".hidden").mkdir()
    for name in ("b.mp3", "A.FLAC", "c.ogg", "d.wav", "cover.jpg", ".secret.mp3", "notes.txt"):
        (root / name).touch()
    (root / "beta" / "Album" / "01.flac").touch()
    return root


class TestLibrary:
    """Tests for the Library class"""

    def test_directory_path(self, root):
        assert Library(root).directory_path == root

    def test_directory_path_is_changed(self, root):
        library = Library(root)
        library.directory_path = root / "beta"
        assert library.directory_path == root / "beta"
        assert library.list_entries() == [
            LibraryEntry(is_directory=True, name="Album", path=root / "beta" / "Album"),
        ]

    def test_list_entries_of_empty_directory(self, root):
        assert Library(root).list_entries(root / "Alpha") == []

    def test_list_entries_of_missing_directory(self, root):
        assert Library(root).list_entries(root / "missing") == []

    def test_list_entries_of_root(self, root):
        assert Library(root).list_entries() == [
            LibraryEntry(is_directory=True, name="Alpha", path=root / "Alpha"),
            LibraryEntry(is_directory=True, name="beta", path=root / "beta"),
            LibraryEntry(is_directory=False, name="A.FLAC", path=root / "A.FLAC"),
            LibraryEntry(is_directory=False, name="b.mp3", path=root / "b.mp3"),
            LibraryEntry(is_directory=False, name="c.ogg", path=root / "c.ogg"),
            LibraryEntry(is_directory=False, name="d.wav", path=root / "d.wav"),
        ]

    def test_list_entries_of_subdirectory(self, root):
        album = root / "beta" / "Album"
        assert Library(root).list_entries(album) == [
            LibraryEntry(is_directory=False, name="01.flac", path=album / "01.flac"),
        ]

    def test_list_entries_outside_root(self, root):
        with pytest.raises(ValueError, match="is outside"):
            Library(root).list_entries(root.parent)


class TestListDirectories:
    """Tests for the list_directories function"""

    def test_directories_only_sorted_and_not_hidden(self, root):
        assert list_directories(root) == [root / "Alpha", root / "beta"]

    def test_directory_outside_the_library(self, root):
        assert list_directories(root.parent) == [root]

    def test_directory_without_subdirectories(self, root):
        assert list_directories(root / "beta" / "Album") == []

    def test_missing_directory(self, root, caplog):
        assert list_directories(root / "missing") == []
        assert "Cannot list" in caplog.text
