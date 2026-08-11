"""CLI entry point for running change detection analysis."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.analysis_service import AnalysisService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GeoAI urban change detection")
    parser.add_argument("--t1", type=Path, required=True, help="GeoTIFF time 1")
    parser.add_argument("--t2", type=Path, required=True, help="GeoTIFF time 2")
    parser.add_argument("--method", choices=["baseline", "cva"], default="baseline")
    args = parser.parse_args()

    service = AnalysisService()
    result = service.run_analysis(args.t1, args.t2, method=args.method)
    print(json.dumps(result.statistics, indent=2))


if __name__ == "__main__":
    main()
