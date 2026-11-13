import argparse
import json
from pathlib import Path

from .generator import generate
from .loader import load
from .validate import validate
from .anomalies import detect_anomalies


def main():
    parser = argparse.ArgumentParser(prog="fulfillment")
    sub = parser.add_subparsers(dest="command", required=True)

    generate_parser = sub.add_parser("generate")
    generate_parser.add_argument(
        "--seed",
        type=int,
        default=20261022,
        help="Deterministic random seed.",
    )
    generate_parser.add_argument(
        "--scale",
        choices=("starter", "full"),
        default="starter",
        help="Dataset size.",
    )
    generate_parser.add_argument(
        "--out",
        default="data/output",
        help="Output directory.",
    )

    load_parser = sub.add_parser("load")
    load_parser.add_argument(
        "--root",
        default="data/output",
        help="Generated dataset directory.",
    )

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument(
        "--root",
        default="data/output",
        help="Dataset directory.",
    )

    verify_parser = sub.add_parser("verify-anomalies")
    verify_parser.add_argument(
        "--root",
        default="data/output",
        help="Dataset directory.",
    )

    detect_parser = sub.add_parser("detect-anomalies")
    detect_parser.add_argument(
        "--root",
        default="data/output",
        help="Dataset directory.",
    )

    args = parser.parse_args()

    if args.command == "load":
        result = load(Path(args.root))
        print(json.dumps(result, indent=2, default=str))
        return

    if args.command == "generate":
        result = generate(
            Path(args.out),
            seed=args.seed,
            scale=args.scale,
        )
        print(json.dumps(result, indent=2))

    elif args.command == "validate":
        result = validate(Path(args.root))
        print(json.dumps(result, indent=2))

    elif args.command == "verify-anomalies":
        result = validate(Path(args.root))

        expected = {
            ("PROMISE_BEFORE_ORDER_TIME", "1"),
            ("ALLOCATION_EXCEEDS_STOCK", "ANOM-ALLOC-0001"),
            ("UNSUPPORTED_CARRIER_SERVICE_ZONE", "SHP-2026-000001"),
            ("SHIPMENT_DELIVERED_BEFORE_DISPATCH", "TRK-SHP-2026-000001-002"),
            ("SPLIT_SHIPMENT_STATUS_ROLLUP_ERROR", "ORD-2026-000001"),
        }

        found = {(issue_type, entity_id) for issue_type, entity_id in result}
        issues = sorted(found ^ expected)

        print(
            json.dumps(
                {
                    "status": "PASS" if not issues else "FAIL",
                    "count": len(found),
                    "issues": issues,
                },
                indent=2,
            )
        )

    elif args.command == "detect-anomalies":
        result = detect_anomalies(Path(args.root))
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
