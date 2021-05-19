# Copyright 2020 Planet Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import base64
from http import HTTPStatus
import json
import logging

import httpx
import pytest
import respx

from planet import auth

LOGGER = logging.getLogger(__name__)


# skip the global mock of _SecretFile.read
# for this module
@pytest.fixture(autouse=True, scope='module')
def test_secretfile_read():
    return


@pytest.fixture
def secret_path(monkeypatch, tmp_path):
    secret_path = str(tmp_path / '.test')
    monkeypatch.setattr(auth, 'SECRET_FILE_PATH', secret_path)
    yield secret_path


def test_Auth_from_key():
    test_auth_env1 = auth.Auth.from_key('testkey')
    assert test_auth_env1.value == 'testkey'


def test_Auth_from_key_empty():
    with pytest.raises(auth.APIKeyAuthException):
        _ = auth.Auth.from_key('')


def test_Auth_from_file(secret_path):
    with open(secret_path, 'w') as fp:
        fp.write('{"key": "testvar"}')

    test_auth = auth.Auth.from_file()
    assert test_auth.value == 'testvar'


def test_Auth_from_file_doesnotexist(secret_path):
    with pytest.raises(auth.AuthException):
        _ = auth.Auth.from_file(secret_path)


def test_Auth_from_file_wrongformat(secret_path):
    with open(secret_path, 'w') as fp:
        fp.write('{"notkey": "testvar"}')

    with pytest.raises(auth.AuthException):
        _ = auth.Auth.from_file(secret_path)


def test_Auth_from_file_alternate(tmp_path):
    secret_path = str(tmp_path / '.test')
    with open(secret_path, 'w') as fp:
        fp.write('{"key": "testvar"}')

    test_auth = auth.Auth.from_file(secret_path)
    assert test_auth.value == 'testvar'


def test_Auth_from_env(monkeypatch):
    monkeypatch.setenv('PL_API_KEY', 'testkey')
    test_auth_env = auth.Auth.from_env()
    assert test_auth_env.value == 'testkey'


def test_Auth_from_env_failure(monkeypatch):
    monkeypatch.delenv('PL_API_KEY', raising=False)
    with pytest.raises(auth.AuthException):
        _ = auth.Auth.from_env()


def test_Auth_from_env_alternate_success(monkeypatch):
    alternate = 'OTHER_VAR'
    monkeypatch.setenv(alternate, 'testkey')
    monkeypatch.delenv('PL_API_KEY', raising=False)

    test_auth_env = auth.Auth.from_env(alternate)
    assert test_auth_env.value == 'testkey'


def test_Auth_from_env_alternate_doesnotexist(monkeypatch):
    alternate = 'OTHER_VAR'
    monkeypatch.delenv(alternate, raising=False)
    monkeypatch.delenv('PL_API_KEY', raising=False)

    with pytest.raises(auth.AuthException):
        _ = auth.Auth.from_env(alternate)


@respx.mock
def test_Auth_from_login(monkeypatch):
    test_url = 'http://MockNotRealURL/'
    login_url = test_url + 'login'

    apikey = base64.urlsafe_b64encode(
        json.dumps({'api_key': 'foobar'}).encode()
    ).decode()

    response = {
        'token':  'junk.' + apikey
    }
    mock_resp = httpx.Response(HTTPStatus.OK, json=response)
    respx.post(login_url).return_value = mock_resp

    test_auth = auth.Auth.from_login('email', 'pw', base_url=test_url)
    assert test_auth.value == 'foobar'


def test_Auth_write_doesnotexist(tmp_path):
    test_auth = auth.Auth.from_key('test')
    secret_path = str(tmp_path / '.test')
    test_auth.write(secret_path)

    with open(secret_path, 'r') as fp:
        assert json.loads(fp.read()) == {"key": "test"}


def test_Auth_write_exists(tmp_path):
    secret_path = str(tmp_path / '.test')

    with open(secret_path, 'w') as fp:
        fp.write('{"existing": "exists"}')

    test_auth = auth.Auth.from_key('test')
    test_auth.write(secret_path)

    with open(secret_path, 'r') as fp:
        assert json.loads(fp.read()) == {"key": "test", "existing": "exists"}
