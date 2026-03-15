"""Convert CSV files to Parquet format for use with TradeRewind.

Usage::

    python csv_to_parquet.py <input_dir> <output_dir> [--pattern "*.csv"]
"""

from pathlib import Path
import argparse
import pandas as pd


def convert_csv_file(csv_path: Path, out_dir: Path) -> Path:
    """Convert a single CSV file to Parquet in out_dir.

    Args:
        csv_path: Path to the source CSV file.
        out_dir: Directory where the Parquet file will be written.

    Returns:
        Path to the newly created Parquet file.
    """
    frame = pd.read_csv(csv_path)
    parquet_path = out_dir / (csv_path.stem + ".parquet")
    frame.to_parquet(parquet_path, index=False)
    return parquet_path


def convert_folder(
    in_dir: Path,
    out_dir: Path,
    pattern: str = "*.csv",
) -> None:
    """Convert all CSV files in in_dir matching pattern into out_dir.

    Args:
        in_dir: Directory containing source CSV files.
        out_dir: Directory to write Parquet files (created if missing).
        pattern: Glob pattern for selecting files (default: ``"*.csv"``).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for csv_path in sorted(in_dir.glob(pattern)):
        if csv_path.is_file():
            parquet_path = convert_csv_file(csv_path, out_dir)
            print(f"Wrote {parquet_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the CSV-to-Parquet converter."""
    parser = argparse.ArgumentParser(
        description="Convert a folder of CSV files to Parquet files."
    )
    parser.add_argument("input_dir", type=Path, help="Folder containing CSV files")
    parser.add_argument("output_dir", type=Path, help="Folder to write Parquet files")
    parser.add_argument(
        "--pattern",
        type=str,
        default="*.csv",
        help="Glob pattern for CSVs (default: *.csv)",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point: parse args and run the folder conversion."""
    args = parse_args()
    convert_folder(args.input_dir, args.output_dir, args.pattern)


if __name__ == "__main__":
    main()
