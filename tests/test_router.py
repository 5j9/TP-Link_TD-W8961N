from datetime import datetime

from pytest import fixture
from json import loads
from pathlib import Path

from router import Router

# Copy tests/config-sample.json to tests/config.json and modify as needed.
with open(Path(__file__).parent / 'config.json') as f:
    config = loads(f.read())


@fixture(scope='session')
def router(request):
    with Router(**config) as router:
        router.login()
        yield router


def test_statistics(router):
    s = router.statistics('WLAN')
    assert s.keys() == {
        'Rx Drops Count',
        'Rx Errors Count',
        'Rx Frames Count',
        'Tx Drops Count',
        'Tx Errors Count',
        'Tx Frames Count',
    }
    assert all(type(v) is int for v in s.values())


def test_device_info(router):
    info = router.device_info()
    assert info.keys == {
        'Device Information',
        'LAN',
        'Wireless',
        'WAN',
        'ADSL',
    }


def test_system_log(router):
    entries = router.system_log()
    for dt, msg in entries:
        assert type(dt) is datetime
        assert type(msg) is str
