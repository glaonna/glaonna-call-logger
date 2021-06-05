# Local
from calllogger.api import info
from calllogger.utils import TokenAuth
from calllogger import running


def test_get_owner_info(requests_mock, mocker):
    tokenauth = TokenAuth("token")
    mocked = mocker.patch.object(running, "is_set")
    mocked.return_value = True
    expected_resp = {'id': 1, 'name': 'Test', 'email': 'test@test.com'}
    mocked_request = requests_mock.get(info.info_url, status_code=200, json=expected_resp)
    resp = info.get_owner_info(tokenauth, "identifier")

    assert mocked_request.called
    assert resp == expected_resp
