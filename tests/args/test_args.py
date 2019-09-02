# -*- coding: utf-8 -*-
"""Test the TcEx Args Config Module."""
import json
import sys

from tcex import TcEx
from tcex.args import Args


class MockGet:
    """Mock tcex session.get() method."""

    def __init__(self, data, ok=True):
        """Initialize class properties."""
        self.data = data
        self._ok = ok

    @property
    def headers(self):
        """Mock headers property"""
        return {'content-type': 'application/json'}

    def json(self):
        """Mock json method"""
        return self.data

    @property
    def ok(self):
        """Mock ok property"""
        return self._ok

    @property
    def reason(self):
        """Mock text property"""
        return 'reason'

    @property
    def text(self):
        """Mock text property"""
        return json.dumps(self.data)


# pylint: disable=W0201
class TestArgsConfig:
    """Test TcEx Args Config."""

    @staticmethod
    def test_add_argument(config_data, tc_log_file):
        """Test args.

        Test argument_parser add_argument method with a required field and config_data.
        """
        # update config data
        config_data['name'] = 'pytest'
        config_data['tc_log_file'] = tc_log_file
        config_data['tc_log_to_api'] = True

        # clear sys.argv to avoid invalid arguments
        sys_argv_orig = sys.argv
        sys.argv = sys.argv[:1]

        # initialize tcex and add required argument
        tcex = TcEx(config=config_data)
        tcex.parser.add_argument('--name', required=True)

        # parse args
        args = tcex.args
        assert args.name == config_data.get('name')

        # reset sys.argv
        sys.argv = sys_argv_orig

    @staticmethod
    def test_aot_args(tcex, config_data, tc_log_file):
        """Test tcex_args.config_file() method."""
        tc_action_channel = 'pytest-action-channel'

        # add custom config data
        config_data['my_bool'] = 'true'
        config_data['my_multi'] = 'one|two'

        # send AOT message
        aot_msg = {'type': 'execute', 'params': config_data}
        tcex.playbook.db.rpush(tc_action_channel, json.dumps(aot_msg))

        # update sys.argv to enable aot
        sys_argv_orig = sys.argv
        sys.argv = sys.argv[:1] + [
            '--tc_aot_enabled',
            '--tc_action_channel',
            tc_action_channel,
            '--tc_log_file',
            tc_log_file,
        ]
        my_tcex = TcEx()

        # add custom args (install.json defined in conftest.py)
        my_tcex.parser.add_argument('--my_bool', action='store_true')
        my_tcex.parser.add_argument('--my_multi', action='append')

        # parser args
        args = my_tcex.args
        rargs = my_tcex.rargs

        assert args.my_bool is True
        assert rargs.my_bool is True  # pylint: disable=no-member
        assert args.my_multi == ['one', 'two']
        assert rargs.my_multi == ['one', 'two']  # pylint: disable=no-member

        # reset sys.argv
        sys.argv = sys_argv_orig

    @staticmethod
    def test_args(tcex):
        """Test args."""
        assert tcex.args.tc_token
        assert tcex.args.tc_token_expires
        assert tcex.args.api_default_org == 'TCI'

    @staticmethod
    def test_config_file(tcex):
        """Test tcex_args.config_file() method."""
        tcex.tcex_args.config_file('tests/args/config.json')
        tcex.tcex_args.config_file('tests/args/dummy-config.json')

    @staticmethod
    def test_config_replace(tcex):
        """Test args."""

        new_api_default_org = 'new_api_default_org'
        tcex.tcex_args.config({'api_default_org': new_api_default_org}, replace=True)
        assert tcex.args.api_default_org == new_api_default_org

    @staticmethod
    def test_load_secure_params(tcex, config_data, monkeypatch):
        """Test load_secure_params method."""
        get_orig = tcex.session.get

        # monkeypatch method
        def mp_get(*args, **kwargs):  # pylint: disable=unused-argument
            return MockGet({'inputs': config_data})

        monkeypatch.setattr(tcex.session, 'get', mp_get)

        data = tcex.tcex_args._load_secure_params()

        assert data.get('tc_log_path') == 'log'

        # reset monkeypatched tcex.session.get()
        tcex.session.get = get_orig

    @staticmethod
    def test_load_secure_params_bad_data(tcex, monkeypatch):
        """Test load_secure_params method."""
        get_orig = tcex.session.get

        # monkeypatch method
        def mp_get(*args, **kwargs):  # pylint: disable=unused-argument
            return MockGet({})

        monkeypatch.setattr(tcex.session, 'get', mp_get)

        try:
            tcex.tcex_args._load_secure_params()
        except RuntimeError:
            assert True

        # reset monkeypatched tcex.session.get()
        tcex.session.get = get_orig

    @staticmethod
    def test_load_secure_params_not_ok(tcex, monkeypatch):
        """Test load_secure_params method."""
        get_orig = tcex.session.get

        # monkeypatch method
        def mp_get(*args, **kwargs):  # pylint: disable=unused-argument
            return MockGet(data={}, ok=False)

        monkeypatch.setattr(tcex.session, 'get', mp_get)

        try:
            tcex.tcex_args._load_secure_params()
        except RuntimeError:
            assert True

        # reset monkeypatched tcex.session.get()
        tcex.session.get = get_orig

    @staticmethod
    def test_update_params(tcex, config_data):
        """Test tcex_args.config_file() method."""
        # add custom config data
        config_data['my_bool'] = 'true'
        config_data['my_multi'] = 'one|two'
        config_data['unknown_args'] = True  # test unknown args

        # update params
        updated_params = tcex.tcex_args.update_params(config_data)
        tcex.tcex_args.config(updated_params, False)

        # add custom args (install.json defined in conftest.py)
        tcex.parser.add_argument('--my_bool', action='store_true')
        tcex.parser.add_argument('--my_multi', action='append')

        # parser args
        args = tcex.args
        rargs = tcex.rargs

        assert args.my_bool is True
        assert rargs.my_bool is True  # pylint: disable=no-member
        assert args.my_multi == ['one', 'two']
        assert rargs.my_multi == ['one', 'two']  # pylint: disable=no-member

    @staticmethod
    def test_secure_params(config_data, tc_log_file, monkeypatch):
        """Test load_secure_params method."""
        # add custom config data
        config_data['my_bool'] = 'true'
        config_data['my_multi'] = 'one|two'

        # monkeypatch session get method
        def load_secure_params(self):  # pylint: disable=unused-argument
            return config_data

        monkeypatch.setattr(Args, '_load_secure_params', load_secure_params)

        # update sys.argv to enable secure_params
        sys_argv_orig = sys.argv
        sys.argv = sys.argv[:1] + [
            '--tc_secure_params',
            '--tc_token',
            config_data.get('tc_token'),
            '--tc_token_expires',
            config_data.get('tc_token_expires'),
            '--tc_log_file',
            tc_log_file,
        ]
        tcex = TcEx()

        # add custom args (install.json defined in conftest.py)
        tcex.parser.add_argument('--my_bool', action='store_true')
        tcex.parser.add_argument('--my_multi', action='append')

        # parser args
        args = tcex.args
        rargs = tcex.rargs

        assert args.my_bool is True
        assert rargs.my_bool is True  # pylint: disable=no-member
        assert args.my_multi == ['one', 'two']
        assert rargs.my_multi == ['one', 'two']  # pylint: disable=no-member

        # reset sys.argv
        sys.argv = sys_argv_orig

    @staticmethod
    def test_unknown_args(tcex):
        """Test args."""
        # update sys.argv to enable aot
        sys_argv_orig = sys.argv
        sys.argv = sys.argv[:1] + ['--unknown_arg']
        args = tcex.args  # noqa: F841; pylint: disable=unused-variable
        assert tcex.tcex_args._unknown_args == ['--unknown_arg']

        # reset sys.argv
        sys.argv = sys_argv_orig
