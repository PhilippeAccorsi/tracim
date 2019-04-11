from time import sleep

from parameterized import parameterized
import pytest
import requests
import transaction
from requests.exceptions import ConnectionError

from tracim_backend.lib.core.group import GroupApi
from tracim_backend.lib.core.user import UserApi
from tracim_backend.lib.core.userworkspace import RoleApi
from tracim_backend.lib.core.workspace import WorkspaceApi
from tracim_backend.models.auth import User
from tracim_backend.models.data import UserRoleInWorkspace
from tracim_backend.models.setup_models import get_tm_session
from tracim_backend.tests import CaldavRadicaleProxyFunctionalTest
from tracim_backend.tests import FunctionalTest

VALID_CALDAV_BODY_PUT_EVENT = """
BEGIN:VCALENDAR
PRODID:-//Mozilla.org/NONSGML Mozilla Calendar V1.1//EN
VERSION:2.0
X-WR-CALNAME:test
X-WR-TIMEZONE:Europe/Paris
BEGIN:VEVENT
CREATED:20190308T133249Z
LAST-MODIFIED:20190308T133251Z
DTSTAMP:20190308T133251Z
UID:6028cb45-10f3-4f95-8989-5fb6436a0243
SUMMARY:Nouvel évènement
DTSTART;VALUE=DATE:20190306
DTEND;VALUE=DATE:20190307
TRANSP:TRANSPARENT
END:VEVENT
END:VCALENDAR
"""
CALDAV_URL_FOR_TEST = ('http://localhost:5232')

