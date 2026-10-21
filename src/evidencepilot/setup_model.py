"""Interactive local model configuration. API keys never echo to the terminal."""
import argparse
import getpass
import json
from pathlib import Path
from urllib.parse import urlsplit

from .providers import OpenAICompatibleProvider, ProviderError


def valid_endpoint(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError('Use an HTTPS API base URL without credentials, query or fragment.')
    if parsed.path.rstrip('/').endswith('/chat/completions'):
        raise ValueError('Enter the base URL, not the full /chat/completions endpoint.')
    return value.rstrip('/')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Send one small request using existing configuration')
    args = parser.parse_args()
    if not args.check:
        path = Path(__file__).resolve().parents[2] / '.env.local'
        if path.exists():
            print('Local configuration already exists. Edit it locally or use --check; it was not overwritten.')
            return
        print('Enter details from your model service. The API key is hidden while typing.')
        try:
            endpoint = valid_endpoint(input('API base URL: ').strip())
            model = input('Model ID: ').strip()
            key = getpass.getpass('API key (hidden): ').strip()
            if not model or not key or any('\n' in v or '\r' in v for v in (model, key)):
                raise ValueError('Model ID and API key must be non-empty single-line values.')
            with path.open('x', encoding='utf-8') as handle:
                handle.write(f'EVIDENCEPILOT_BASE_URL={endpoint}\nEVIDENCEPILOT_MODEL={model}\nEVIDENCEPILOT_API_KEY={key}\n')
        except (ValueError, EOFError, KeyboardInterrupt) as exc:
            print(str(exc) or 'Configuration cancelled.')
            return
        print('Saved .env.local (excluded by .gitignore). No request was sent.')
        print('Next: run this module with --check to send one small API request.')
        return
    provider = OpenAICompatibleProvider.from_environment()
    if provider is None:
        parser.error('No complete configuration found. Run setup first.')
    try:
        provider.timeout_seconds = 120
        print('Checking API connection (one small request; up to 120s)...', flush=True)
        response = provider.complete_json('Return only this JSON object: {"status":"ok"}.', 'Connection check.', max_tokens=128)
        if response.get('status') != 'ok':
            raise ProviderError('Endpoint responded, but the structured-output check did not pass.')
    except ProviderError as exc:
        print(f'Connection check failed: {exc}')
        raise SystemExit(1)
    print(json.dumps({'connection': 'ok', 'model': provider.model, 'requests': 1}))


if __name__ == '__main__':
    main()
