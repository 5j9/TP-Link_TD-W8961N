from json import loads
from pathlib import Path
from typing import Literal

from playwright.sync_api import sync_playwright, Page, ElementHandle


class Router:
    def __init__(
        self,
        *,
        page: Page,
        username: str = 'admin',
        password: str = 'admin',
        ip_address: str = '192.168.1.1',
    ):
        self.username = username
        self.password = password
        self.url = f'http://{ip_address}/'
        self.page = page

    def login(self):
        page = self.page
        page.goto(self.url + 'login_security.html')
        page.keyboard.type(self.username)
        page.keyboard.press('Tab')
        page.keyboard.type(self.password)
        page.keyboard.press('Enter')

    def statistics(
        self, interface: Literal['Ethernet', 'ADSL', 'WLAN']
    ) -> dict:
        page = self.page
        page.goto(
            self.url + 'status/status_statistics.htm',
            referer='http://192.168.1.1/',
        )
        radio_value = {'Ethernet': 'Zero', 'ADSL': 'One', 'WLAN': 'Two'}[
            interface
        ]
        radio_selector = f'input[value="{radio_value}"]'
        page.click(radio_selector)
        table_selector = 'table[bordercolor="#CCCCCC"]'
        page.wait_for_selector(table_selector)
        table = page.query_selector(table_selector)
        return _extract_column_data_from_table(table)


def _extract_col_from_trs(trs: list[ElementHandle], col: int) -> list:
    return [
        tr.query_selector(f'td:nth-child({col})').inner_text().strip()
        for tr in trs
    ]


def _extract_column_data_from_table(
    table: ElementHandle, map_=((1, 2), (3, 4)), ignore_header=True
) -> dict:
    trs = table.query_selector_all('tr')
    if ignore_header:
        trs.pop(0)

    result = {}
    for k_col, v_col in map_:
        result |= zip(
            _extract_col_from_trs(trs, k_col),
            [
                int(i.replace(',', ''))
                for i in _extract_col_from_trs(trs, v_col)
            ],
        )

    return result


with open(Path(__file__).parent / 'config.json') as f:
    config = loads(f.read())

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=config['headless'], args=['--start-maximized']
    )
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    router = Router(
        username=config['username'], password=config['password'], page=page
    )
    router.login()
    statistics = router.statistics('WLAN')
    print(statistics)

    browser.close()
