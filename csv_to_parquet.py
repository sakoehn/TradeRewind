from __future__ import annotations
from pathlib import Path
import argparse
import pandas as pd


def convert_csv_file(csv_path: Path, out_dir: Path) -> Path:
    """Convert a single CSV file to Parquet in out_dir, return Parquet path."""
    df = pd.read_csv(csv_path)  # customize kwargs as needed [web:28]
    parquet_path = out_dir / (csv_path.stem + ".parquet")
    df.to_parquet(parquet_path, index=False)  # requires pyarrow or fastparquet [web:16]
    return parquet_path


def convert_folder(in_dir: Path, out_dir: Path, pattern: str = "*.csv") -> None:
    """Convert all CSV files in in_dir matching pattern into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for csv_path in sorted(in_dir.glob(pattern)):
        if csv_path.is_file():
            parquet_path = convert_csv_file(csv_path, out_dir)
            print(f"Wrote {parquet_path}")


def parse_args() -> argparse.Namespace:
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
    args = parse_args()
    convert_folder(args.input_dir, args.output_dir, args.pattern)


if __name__ == "__main__":
    main()
