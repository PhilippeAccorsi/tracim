from hapic.ext.pyramid import PyramidContext
from pyramid.config import Configurator

from tracim_backend.app_models.applications import TracimApplicationInContext
from tracim_backend.app_models.contents import content_status_list
from tracim_backend.applications.content_file.file_controller import FileController
from tracim_backend.config import CFG
from tracim_backend.lib.utils.app import TracimApplication


class ContentFileApp(TracimApplication):
    def create_app(self, app_config: CFG) -> TracimApplicationInContext:
        _file = TracimApplicationInContext(
            label="Files",
            slug="contents/file",
            fa_icon="paperclip",
            is_active=True,
            config={},
            main_route="/ui/workspaces/{workspace_id}/contents?type=file",
            app_config=app_config,
        )
        _file.add_content_type(
            slug="file",
            label="File",
            creation_label="Upload a file",
            available_statuses=content_status_list.get_all(),
        )
        return _file

    def load_config(self, app_config: CFG) -> CFG:
        return app_config

    def check_config(self, app_config: CFG) -> CFG:
        return app_config

    def import_controllers(
        self,
        configurator: Configurator,
        app_config: CFG,
        route_prefix: str,
        context: PyramidContext,
    ) -> Configurator:
        file_controller = FileController()
        configurator.include(file_controller.bind, route_prefix=route_prefix)
        return configurator


application = ContentFileApp()