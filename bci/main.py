import logging

import bci.browser.binary.factory as binary_factory
from bci.analysis.plot_factory import PlotFactory
from bci.browser.support import get_chromium_support, get_firefox_support
from bci.configuration import Global, Loggers
from bci.database.mongo.mongodb import MongoDB
from bci.evaluations.logic import EvaluationParameters, PlotParameters
from bci.master import Master

logger = logging.getLogger(__name__)


class Main:
    loggers = None
    master = None

    @staticmethod
    def initialize():
        Main.loggers = Loggers()
        Main.loggers.configure_loggers()
        if Global.check_required_env_parameters():
            Main.master = Master()

    @staticmethod
    def is_ready() -> bool:
        return Main.master is not None

    @staticmethod
    def run(params: EvaluationParameters):
        Main.master.run(params)

    @staticmethod
    def stop_gracefully():
        Main.master.activate_stop_gracefully()

    @staticmethod
    def stop_forcefully():
        Main.master.activate_stop_forcefully()

    @staticmethod
    def get_state() -> str:
        return Main.master.state

    @staticmethod
    def connect_to_database():
        return Main.master.connect_to_database()

    @staticmethod
    def get_logs() -> list[str]:
        return list(
            map(
                lambda x: Main.format_to_user_log(x.__dict__),
                Loggers.memory_handler.buffer,
            )
        )

    @staticmethod
    def format_to_user_log(log: dict) -> str:
        return f'[{log["asctime"]}] [{log["levelname"]}] {log["name"]}: {log["msg"]}'

    @staticmethod
    def get_database_info() -> dict:
        return MongoDB().get_info()

    @staticmethod
    def get_browser_support() -> list[dict]:
        return [get_chromium_support(), get_firefox_support()]

    @staticmethod
    def list_downloaded_binaries(browser):
        return binary_factory.list_downloaded_binaries(browser)

    @staticmethod
    def list_artisanal_binaries(browser):
        return binary_factory.list_artisanal_binaries(browser)

    @staticmethod
    def update_artisanal_binaries(browser):
        return binary_factory.update_artisanal_binaries(browser)

    @staticmethod
    def download_online_binary(browser, rev_number):
        binary_factory.download_online_binary(browser, rev_number)

    @staticmethod
    def get_mech_groups_of_evaluation_framework(evaluation_name: str, project) -> list[tuple[str, bool]]:
        return Main.master.evaluation_framework.get_mech_groups(project)

    @staticmethod
    def get_projects_of_custom_framework() -> list[str]:
        return Main.master.evaluation_framework.get_projects()

    @staticmethod
    def convert_to_plotparams(data: dict) -> PlotParameters:
        if data.get("lower_version", None) and data.get("upper_version", None):
            major_version_range = (data["lower_version"], data["upper_version"])
        else:
            major_version_range = None
        if data.get("lower_revision_nb", None) and data.get("upper_revision_nb", None):
            revision_number_range = (
                data["lower_revision_nb"],
                data["upper_revision_nb"],
            )
        else:
            revision_number_range = None
        return PlotParameters(
            data.get("plot_mech_group"),
            data.get("target_mech_id"),
            data.get("browser_name"),
            data.get("db_collection"),
            major_version_range=major_version_range,
            revision_number_range=revision_number_range,
            browser_config=data.get("browser_setting", "default"),
            extensions=data.get("extensions", []),
            cli_options=data.get("cli_options", []),
            dirty_allowed=data.get("dirty_allowed", True),
            target_cookie_name=None
            if data.get("check_for") == "request"
            else data.get("target_cookie_name", "generic"),
        )

    @staticmethod
    def get_data_sources(data: dict):
        params = Main.convert_to_plotparams(data)

        if PlotFactory.validate_params(params):
            return None, None

        return \
            PlotFactory.get_plot_revision_data(params, MongoDB()), \
            PlotFactory.get_plot_version_data(params, MongoDB())

    @staticmethod
    def get_poc(project: str, poc: str) -> dict:
        return Main.master.evaluation_framework.get_poc_structure(project, poc)

    @staticmethod
    def get_poc_file(project: str, poc: str, domain: str, path: str, file: str) -> str:
        return Main.master.evaluation_framework.get_poc_file(project, poc, domain, path, file)

    @staticmethod
    def update_poc_file(project: str, poc: str, domain: str, path: str, file: str, content: str) -> bool:
        logger.debug(f'Updating file {file} of project {project} and poc {poc}')
        return Main.master.evaluation_framework.update_poc_file(project, poc, domain, path, file, content)

    @staticmethod
    def create_empty_poc(project: str, poc_name: str) -> bool:
        return Main.master.evaluation_framework.create_empty_poc(project, poc_name)

    @staticmethod
    def get_available_domains() -> list[str]:
        return Global.get_available_domains()

    @staticmethod
    def add_page(project: str, poc: str, domain: str, path: str, file_type: str) -> bool:
        return Main.master.evaluation_framework.add_page(project, poc, domain, path, file_type)

    @staticmethod
    def sigint_handler(signum, frame):
        return Main.master.stop_bughog()
