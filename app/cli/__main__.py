from __future__ import annotations

import argparse

from app.adapters.format_adapter import convert_dataset, read_dataset
from app.gateways import DataQualityGateway


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gateway")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("dataset")

    infer = subparsers.add_parser("infer-schema")
    infer.add_argument("dataset")

    profile = subparsers.add_parser("profile")
    profile.add_argument("dataset")

    validate = subparsers.add_parser("validate")
    validate.add_argument("dataset")

    retrieve = subparsers.add_parser("retrieve")
    retrieve.add_argument("events")
    retrieve.add_argument("features")

    detect = subparsers.add_parser("detect-leakage")
    detect.add_argument("events")
    detect.add_argument("features")

    convert = subparsers.add_parser("convert")
    convert.add_argument("dataset")
    convert.add_argument("--format", dest="file_format", default="parquet")

    benchmark = subparsers.add_parser("benchmark")
    benchmark.set_defaults(command="benchmark")

    acceptance = subparsers.add_parser("acceptance")
    acceptance.set_defaults(command="acceptance")

    reproduce = subparsers.add_parser("reproduce")
    reproduce.set_defaults(command="reproduce")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    gateway = DataQualityGateway()

    if args.command == "ingest":
        df = read_dataset(args.dataset)
        print({"rows": len(df), "columns": list(df.columns)})
    elif args.command == "infer-schema":
        print(gateway.infer_schema(args.dataset))
    elif args.command == "profile":
        print(gateway.profile(args.dataset))
    elif args.command == "validate":
        print(gateway.validate_dataset(args.dataset))
    elif args.command == "retrieve":
        print(gateway.retrieve(args.events, args.features))
    elif args.command == "detect-leakage":
        print(gateway.validate_leakage(args.events, args.features))
    elif args.command == "convert":
        output = args.dataset.replace(".csv", ".parquet") if args.file_format == "parquet" else args.dataset.replace(".parquet", ".csv")
        print(convert_dataset(args.dataset, output, args.file_format))
    elif args.command == "benchmark":
        print(gateway.benchmark())
    elif args.command == "acceptance":
        print(gateway.acceptance())
    elif args.command == "reproduce":
        print({"status": "reproduce-ready", "message": "Use scripts/reproduce_all.sh to replay the pipeline."})


if __name__ == "__main__":
    main()
