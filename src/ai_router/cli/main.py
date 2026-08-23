import argparse
import json
import os
from pathlib import Path

from ..openai_server import run_server
from ..router import AIRouter

_OUTPUT_TYPES = ["auto", "text", "image", "audio", "embedding", "video_analysis", "video_generation", "live"]
_GROUNDING_TYPES = ["search", "maps"]


def _add_provider_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--providers",
        help="Comma-separated provider IDs or aliases to allow, e.g. gemini,huggingface,openrouter,nvidia",
    )
    parser.add_argument(
        "--exclude-providers",
        help="Comma-separated provider IDs or aliases to exclude, e.g. gemini",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Config-driven multi-provider AI router")
    parser.add_argument("--config-dir", default=os.getenv("AI_ROUTER_CONFIG_DIR", "config"))
    parser.add_argument("--state-db", default=os.getenv("AI_ROUTER_STATE_DB", "data/ai_router.db"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("summary")

    call = sub.add_parser("call-json")
    call.add_argument("--chain", default="default")
    call.add_argument("--operation", default="cli_call")
    call.add_argument("--provider")
    call.add_argument("--model")
    call.add_argument("--system", required=True)
    call.add_argument("--user", required=True)
    _add_provider_filters(call)

    route = sub.add_parser("route-plan")
    route.add_argument("--output-type", choices=_OUTPUT_TYPES, default="auto")
    route.add_argument("--grounding", choices=_GROUNDING_TYPES)
    route.add_argument("--user", required=True)
    route.add_argument("--provider")
    route.add_argument("--model")
    _add_provider_filters(route)

    auto = sub.add_parser("call-auto")
    auto.add_argument("--output-type", choices=_OUTPUT_TYPES, default="auto")
    auto.add_argument("--grounding", choices=_GROUNDING_TYPES)
    auto.add_argument("--operation", default="cli_auto_call")
    auto.add_argument("--provider")
    auto.add_argument("--model")
    auto.add_argument("--system", default="")
    auto.add_argument("--user", required=True)
    auto.add_argument("--image-data")
    auto.add_argument("--image-mime-type", default="image/png")
    auto.add_argument("--video-uri")
    auto.add_argument("--voice", default="Kore")
    auto.add_argument("--output-dimensionality", type=int)
    auto.add_argument("--latitude", type=float)
    auto.add_argument("--longitude", type=float)
    _add_provider_filters(auto)

    serve = sub.add_parser("serve", help="Run the local OpenAI-compatible chat server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8787)
    serve.add_argument("--local-api-key", default="")
    serve.add_argument("--provider")
    serve.add_argument("--model")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "serve":
        run_server(
            config_dir=args.config_dir,
            state_db=args.state_db,
            host=args.host,
            port=args.port,
            local_api_key=args.local_api_key,
            provider=args.provider,
            model=args.model,
        )
        return 0
    router = AIRouter(config_dir=Path(args.config_dir), state_db=Path(args.state_db))
    try:
        if args.command == "summary":
            print(json.dumps(router.summary(), ensure_ascii=False, indent=2))
            return 0
        if args.command == "route-plan":
            result = router.route_plan(
                user_prompt=args.user,
                output_type=args.output_type,
                grounding=args.grounding,
                provider=args.provider,
                model=args.model,
                providers=args.providers,
                exclude_providers=args.exclude_providers,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "call-auto":
            result = router.complete_auto(
                user_prompt=args.user,
                system_prompt=args.system,
                output_type=args.output_type,
                grounding=args.grounding,
                operation=args.operation,
                provider=args.provider,
                model=args.model,
                image_data=args.image_data,
                image_mime_type=args.image_mime_type,
                video_uri=args.video_uri,
                voice=args.voice,
                output_dimensionality=args.output_dimensionality,
                latitude=args.latitude,
                longitude=args.longitude,
                providers=args.providers,
                exclude_providers=args.exclude_providers,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        result = router.complete_json(
            chain=args.chain,
            operation=args.operation,
            provider=args.provider,
            model=args.model,
            system_prompt=args.system,
            user_prompt=args.user,
            providers=args.providers,
            exclude_providers=args.exclude_providers,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    finally:
        router.close()


if __name__ == "__main__":
    raise SystemExit(main())