class TestCaldavRadicaleProxyEndpoints(CaldavRadicaleProxyFunctionalTest):

    @pytest.mark.skip('This Need sleep method actually')
    def test_radicale_available(self) -> None:
        try:
            result = requests.get(CALDAV_URL_FOR_TEST, timeout=3)
        except ConnectionError as exc:
            # we do retry just one time in order to be sure server was
            # correctly setup
            sleep(0.1)
            result = requests.get(CALDAV_URL_FOR_TEST, timeout=3)
        assert result.status_code == 200

    def test_proxy_user_agenda__ok__nominal_case(self) -> None:
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User) \
            .filter(User.email == 'admin@admin.admin') \
            .one()
        uapi = UserApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        gapi = GroupApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        groups = [gapi.get_one_with_name('users')]
        user = uapi.create_user('test@test.test', password='test@test.test', do_save=True, do_notify=False, groups=groups)  # nopep8
        transaction.commit()
        self.testapp.authorization = (
            'Basic',
            (
                'test@test.test',
                'test@test.test'
            )
        )
        result = self.testapp.get('/agenda/user/{}/'.format(user.user_id), status=404)
        event = VALID_CALDAV_BODY_PUT_EVENT
        result = self.testapp.put('/agenda/user/{}/'.format(user.user_id), event, content_type='text/calendar', status=201)
        result = self.testapp.get('/agenda/user/{}/'.format(user.user_id), status=200)
        result = self.testapp.delete('/agenda/user/{}/'.format(user.user_id), status=200)

    @parameterized.expand([
        #  sub_items label
        ('2d89ab53-e66f-6a48-634a-f112fb27b5e8'), # thunderbird-like
        ('c584046fa2a358f646aa18e94f61a011f32e7d14a5735cd80bceaca8351d8fa4'), # caldavzap-like
    ])
    def test_proxy_user_agenda__ok__on_sub_items(self, sub_item_label) -> None:
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User) \
            .filter(User.email == 'admin@admin.admin') \
            .one()
        uapi = UserApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        gapi = GroupApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        groups = [gapi.get_one_with_name('users')]
        user = uapi.create_user('test@test.test', password='test@test.test', do_save=True, do_notify=False, groups=groups)  # nopep8
        transaction.commit()
        self.testapp.authorization = (
            'Basic',
            (
                'test@test.test',
                'test@test.test'
            )
        )
        result = self.testapp.get('/agenda/user/{}/{}'.format(user.user_id, sub_item_label), status=404)
        event = VALID_CALDAV_BODY_PUT_EVENT
        result = self.testapp.put('/agenda/user/{}/'.format(user.user_id), event, content_type='text/calendar', status=201)
        result = self.testapp.put('/agenda/user/{}/{}.ics'.format(user.user_id, sub_item_label), event, content_type='text/calendar', status='*')
        result = self.testapp.get('/agenda/user/{}/{}.ics'.format(user.user_id, sub_item_label), status=200)
        result = self.testapp.delete('/agenda/user/{}/{}.ics'.format(user.user_id, sub_item_label), status=200)
        result = self.testapp.delete('/agenda/user/{}/'.format(user.user_id, sub_item_label), status=200)

    def test_proxy_user_agenda__err__other_user_agenda(self) -> None:
        dbsession = get_tm_session(self.session_factory,
                                   transaction.manager)
        admin = dbsession.query(User) \
            .filter(User.email == 'admin@admin.admin') \
            .one()
        uapi = UserApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        gapi = GroupApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        groups = [gapi.get_one_with_name('users')]
        user = uapi.create_user('test@test.test', password='test@test.test',
                                do_save=True, do_notify=False,
                                groups=groups)  # nopep8
        user2 = uapi.create_user('test2@test2.test2', password='test@test.test',
                                do_save=True, do_notify=False,
                                groups=groups)  # nopep8
        transaction.commit()
        self.testapp.authorization = (
            'Basic',
            (
                'test@test.test',
                'test@test.test'
            )
        )
        result = self.testapp.get(
            '/agenda/user/{}/'.format(user2.user_id), status=403)
        assert result.json_body['code'] == 5001

    def test_proxy_workspace_agenda__ok__nominal_case(self) -> None:
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User) \
            .filter(User.email == 'admin@admin.admin') \
            .one()
        uapi = UserApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        gapi = GroupApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        groups = [gapi.get_one_with_name('users')]
        user = uapi.create_user('test@test.test', password='test@test.test', do_save=True, do_notify=False, groups=groups)  # nopep8
        workspace_api = WorkspaceApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
            show_deleted=True,
        )
        workspace = workspace_api.create_workspace('test', save_now=True)  # nopep8
        workspace.agenda_enabled=True
        rapi = RoleApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        rapi.create_one(user, workspace, UserRoleInWorkspace.CONTENT_MANAGER, False)  # nopep8
        transaction.commit()
        self.testapp.authorization = (
            'Basic',
            (
                'test@test.test',
                'test@test.test'
            )
        )
        result = self.testapp.get('/agenda/workspace/{}/'.format(workspace.workspace_id), status=404)
        event = VALID_CALDAV_BODY_PUT_EVENT
        result = self.testapp.put('/agenda/workspace/{}/'.format(workspace.workspace_id), event, content_type='text/agenda', status=201)
        result = self.testapp.get('/agenda/workspace/{}/'.format(workspace.workspace_id), status=200)
        result = self.testapp.delete('/agenda/workspace/{}/'.format(workspace.workspace_id), status=200)

    def test_proxy_workspace_agenda__err__other_workspace_agenda(self) -> None:
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User) \
            .filter(User.email == 'admin@admin.admin') \
            .one()
        uapi = UserApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        gapi = GroupApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        groups = [gapi.get_one_with_name('users')]
        user = uapi.create_user('test@test.test', password='test@test.test',
                                do_save=True, do_notify=False,
                                groups=groups)  # nopep8
        workspace_api = WorkspaceApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
            show_deleted=True,
        )
        workspace = workspace_api.create_workspace('test',
                                                   save_now=True)  # nopep8
        transaction.commit()
        self.testapp.authorization = (
            'Basic',
            (
                'test@test.test',
                'test@test.test'
            )
        )
        result = self.testapp.get(
            '/agenda/workspace/{}/'.format(workspace.workspace_id),
            status=403)
        assert result.json_body['code'] == 5001

