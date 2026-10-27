"""Exercise the shipped HTML under its actual repository path."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import threading

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'artifacts/docs'


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    web = tmp_path_factory.mktemp('web')
    (web / 'livingproof-common').symlink_to(OUTPUT / 'html', target_is_directory=True)
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(web))
    http = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{http.server_port}/livingproof-common'
    http.shutdown()
    http.server_close()
    thread.join()


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as playwright:
        options = {'headless': True}
        if os.environ.get('COMMON_BROWSER_EXECUTABLE'):
            options['executable_path'] = os.environ['COMMON_BROWSER_EXECUTABLE']
        browser = playwright.chromium.launch(**options)
        yield browser
        browser.close()


@pytest.mark.parametrize('width', [1280, 390], ids=['desktop', 'mobile'])
def test_navigation_search_and_assets(browser, server, width):
    context = browser.new_context(viewport={'width': width, 'height': 844})
    page = context.new_page()
    failures = []
    page.on('pageerror', lambda error: failures.append(str(error)))
    page.on('response', lambda response: failures.append(response.url)
            if response.status >= 400 else None)
    page.goto(server + '/index.html')
    if width == 390:
        page.locator('label.md-header__button[for="__drawer"]:visible').first.click()
    page.get_by_role('link', name='API', exact=True).first.click()
    expect(page.locator('article')).to_contain_text('current_version')
    page.goto(server + '/search.html?q=current_version')
    expect(page.locator('article')).to_contain_text('not automatically submitted')
    if width == 390:
        page.locator('label[for="__search"]:visible').first.click()
    else:
        page.get_by_role('button', name='Search', exact=False).first.click()
    page.get_by_placeholder('Search', exact=True).fill('current_version')
    result = page.locator('dialog a[href*="api.html"]').first
    expect(result).to_be_visible(timeout=15000)
    result.click()
    expect(page).to_have_url(re.compile('/livingproof-common/api.html'))
    expect(page.locator('article')).to_contain_text('current_version')
    (OUTPUT / 'screenshots').mkdir(exist_ok=True)
    page.screenshot(path=str(OUTPUT / 'screenshots' / f'navigation-{width}.png'))
    assert not failures, failures
    context.close()


@pytest.mark.parametrize('mode', ['light', 'dark'])
def test_theme_and_mobile_code(browser, server, mode):
    context = browser.new_context(viewport={'width': 390, 'height': 844}, color_scheme=mode)
    page = context.new_page()
    page.goto(server + '/usage.html')
    page.wait_for_function("getComputedStyle(document.body).backgroundColor !== 'rgba(0, 0, 0, 0)'")
    color = page.evaluate('getComputedStyle(document.body).backgroundColor')
    assert (sum(map(int, re.findall(r'\d+', color)[:3])) < 384) == (mode == 'dark')
    expect(page.locator('article pre').first).to_be_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    seen = set()
    for _ in range(3):
        page.locator('[data-md-component="palette"] label:visible').first.click()
        page.wait_for_timeout(150)
        seen.add(page.evaluate('getComputedStyle(document.body).backgroundColor'))
    assert len(seen) >= 2
    context.close()


def test_version_scenarios_and_legacy_anchors(browser, server):
    page = browser.new_page()
    record = json.loads((OUTPUT / 'html/build.json').read_text())
    page.goto(server + '/index.html')
    expect(page.locator('article')).to_contain_text(record['source_commit'])
    for anchor in ['consumer-identity', 'api-reference', 'contributor-tasks',
                   'software-test-coverage', 'livingproof_common.versioning.current_version']:
        page.goto(server + '/index.html#' + anchor)
        link = page.locator(f'[id="{anchor}"] a')
        expect(link).to_have_count(1)
        link.click()
        assert '/livingproof-common/' in page.url
        if 'current_version' in anchor:
            expect(page.locator('article')).to_contain_text('current_version(consumer)')
    page.goto(server + '/scenarios.html')
    report = json.loads((OUTPUT / 'html/scenarios.json').read_text())
    assert len(report['scenarios']) == 7
    for row in report['scenarios']:
        expect(page.locator('article')).to_contain_text(row['scenario'])
        expect(page.locator('article')).to_contain_text(row['steps'].splitlines()[0])
    page.close()


@pytest.mark.parametrize('filename', ['genindex.html', 'py-modindex.html'])
def test_old_generated_indexes_reach_api(browser, server, filename):
    page = browser.new_page()
    page.goto(server + '/' + filename)
    expect(page).to_have_url(server + '/api.html')
    expect(page.locator('article')).to_contain_text('current_version(consumer)')
    page.close()


def test_navigation_and_revision_without_scripts(browser, server):
    context = browser.new_context(java_script_enabled=False)
    page = context.new_page()
    record = json.loads((OUTPUT / 'html/build.json').read_text())
    page.goto(server + '/contribute.html')
    root = page.get_by_role('link', name='Documentation home', exact=True).first
    expect(root).to_have_attribute('href', 'https://docs.livingprooflabs.com/')
    root.focus()
    expect(root).to_be_focused()
    expect(page.get_by_role('link', name='Help / report an issue')).to_have_attribute(
        'href', 'https://github.com/Living-Proof-Labs/livingproof-common/issues')
    expect(page.get_by_role('link', name='Docs: development', exact=False)).to_have_attribute(
        'href', 'https://github.com/Living-Proof-Labs/livingproof-common/tree/' + record['source_commit'])
    page.goto(server + '/tasks.html')
    expect(page.locator('article')).to_contain_text('uv run --locked --no-sync ruff check .')
    context.close()
