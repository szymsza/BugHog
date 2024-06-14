import logging
import logging.handlers
import os
import sys

import bci.database.mongo.container as container
from bci.evaluations.logic import DatabaseConnectionParameters

logger = logging.getLogger(__name__)


class Global:

    custom_page_folder = '/app/experiments/pages'

    @staticmethod
    def get_extension_folder(browser: str) -> str:
        return Global.get_browser_config_class(browser).extension_folder

    @staticmethod
    def get_browser_config_class(browser: str):
        match browser:
            case 'chromium':
                return Chromium
            case 'firefox':
                return Firefox
            case _:
                raise ValueError(f'Invalid browser \'{browser}\'')

    @staticmethod
    def check_required_env_parameters() -> bool:
        fatal = False
        # HOST_PWD
        if (host_pwd := os.getenv('HOST_PWD')) in ['', None]:
            logger.fatal('The "HOST_PWD" variable is not set. If you\'re using sudo, you might have to pass it explicitly, for example "sudo HOST_PWD=$PWD docker compose up".')
            fatal = True
        else:
            logger.debug(f'HOST_PWD={host_pwd}')

        # BUGHOG_VERSION
        if (bughog_version := os.getenv('BUGHOG_VERSION')) in ['', None]:
            logger.fatal('"BUGHOG_VERSION" variable is not set.')
            fatal = True
        else:
            logger.info(f'Starting BugHog with tag "{bughog_version}"')

        return not fatal

    @staticmethod
    def initialize_folders():
        for browser in ['chromium', 'firefox']:
            if not os.path.isfile(f'/app/browser/binaries/{browser}/artisanal/meta.json'):
                with open(f'/app/browser/binaries/{browser}/artisanal/meta.json', 'w') as file:
                    file.write('{}')

    @staticmethod
    def get_database_connection_params() -> DatabaseConnectionParameters:
        required_database_params = [
            'BCI_MONGO_HOST',
            'BCI_MONGO_USERNAME',
            'BCI_MONGO_DATABASE',
            'BCI_MONGO_PASSWORD'
        ]
        missing_database_params = [
            param for param in required_database_params
            if os.getenv(param) in ['', None]]
        if missing_database_params:
            logger.info(f'Could not find database parameters {missing_database_params}, using database container...')
            return container.run()
        else:
            database_params = DatabaseConnectionParameters(
                os.getenv('BCI_MONGO_HOST'),
                os.getenv('BCI_MONGO_USERNAME'),
                os.getenv('BCI_MONGO_PASSWORD'),
                os.getenv('BCI_MONGO_DATABASE')
            )
            logger.info(f'Found database environment variables \'{database_params}\'')
            return database_params

    @staticmethod
    def get_tag() -> str:
        '''
        Returns the Docker image tag of BugHog.
        This should never be empty.
        '''
        assert (bughog_version := os.getenv('BUGHOG_VERSION')) not in ['', None]
        return bughog_version


class Chromium:

    extension_folder = '/app/browser/extensions/chromium'
    repo_to_use = 'online'


class Firefox:

    extension_folder = '/app/browser/extensions/firefox'
    repo_to_use = 'online'


class CustomHTTPHandler(logging.handlers.HTTPHandler):

    def __init__(self, host: str, url: str, method: str = 'GET', secure: bool = False, credentials=None, context=None) -> None:
        super().__init__(host, url, method=method, secure=secure, credentials=credentials, context=context)
        self.hostname = os.getenv('HOSTNAME')

    def mapLogRecord(self, record):
        record_dict = super().mapLogRecord(record)
        record_dict['hostname'] = self.hostname
        return record_dict


class Loggers:

    formatter = logging.Formatter(fmt='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
    memory_handler = logging.handlers.MemoryHandler(capacity=100, flushLevel=logging.ERROR)

    @staticmethod
    def configure_loggers():
        hostname = os.getenv('HOSTNAME')

        # Configure bci_logger
        bci_logger = logging.getLogger('bci')
        bci_logger.setLevel(logging.DEBUG)

        # Configure stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(Loggers.formatter)
        bci_logger.addHandler(stream_handler)

        # Configure file handler
        file_handler = logging.handlers.RotatingFileHandler(f'/app/logs/{hostname}.log', mode='a', backupCount=2)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(Loggers.formatter)
        bci_logger.addHandler(file_handler)

        # Configure http handler for workers
        if hostname != 'bh_core':
            http_handler = CustomHTTPHandler('core:5000', '/api/log/', method='POST', secure=False)
            http_handler.setLevel(logging.INFO)
            http_handler.setFormatter(Loggers.formatter)
            bci_logger.addHandler(http_handler)

        # Configure memory handler
        Loggers.memory_handler.setLevel(logging.INFO)
        buffer_formatter = logging.handlers.BufferingHandler(Loggers.formatter)
        Loggers.memory_handler.setFormatter(buffer_formatter)
        bci_logger.addHandler(Loggers.memory_handler)

        # Log uncaught exceptions
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            bci_logger.critical('Uncaught exception', exc_info=(exc_type, exc_value, exc_traceback))

        sys.excepthook = handle_exception

        bci_logger.debug('Loggers initialized')

    @staticmethod
    def get_formatted_buffer_logs() -> list[str]:
        return [Loggers.formatter.format(record) for record in Loggers.memory_handler.buffer]