class TestAgendaApi(FunctionalTest):
    config_section = 'functional_caldav_radicale_proxy_test'

    def test_proxy_user_agenda__ok__nominal_case(self) -> None:
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User) \
            .filter(User.email == 'admin@admin.admin') \
            .one()
        uapi = UserApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        gapi = GroupApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        groups = [gapi.get_one_with_name('users')]
        user = uapi.create_user('test@test.test', password='test@test.test', do_save=True, do_notify=False, groups=groups)  # nopep8
        workspace_api = WorkspaceApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
            show_deleted=True,
        )
        workspace = workspace_api.create_workspace('wp1', save_now=True)  # nopep8
        workspace.agenda_enabled = True
        workspace2 = workspace_api.create_workspace('wp2', save_now=True)  # nopep8
        workspace2.agenda_enabled = True
        workspace3 = workspace_api.create_workspace('wp3', save_now=True)  # nopep8
        workspace3.agenda_enabled = False
        secret_workspace = workspace_api.create_workspace('secret', save_now=True)  # nopep8
        secret_workspace.agenda_enabled = True
        rapi = RoleApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        rapi.create_one(user, workspace, UserRoleInWorkspace.CONTRIBUTOR, False)  # nopep8
        rapi.create_one(user, workspace2, UserRoleInWorkspace.READER, False)  # nopep8
        rapi.create_one(user, workspace3, UserRoleInWorkspace.READER, False)  # nopep8
        transaction.commit()
        self.testapp.authorization = (
            'Basic',
            (
                'test@test.test',
                'test@test.test'
            )
        )
        result = self.testapp.get('/api/v2/users/{}/agenda'.format(user.user_id), status=200)
        agendas = result.json_body
        assert len(result.json_body) == 3
        agenda = result.json_body[0]
        assert agenda['agenda_url'] == 'http://localhost:6543/agenda/user/{}/'.format(user.user_id)
        assert agenda['with_credentials'] == True
        agenda = result.json_body[1]
        assert agenda['agenda_url'] == 'http://localhost:6543/agenda/workspace/{}/'.format(workspace.workspace_id)
        assert agenda['with_credentials'] == True
        agenda = result.json_body[2]
        assert agenda['agenda_url'] == 'http://localhost:6543/agenda/workspace/{}/'.format(workspace2.workspace_id)
        assert agenda['with_credentials'] == True



    def test_proxy_user_agenda__ok__workspace_filter(self) -> None:
        dbsession = get_tm_session(self.session_factory, transaction.manager)
        admin = dbsession.query(User) \
            .filter(User.email == 'admin@admin.admin') \
            .one()
        uapi = UserApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        gapi = GroupApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        groups = [gapi.get_one_with_name('users')]
        user = uapi.create_user('test@test.test', password='test@test.test', do_save=True, do_notify=False, groups=groups)  # nopep8
        workspace_api = WorkspaceApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
            show_deleted=True,
        )
        workspace = workspace_api.create_workspace('wp1', save_now=True)  # nopep8
        workspace.agenda_enabled = True
        workspace2 = workspace_api.create_workspace('wp2', save_now=True)  # nopep8
        workspace2.agenda_enabled = True
        workspace3 = workspace_api.create_workspace('wp3', save_now=True)  # nopep8
        workspace3.agenda_enabled = True
        rapi = RoleApi(
            current_user=admin,
            session=dbsession,
            config=self.app_config,
        )
        rapi.create_one(user, workspace, UserRoleInWorkspace.CONTRIBUTOR, False)  # nopep8
        rapi.create_one(user, workspace2, UserRoleInWorkspace.READER, False)  # nopep8
        rapi.create_one(user, workspace3, UserRoleInWorkspace.READER, False)  # nopep8
        transaction.commit()
        self.testapp.authorization = (
            'Basic',
            (
                'test@test.test',
                'test@test.test'
            )
        )
        params = {
            'workspace_ids': '{},{}'.format(workspace.workspace_id, workspace3.workspace_id),
            'agenda_types': 'workspace'
        }
        result = self.testapp.get('/api/v2/users/{}/agenda'.format(user.user_id), params=params, status=200)
        agendas = result.json_body
        assert len(result.json_body) == 2
        agenda = result.json_body[0]
        assert agenda['agenda_url'] == 'http://localhost:6543/agenda/workspace/{}/'.format(workspace.workspace_id)
        assert agenda['with_credentials'] == True
        agenda = result.json_body[1]
        assert agenda['agenda_url'] == 'http://localhost:6543/agenda/workspace/{}/'.format(workspace3.workspace_id)
        assert agenda['with_credentials'] == True
