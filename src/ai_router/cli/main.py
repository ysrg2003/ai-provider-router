from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..router import AIRouter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Config-driven multi-provider AI router")
    parser.add_argument("--config-dir", default="config")
    parser.add_argument("--state-db", default="data/ai_router.db")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")
    call = sub.add_parser("call-json")
    call.add_argument("--chain", default="default")
    call.add_argument("--operation", default="cli_call")
    call.add_argument("--system", required=True)
    call.add_argument("--user", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    router = AIRouter(config_dir=Path(args.config_dir), state_db=Path(args.state_db))
    try:
        if args.command == "summary":
            print(json.dumps(router.summary(), ensure_ascii=False, indent=2))
            return 0
        result = router.complete_json(
            chain=args.chain,
            operation=args.operation,
            system_prompt=args.system,
            user_prompt=args.user,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        router.close()


if __name__ == "__main__":
    raise SystemExit(main())
