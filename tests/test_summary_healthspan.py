"""Balanced healthspan summary: equal domains, no invented scores or missing data."""
import pytest
from test_dashboard_ui import browser, dataset, open_dashboard, pw
from test_preview_assets import preview_module


def test_health_domains_have_equal_visual_priority(browser, tmp_path):
    page = open_dashboard(browser, tmp_path, preview_module().demo_dataset())
    try:
        cards = page.locator('#summary-view .domain-card')
        assert cards.count() == 6
        assert cards.first.get_attribute('data-domain') == 'sleep'
        assert cards.filter(has=page.locator('[data-domain="glucose"]')).count() == 0  # domains are peers, not nested
        assert page.locator('#summary-view .domain-card[data-domain="glucose"]').count() == 1
        sizes = cards.evaluate_all('els => els.map(e=>({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))')
        assert max(s['width'] for s in sizes) - min(s['width'] for s in sizes) < 2
        assert max(s['height'] for s in sizes) - min(s['height'] for s in sizes) < 2
        assert page.locator('#summary-view #glucose-day-chart').count() == 0
        pw.expect(page.locator('#summary-view')).to_contain_text('Health foundations')
        pw.expect(page.locator('#summary-view')).to_contain_text('No longevity score')
        pw.expect(page.locator('#demo-notice')).to_have_text('Synthetic demo data · Not a real person')
        page.locator('#summary-view [data-open="glucose"]').click()
        pw.expect(page.locator('#detail-body')).to_contain_text('Daily readings')
        assert page.locator('#detail-body #glucose-day-chart svg').count() == 1
    finally:
        page.close()


def test_missing_foundations_are_disclosed_not_filled(browser, tmp_path, dataset):
    page = open_dashboard(browser, tmp_path, dataset)
    try:
        assert page.locator('#summary-view .domain-card').count() == 2
        pw.expect(page.locator('#coverage-note')).to_contain_text('Sleep')
        pw.expect(page.locator('#coverage-note')).to_contain_text('Nutrition')
        assert page.locator('#summary-view [data-domain="sleep"]').count() == 0
    finally:
        page.close()


@pytest.mark.parametrize('width', [320, 390, 768, 1280])
def test_all_demo_domains_and_detail_periods_work_on_mobile(browser, tmp_path, width):
    page = open_dashboard(browser, tmp_path, preview_module().demo_dataset(), width)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    try:
        for key in page.locator('#summary-view [data-open]').evaluate_all('els=>els.map(e=>e.dataset.open)'):
            page.locator(f'#summary-view [data-open="{key}"]').click()
            dialog = page.locator('#detail')
            pw.expect(dialog).to_be_visible()
            for name in ('7 days', '30 days', 'All dates'):
                dialog.get_by_role('button', name=name, exact=True).click()
                assert dialog.evaluate('e=>e.scrollWidth<=e.clientWidth')
                assert 'NaN' not in dialog.inner_text()
            if key == 'glucose':
                for value in page.locator('#glucose-day option').evaluate_all('els=>els.map(e=>e.value)'):
                    page.locator('#glucose-day').select_option(value)
                    assert 'NaN' not in page.locator('#glucose-day-chart').inner_html()
            dialog.get_by_role('button', name='Done', exact=True).click()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors, errors
    finally:
        page.close()


def test_trends_are_neutral_and_require_observed_days(browser, tmp_path):
    data = preview_module().demo_dataset()
    page = open_dashboard(browser, tmp_path, data)
    try:
        pw.expect(page.locator('#summary-view')).to_contain_text('Latest 7 days vs prior 7')
        assert page.locator('#summary-view .trend-note').count() >= 3
        text = page.locator('#summary-view').inner_text().lower()
        assert 'biological age' not in text
        assert 'years added' not in text
        page.get_by_role('button', name='7 days', exact=True).click()
        pw.expect(page.locator('#summary-view')).to_contain_text('Not enough days to compare')
    finally:
        page.close()
