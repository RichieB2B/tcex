# -*- coding: utf-8 -*-
"""TcEx testing Framework."""
import json
import logging
import os
import random
import string
import time
import traceback
import uuid
from datetime import datetime

import pytest
from tcex import TcEx
from tcex.inputs import FileParams
from tcex.app_config_object.install_json import InstallJson
from tcex.app_config_object.profile import Profile

from ..logger import RotatingFileHandlerCustom
from .stage_data import Stager
from .validate_data import Validator

logger = logging.getLogger('TestCase')
lfh = RotatingFileHandlerCustom(filename='log/tests.log')
lfh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
lfh.setFormatter(formatter)
logger.addHandler(lfh)
logger.setLevel(logging.DEBUG)


class TestCase:
    """Base TestCase Class"""

    _app_path = os.getcwd()
    _current_test = None
    # _input_params = None
    # _install_json = None
    _profile = None
    _stager = None
    _staged_tc_data = []
    _timer_class_start = None
    _timer_method_start = None
    _validator = None
    app = None
    context = None
    enable_update_profile = False
    ij = InstallJson()
    log = logger
    env = set(os.getenv('TCEX_TEST_ENVS', 'build').split(','))
    redis_client = None
    tcex = None
    tcex_testing_context = None

    @staticmethod
    def _encrypt_file_contents(key, data):
        """Return encrypted data for file params."""
        fp = FileParams()
        fp.EVP_EncryptInit(fp.EVP_aes_128_cbc(), key.encode('utf-8'), b'\0' * 16)
        return fp.EVP_EncryptUpdate(data) + fp.EVP_EncryptFinal()

    def _exit(self, code):
        """Log and return exit code"""
        self.log.info(f'[run] Exit Code: {code}')
        return code

    @staticmethod
    def _to_bool(value):
        """Return bool value from int or string."""
        return str(value).lower() in ['1', 'true']

    def _update_path_args(self, args):
        """Update path in args for each test profile."""
        args['tc_in_path'] = self.profile.tc_in_path
        args['tc_log_path'] = self.profile.tc_log_path
        args['tc_out_path'] = self.profile.tc_out_path
        args['tc_temp_path'] = self.profile.tc_temp_path

    def app_init(self, args):
        """Return an instance of App."""
        from app import App  # pylint: disable=import-error

        # return App(self.get_tcex(args))
        args = args or {}

        # update path args
        self._update_path_args(args)

        # update default args with app args
        app_args = dict(self.default_args)
        app_args.update(args)
        # app_args['tc_log_file'] = f'{self.test_case_name}.log'
        app_args['tc_logger_name'] = self.context

        if self.ij.runtime_level.lower() in [
            'triggerservice',
            'webhooktriggerservice',
        ]:
            # service Apps will get their args/params from encrypted file in the "in" directory
            data = json.dumps(app_args, sort_keys=True).encode('utf-8')
            key = ''.join(random.choice(string.ascii_lowercase) for i in range(16))
            encrypted_data = self._encrypt_file_contents(key, data)

            app_params_json = os.path.join(self.test_case_feature_dir, '.app_params.json')
            with open(app_params_json, 'wb') as fh:
                fh.write(encrypted_data)

            # create environment variable for tcex inputs method to pick up to read encrypted file
            os.environ['TC_APP_PARAM_KEY'] = key
            os.environ['TC_APP_PARAM_FILE'] = app_params_json

            # tcex will read args/params from encrypted file
            tcex = TcEx()
        else:
            tcex = TcEx(config=app_args)

        return App(tcex)

    def app_init_create_config(self, args, output_variables, tcex_testing_context):
        """Create files necessary to start a Service App."""
        args['tc_playbook_out_variables'] = ','.join(output_variables)
        args['tcex_testing_context'] = tcex_testing_context

        # update path args
        self._update_path_args(args)

        # merge default and app args
        app_args = dict(self.default_args)
        app_args.update(args)

        # service Apps will get their args/params from encrypted file in the "in" directory
        data = json.dumps(app_args, sort_keys=True).encode('utf-8')
        key = ''.join(random.choice(string.ascii_lowercase) for i in range(16))
        encrypted_data = self._encrypt_file_contents(key, data)

        # create files necessary to run Service App
        if not os.path.exists(app_args.get('tc_in_path')):
            os.mkdir(app_args.get('tc_in_path'))

        app_params_json = os.path.join(app_args.get('tc_in_path'), '.app_params.json')
        with open(app_params_json, 'wb') as fh:
            fh.write(encrypted_data)

        # create environment variable for tcex inputs method to pick up to read encrypted file
        os.environ['TC_APP_PARAM_KEY'] = key
        os.environ['TC_APP_PARAM_FILE'] = app_params_json

    @staticmethod
    def check_environment(environments):
        """Check if test case matches current environments, else skip test.

        Args:
            environments (list): The test case environments.
        """
        test_envs = environments or ['build']
        os_envs = set(os.environ.get('TCEX_TEST_ENVS', 'build').split(','))
        if not os_envs.intersection(set(test_envs)):
            pytest.skip('Profile skipped based on current environment.')

    @property
    def default_args(self):
        """Return App default args."""
        args = {
            'api_access_id': os.getenv('API_ACCESS_ID'),
            'api_default_org': os.getenv('API_DEFAULT_ORG'),
            'api_secret_key': os.getenv('API_SECRET_KEY'),
            'tc_api_path': os.getenv('TC_API_PATH'),
            'tc_in_path': os.getenv('TC_IN_PATH', 'log'),
            'tc_log_level': os.getenv('TC_LOG_LEVEL', 'trace'),
            'tc_log_path': os.getenv('TC_LOG_PATH', 'log'),
            'tc_log_to_api': self._to_bool(os.getenv('TC_LOG_TO_API', 'false')),
            'tc_out_path': os.getenv('TC_OUT_PATH', 'log'),
            'tc_proxy_external': self._to_bool(os.getenv('TC_PROXY_EXTERNAL', 'false')),
            'tc_proxy_host': os.getenv('TC_PROXY_HOST', 'localhost'),
            'tc_proxy_password': os.getenv('TC_PROXY_PASSWORD', ''),
            'tc_proxy_port': os.getenv('TC_PROXY_PORT', '4242'),
            'tc_proxy_tc': self._to_bool(os.getenv('TC_PROXY_TC', 'false')),
            'tc_proxy_username': os.getenv('TC_PROXY_USERNAME', ''),
            'tc_temp_path': os.getenv('TC_TEMP_PATH', 'log'),
        }
        if os.getenv('TC_TOKEN'):
            args['tc_token'] = os.getenv('TC_TOKEN')
            args['tc_token_expires'] = os.getenv('TC_TOKEN_EXPIRES')
        return args

    def init_profile(self, profile_name, replace_exit_message=False, replace_outputs=False):
        """Stages and sets up the profile given a profile name"""
        self._profile = Profile(
            default_args=self.default_args,
            name=profile_name,
            redis_client=self.redis_client,
            replace_exit_message=replace_exit_message,
            replace_outputs=replace_outputs,
            tcex_testing_context=self.tcex_testing_context,
        )

        # stage ThreatConnect data based on current profile
        self._staged_tc_data = self.stager.threatconnect.entities(
            self._profile.stage_threatconnect, self._profile.owner
        )
        print('stage_tc_data', self._staged_tc_data)

        # insert staged data for replacement
        self._profile.tc_staged_data = self._staged_tc_data

        # update schema
        self._profile.init()

        # stage kvstore data based on current profile
        self.stager.redis.from_dict(self._profile.stage_kvstore)

    # @property
    # def install_json(self):
    #     """Return install.json contents."""
    #     file_fqpn = os.path.join(self._app_path, 'install.json')
    #     if self._install_json is None:
    #         if os.path.isfile(file_fqpn):
    #             with open(file_fqpn, 'r') as fh:
    #                 self._install_json = json.load(fh)
    #         else:
    #             print(f'File "{file_fqpn}" could not be found.')
    #     return self._install_json

    # def input_params(self):
    #     """Return install.json params in a dict with name param as key.

    #     Returns:
    #         dict: A dictionary containing the install.json input params with name as key.
    #     """
    #     if self._input_params is None:
    #         self._input_params = {}
    #         # Currently there is no support for projects with multiple install.json files.
    #         for p in self.ij.params:
    #             self._input_params.setdefault(p.get('name'), p)
    #     return self._input_params

    def log_data(self, stage, label, data, level='info'):
        """Log validation data."""
        msg = f"{f'[{stage}]'!s:>20} : {label!s:<15}: {data!s:<50}"
        getattr(self.log, level)(msg)

    @property
    def profile(self):
        """Return profile instance."""
        return self._profile

    # @property
    # def profile_name(self):
    #     """Return partially parsed test case data."""
    #     name_pattern = r'^test_[a-zA-Z0-9_]+\[(.+)\]$'
    #     try:
    #         return re.search(name_pattern, self.test_case_data[-1]).group(1)
    #     except AttributeError:
    #         return None

    # @property
    # def profile_names(self):
    #     """Return all profile names in the profiles.d directory."""
    #     profile_names = []
    #     for filename in sorted(os.listdir(self.test_case_profile_dir)):
    #         if filename.endswith('.json'):
    #             profile_names.append(filename.replace('.json', ''))
    #     return profile_names

    def run(self, args):
        """Implement in Child Class"""
        raise NotImplementedError('Child class must implement this method.')

    def run_app_method(self, app, method):
        """Run the provided App method."""
        try:
            getattr(app, method)()
        except SystemExit as e:
            self.log.info(f'[run] Exit Code: {e.code}')
            self.log.error(f'App failed in {method}() method ({e}).')
            app.tcex.log.info(f'Exit Code: {e.code}')
            return e.code
        except Exception:
            self.log.error(
                f'App encountered except in {method}() method ({traceback.format_exc()}).'
            )
            return 1
        return 0

    @classmethod
    def setup_class(cls):
        """Run once before all test cases."""
        cls._timer_class_start = time.time()
        cls.log.info(f"{'#' * 10} Setup Class {'#' * 10}")
        TestCase.log_data(TestCase(), 'setup class', 'started', datetime.now().isoformat())
        TestCase.log_data(TestCase(), 'setup class', 'local envs', cls.env)

    def setup_method(self):
        """Run before each test method runs."""
        self._timer_method_start = time.time()
        self._current_test = os.getenv('PYTEST_CURRENT_TEST').split(' ')[0]
        self.log.info(f"{'=' * 10} {self._current_test} {'=' * 10}")
        self.log_data('setup method', 'started', datetime.now().isoformat())

        # create and log current context
        self.context = os.getenv('TC_PLAYBOOK_DB_CONTEXT', str(uuid.uuid4()))
        self.log_data('setup method', 'context', self.context)

        # setup per method instance of tcex
        args = dict(self.default_args)
        args['tc_log_file'] = os.path.join(self.test_case_feature, self.test_case_name, 'setup.log')
        args['tc_logger_name'] = f'tcex-{self.test_case_feature}-{self.test_case_name}'
        self.tcex = TcEx(config=args)

        # initialize new stager instance
        self._stager = self.stager_init()

        # initialize new validator instance
        self._validator = self.validator_init()

    @property
    def stager(self):
        """Return instance of Stager class."""
        return self._stager

    def stager_init(self):
        """Return instance of Stager class."""
        tc_log_file = os.path.join(self.test_case_feature, self.test_case_name, 'stage.log')

        # args data
        args = dict(self.default_args)

        # override default log level if profiled
        args['tc_log_level'] = 'warning'

        # set log path to be the feature and test case name
        args['tc_log_file'] = tc_log_file

        # set a logger name to have a logger specific for stager
        args['tc_logger_name'] = 'tcex-stager'

        tcex = TcEx(config=args)
        return Stager(tcex, logger, self.log_data)

    @classmethod
    def teardown_class(cls):
        """Run once before all test cases."""
        cls.log.info(f"{'^' * 10} Teardown Class {'^' * 10}")
        TestCase.log_data(TestCase(), 'teardown class', 'finished', datetime.now().isoformat())
        TestCase.log_data(
            TestCase(), 'teardown class', 'elapsed', time.time() - cls._timer_class_start
        )

    def teardown_method(self):
        """Run after each test method runs."""
        if self.enable_update_profile and self.ij.runtime_level.lower() not in [
            'triggerservice',
            'webhooktriggerservice',
        ]:
            # exit message can not be validated for a Service App
            self.profile.update_exit_message()

        # delete threatconnect staged data
        self.stager.threatconnect.delete_staged(self._staged_tc_data)

        # log running times
        self.log_data('teardown method', 'finished', datetime.now().isoformat())
        self.log_data('teardown method', 'elapsed', time.time() - self._timer_class_start)

    @property
    def test_case_data(self):
        """Return partially parsed test case data."""
        return os.getenv('PYTEST_CURRENT_TEST').split(' ')[0].split('::')

    @property
    def test_case_feature(self):
        """Return partially parsed test case data."""
        return self.test_case_data[0].split('/')[1].replace('/', '-')

    @property
    def test_case_feature_dir(self):
        """Return profile fully qualified filename."""
        return os.path.join(self._app_path, 'tests', self.test_case_feature)

    @property
    def test_case_profile_dir(self):
        """Return profile fully qualified filename."""
        return os.path.join(self._app_path, 'tests', self.test_case_feature, 'profiles.d')

    @property
    def test_case_name(self):
        """Return partially parsed test case data."""
        return self.test_case_data[-1].replace('/', '-').replace('[', '-').replace(']', '')

    def validate_exit_message(self, test_exit_message, op='eq', **kwargs):
        """Validate App exit message."""
        if test_exit_message is not None:
            message_tc_file = os.path.join(
                self.default_args.get('tc_out_path'),
                self.test_case_feature,
                self.test_case_name,
                'message.tc',
            )
            app_exit_message = None
            if os.path.isfile(message_tc_file):
                with open(message_tc_file, 'r') as mh:
                    app_exit_message = mh.read()

                if app_exit_message:
                    passed, assert_error = self.validator.compare(
                        app_exit_message, test_exit_message, op=op, **kwargs
                    )
                    assert passed, assert_error
                else:
                    assert False, 'The message.tc file was empty.'
            else:
                assert False, f'No message.tc file found at ({message_tc_file}).'

    @property
    def validator(self):
        """Return instance of Stager class."""
        return self._validator

    def validator_init(self):
        """Return instance of Stager class."""
        tc_log_file = os.path.join(self.test_case_feature, self.test_case_name, 'validate.log')

        # args data
        args = dict(self.default_args)

        # override default log level if profiled
        args['tc_log_level'] = 'warning'

        # set log path to be the feature and test case name
        args['tc_log_file'] = tc_log_file

        # set a logger name to have a logger specific for stager
        args['tc_logger_name'] = 'tcex-validator'

        tcex = TcEx(config=args)
        return Validator(tcex, logger, self.log_data)
