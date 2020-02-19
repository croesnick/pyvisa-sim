import os

import pytest
import pyvisa


def pytest_logger_config(logger_config):
    logger_config.add_loggers(['pyvisa-sim'], stdout_level='debug')
    # logger_config.set_log_option_default('')


@pytest.fixture(scope='session')
def resource_manager():
    rm = pyvisa.ResourceManager('@sim')
    yield rm
    rm.close()


@pytest.fixture
def channels():
    path = os.path.join(os.path.dirname(__file__), 'fixtures', 'channels.yaml')
    rm = pyvisa.ResourceManager(path + '@sim')
    yield rm
    rm.close()
