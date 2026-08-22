from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


def main() -> int:
    parser = argparse.ArgumentParser(description='Run one bounded text smoke per configured Groq model')
    parser.add_argument('--config', type=Path, default=Path('config/models.json'))
    parser.add_argument('--base-url', default=os.getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1'))
    parser.add_argument('--timeout', type=int, default=60)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    api_key = os.getenv('GROQ_API_KEY', '').strip()
    if not api_key:
        print('GROQ_API_KEY is required', file=sys.stderr)
        return 2
    data = json.loads(args.config.read_text(encoding='utf-8'))
    models: list[str] = []
    for collection in (data.get('model_chains', {}), data.get('output_routes', {})):
        for specs in collection.values():
            for spec in specs:
                if spec.get('provider') == 'groq' and spec.get('enabled') and spec.get('model') not in models:
                    models.append(spec['model'])
    results = []
    endpoint = f"{args.base_url.rstrip('/')}/chat/completions"
    for model in models:
        started = time.perf_counter()
        item = {'model': model, 'endpoint': endpoint, 'status': 'failed'}
        try:
            response = requests.post(
                endpoint,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': 'Return exactly GROQ_SMOKE_OK'}],
                    'max_completion_tokens': 1024,
                    'temperature': 0,
                    'stream': False,
                },
                timeout=max(5, args.timeout),
            )
            item['http_status'] = response.status_code
            item['latency_ms'] = round((time.perf_counter() - started) * 1000, 1)
            try:
                body = response.json()
            except ValueError:
                body = {}
            if response.status_code < 400:
                choices = body.get('choices') if isinstance(body, dict) else None
                content = choices[0].get('message', {}).get('content') if isinstance(choices, list) and choices else ''
                item['status'] = 'passed' if str(content).strip() else 'invalid_empty_response'
                item['response_shape'] = {'choices': len(choices) if isinstance(choices, list) else 0, 'content_nonempty': bool(str(content).strip()), 'usage_present': bool(isinstance(body, dict) and body.get('usage'))}
            else:
                item['status'] = 'quota' if response.status_code == 429 else 'auth' if response.status_code in {401, 403} else 'failed'
                item['error_preview'] = str(body)[:300]
        except requests.RequestException as exc:
            item['latency_ms'] = round((time.perf_counter() - started) * 1000, 1)
            item['error_type'] = type(exc).__name__
            item['error_preview'] = str(exc)[:300]
        results.append(item)
        print(json.dumps(item, ensure_ascii=False))
    report = {'provider': 'groq', 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(), 'base_url': args.base_url.rstrip('/'), 'count': len(results), 'results': results}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if all(item['status'] == 'passed' for item in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
