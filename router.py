from re import findall, search
from typing import Literal

from playwright.sync_api import sync_playwright, Page, ElementHandle


class Router:
    def __init__(
        self,
        *,
        username: str = 'admin',
        password: str = 'admin',
        ip_address: str = '192.168.1.1',
        **launch_kwargs,
    ):
        self.username = username
        self.password = password
        self.launch_kwargs = launch_kwargs
        self.url = f'http://{ip_address}/'

    def __enter__(self):
        playwright = self.playwright = sync_playwright().start()
        browser = self.browser = playwright.chromium.launch(
            **self.launch_kwargs
        )
        context = browser.new_context(no_viewport=True)
        self.page: Page = context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.browser.close()
        self.playwright.stop()

    def login(self):
        page = self.page
        page.goto(self.url + 'login_security.html')
        page.keyboard.type(self.username)
        page.keyboard.press('Tab')
        page.keyboard.type(self.password)
        page.keyboard.press('Enter')

    def statistics(
        self, interface: Literal['Ethernet', 'ADSL', 'WLAN']
    ) -> dict[str, int]:
        page = self.page
        page.goto(
            self.url + 'status/status_statistics.htm',
            referer='http://192.168.1.1/',
        )
        radio_value = {'Ethernet': 'Zero', 'ADSL': 'One', 'WLAN': 'Two'}[
            interface
        ]
        radio_selector = f'input[value="{radio_value}"]'
        if not page.wait_for_selector(radio_selector).is_checked():
            page.click(radio_selector)
        table_selector = 'table[bordercolor="#CCCCCC"]'
        page.wait_for_selector(table_selector)
        table = page.query_selector(table_selector)
        return _extract_column_data_from_table(table)

    def device_info(self) -> dict:
        page = self.page
        page.goto(self.url + 'status/status_deviceinfo.htm')
        page.get_by_text('Firmware Version')
        it = page.inner_text('body')
        d = dict(findall(r'(\S.*?)\s*:\s*(\S+.*?)\s*\n', it))

        fwver, _, hwver = (
            d['ADSL Firmware Version']
            .removeprefix('FwVer:')
            .partition(' HwVer:')
        )

        snr = d['SNR Margin'].split('\t')
        snr[0], snr[1] = float(snr[0]), float(snr[1])

        wan_text = it.partition('\nWAN')[2].partition('\nADSL')[0].strip()
        wan = [line.split('\t') for line in wan_text.splitlines()]

        wc_text = (
            it.partition('\nID	MAC\n')[2].partition('\nWAN')[0].strip()
        )
        wc = [line.split('\t') for line in wc_text.splitlines()]

        return {
            'Device Information': {
                'Firmware Version': d['Firmware Version'],
                'MAC Address': d['MAC Address'],
            },
            'LAN': {
                'IP Address': d['IP Address'],
                'Subnet Mask': d['Subnet Mask'],
                'DHCP Server': d['DHCP Server'],
            },
            'Wireless': {
                'Clients number': int(
                    search(r'Wireless Clients number is\s*(\d+)', it)[1]
                ),
                'Clients ID/MAC': wc,
            },
            'WAN': wan,
            'ADSL': {
                'FwVer': fwver,
                'HwVer': hwver,
                'Line State': d['Line State'],
                'Modulation': d['Modulation'],
                'Annex Mode': d['Annex Mode'],
                'Downstream/Upstream': {
                    'SNR Margin': _nnu(d['SNR Margin']),
                    'Line Attenuation': _nnu(d['Line Attenuation']),
                    'Data Rate': _nnu(d['Data Rate']),
                    'Max Rate': _nnu(d['Max Rate']),
                    'POWER': _nnu(d['POWER']),
                    'CRC': (*map(int, d['CRC'].split('\t')),),
                },
            },
        }


def _nnu(s: str) -> tuple[int | float, int | float, str]:
    t = s.split('\t')
    try:
        return int(t[0]), int(t[1]), t[2]
    except ValueError:
        return float(t[0]), float(t[1]), t[2]


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
