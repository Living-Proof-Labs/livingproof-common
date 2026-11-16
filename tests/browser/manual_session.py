# SPDX-License-Identifier: Apache-2.0
"""Manual browser session. GitHub metadata is served from a scoped fixture."""
import json
import re
from urllib.parse import urlsplit

REPO_PATH = '/repos/Living-Proof-Labs/livingproof-common'
RELEASE_PATH = REPO_PATH + '/releases/latest'
FIXTURE_TAG = 'v0.0.0-fixture'
FIXTURE_STARS = 7
GITHUB_API = re.compile(r'^https://api\.github\.com/')
# Local loopback is left to the manual server. Every other host matches.
OTHER_HOSTS = re.compile(r'^https?://(?!(?:127\.0\.0\.1|localhost)(?::\d+)?(?:/|$))')
JSON_HEADERS = {
    'access-control-allow-origin': '*',
    'content-type': 'application/json; charset=utf-8',
}
RATE_LIMIT_HEADERS = {
    **JSON_HEADERS,
    'retry-after': '60',
    'x-ratelimit-limit': '60',
    'x-ratelimit-remaining': '0',
    'x-ratelimit-reset': '1893456000',
    'x-ratelimit-resource': 'core',
    'x-ratelimit-used': '60',
}
REPO_BODY = {
    'full_name': 'Living-Proof-Labs/livingproof-common',
    'html_url': 'https://github.com/Living-Proof-Labs/livingproof-common',
    'stargazers_count': FIXTURE_STARS,
    'forks_count': 2,
    'description': 'fixture repository metadata',
}
RELEASE_BODY = {
    'tag_name': FIXTURE_TAG,
    'name': 'fixture',
    'html_url': (
        'https://github.com/Living-Proof-Labs/livingproof-common/releases/tag/' + FIXTURE_TAG),
    'draft': False,
    'prerelease': False,
}
RATE_LIMIT_BODY = {
    'message': (
        'API rate limit exceeded for 0.0.0.0. (But here\'s the good news: '
        'Authenticated requests get a higher rate limit. Check out the documentation '
        'for more details.)'),
    'documentation_url': (
        'https://docs.github.com/rest/overview/resources-in-the-rest-api#rate-limiting'),
}


def open_manual_page(browser, width, github):
    """Return context, page, failures, traffic, and GitHub responses.

    ``github`` is ``success`` or ``rate_limited``. Failures include local
    non-2xx responses, page errors, and any request that is not the local
    server. ``api.github.com`` is fulfilled here. Any other external host is
    aborted before it can reach the network.
    """
    if github not in {'success', 'rate_limited'}:
        raise ValueError(github)
    context = browser.new_context(viewport={'width': width, 'height': 844})
    failures = []
    traffic = {'fulfilled': [], 'continued': [], 'blocked': []}
    github_responses = []
    page = context.new_page()
    page.on('pageerror', lambda error: failures.append(f'pageerror: {error}'))
    page.on('requestfailed', lambda request: _record_failed(request, failures))
    page.on('response', lambda response: _record_response(response, failures, github_responses))
    _install_routes(context, github, traffic)
    return context, page, failures, traffic, github_responses


def _record_failed(request, failures):
    host = urlsplit(request.url).hostname
    reason = _failure_reason(request)
    # Replacing a document cancels its in-flight local reads. Those are not
    # missing assets. An aborted external request is still a failure.
    if host in {'127.0.0.1', 'localhost'} and reason == 'net::ERR_ABORTED':
        return
    failures.append(f'requestfailed {reason} {request.url}')


def _failure_reason(request):
    failure = request.failure
    if isinstance(failure, str):
        return failure
    if isinstance(failure, dict):
        return failure.get('errorText') or 'failed'
    return getattr(failure, 'error_text', None) or 'failed'


def _record_response(response, failures, github_responses):
    host = urlsplit(response.url).hostname
    if host == 'api.github.com':
        if response.request.method == 'GET':
            github_responses.append({
                'url': response.url,
                'status': response.status,
                'headers': {key.lower(): value for key, value in response.headers.items()},
            })
        return
    if response.status >= 400:
        failures.append(f'{response.status} {response.url}')


def _install_routes(context, github, traffic):
    def external(route):
        traffic['blocked'].append(route.request.url)
        route.abort('blockedbyclient')

    def metadata(route):
        path = urlsplit(route.request.url).path.rstrip('/')
        if path not in {REPO_PATH, RELEASE_PATH}:
            traffic['blocked'].append(route.request.url)
            route.abort('blockedbyclient')
            return
        if github == 'success':
            payload = RELEASE_BODY if path == RELEASE_PATH else REPO_BODY
            status, headers = 200, JSON_HEADERS
        else:
            payload = RATE_LIMIT_BODY
            status, headers = 403, RATE_LIMIT_HEADERS
        body = json.dumps(payload)
        traffic['fulfilled'].append({'url': route.request.url, 'status': status, 'body': body})
        route.fulfill(status=status, headers=headers, body=body)

    # Registered last, so the GitHub fixture wins over the external abort.
    context.route(OTHER_HOSTS, external)
    context.route(GITHUB_API, metadata)
