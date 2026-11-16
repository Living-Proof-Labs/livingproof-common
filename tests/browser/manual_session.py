# SPDX-License-Identifier: Apache-2.0
"""Manual browser session. GitHub metadata must come from a scoped fixture."""
REPO_PATH = '/repos/Living-Proof-Labs/livingproof-common'
RELEASE_PATH = REPO_PATH + '/releases/latest'
FIXTURE_TAG = 'v0.0.0-fixture'
FIXTURE_STARS = 7
RATE_LIMIT_HEADERS = {
    'access-control-allow-origin': '*',
    'content-type': 'application/json; charset=utf-8',
    'retry-after': '60',
    'x-ratelimit-limit': '60',
    'x-ratelimit-remaining': '0',
    'x-ratelimit-reset': '1893456000',
    'x-ratelimit-resource': 'core',
    'x-ratelimit-used': '60',
}


def open_manual_page(browser, width, github):
    """Return context, page, failures, traffic, and GitHub responses.

    ``github`` is ``success`` or ``rate_limited``. Failures must include local
    non-2xx responses and page errors. ``api.github.com`` must be fulfilled
    here and must not reach the network. Any other external host must fail the
    check without a live request.
    """
    raise NotImplementedError(
        'GitHub metadata is still requested live from api.github.com; '
        'scoped fixtures are not installed')
