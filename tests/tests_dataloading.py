"""Tests for the data_loading module without pytest.

Coverage targets
----------------
* data_loading.py
    - load_all_data: loading multiple Parquet files, handling no files, and raising errors.

Run with::

    python tests_dataloading.py
"""

import os
import pandas as pd
import glob
from data_loading import load_all_data

def setup_parquet_files(tmp_path):
    """Helper to create temporary Parquet files for testing."""
    data1 = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    data2 = pd.DataFrame({"col1": [5, 6], "col2": [7, 8]})

    file1 = os.path.join(tmp_path, "file1.parquet")
    file2 = os.path.join(tmp_path, "file2.parquet")

    data1.to_parquet(file1)
    data2.to_parquet(file2)

    return tmp_path

def test_load_all_data_success():
    """Test that all Parquet files are loaded and concatenated successfully."""
    tmp_path = "./temp_test_data"
    os.makedirs(tmp_path, exist_ok=True)
    setup_parquet_files(tmp_path)

    os.path.join = lambda *args: tmp_path
    glob.glob = lambda path: [os.path.join(tmp_path, "file1.parquet"), os.path.join(tmp_path, "file2.parquet")]

    combined_df = load_all_data()

    assert len(combined_df) == 4, "DataFrame length mismatch."
    assert list(combined_df.columns) == ["col1", "col2"], "Column names mismatch."

    print("test_load_all_data_success passed.")

def test_load_all_data_no_files():
    """Test that ValueError is raised when no Parquet files are found."""
    glob.glob = lambda path: []

    try:
        load_all_data()
    except ValueError as e:
        assert str(e) == "No Parquet files found.", "Error message mismatch."
        print("test_load_all_data_no_files passed.")
        return

    assert False, "ValueError was not raised."

def test_load_all_data_file_content():
    """Test that the combined DataFrame has the expected content."""
    tmp_path = "./temp_test_data"
    os.makedirs(tmp_path, exist_ok=True)
    setup_parquet_files(tmp_path)

    os.path.join = lambda *args: tmp_path
    glob.glob = lambda path: [os.path.join(tmp_path, "file1.parquet"), os.path.join(tmp_path, "file2.parquet")]

    combined_df = load_all_data()

    expected_data = pd.DataFrame({"col1": [1, 2, 5, 6], "col2": [3, 4, 7, 8]})
    pd.testing.assert_frame_equal(combined_df.reset_index(drop=True), expected_data)

    print("test_load_all_data_file_content passed.")

if __name__ == "__main__":
    test_load_all_data_success()
    test_load_all_data_no_files()
    test_load_all_data_file_content()