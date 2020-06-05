import abc
import contextlib
from datetime import datetime
import threading
import typing

from sqlalchemy import event as sqlalchemy_event
from sqlalchemy import inspect
from sqlalchemy import null
from sqlalchemy.orm import joinedload

from tracim_backend.app_models.contents import COMMENT_TYPE
from tracim_backend.app_models.contents import FILE_TYPE
from tracim_backend.app_models.contents import FOLDER_TYPE
from tracim_backend.app_models.contents import HTML_DOCUMENTS_TYPE
from tracim_backend.app_models.contents import THREAD_TYPE
from tracim_backend.config import CFG
from tracim_backend.exceptions import UserDoesNotExist
from tracim_backend.lib.core.content import ContentApi
from tracim_backend.lib.core.live_messages import LiveMessagesLib
from tracim_backend.lib.core.plugins import hookimpl
from tracim_backend.lib.core.user import UserApi
from tracim_backend.lib.core.userworkspace import RoleApi
from tracim_backend.lib.core.workspace import WorkspaceApi
from tracim_backend.lib.rq import get_redis_connection
from tracim_backend.lib.rq import get_rq_queue
from tracim_backend.lib.rq import worker_session
from tracim_backend.lib.utils.logger import logger
from tracim_backend.lib.utils.request import TracimRequest
from tracim_backend.models.auth import Profile
from tracim_backend.models.auth import User
from tracim_backend.models.data import ActionDescription
from tracim_backend.models.data import Content
from tracim_backend.models.data import ContentRevisionRO
from tracim_backend.models.data import UserRoleInWorkspace
from tracim_backend.models.data import Workspace
from tracim_backend.models.event import EntityType
from tracim_backend.models.event import Event
from tracim_backend.models.event import Message
from tracim_backend.models.event import OperationType
from tracim_backend.models.event import ReadStatus
from tracim_backend.models.tracim_session import TracimSession
from tracim_backend.views.core_api.schemas import CommentSchema
from tracim_backend.views.core_api.schemas import FileContentSchema
from tracim_backend.views.core_api.schemas import EventSchema
from tracim_backend.views.core_api.schemas import TextBasedContentSchema
from tracim_backend.views.core_api.schemas import UserSchema
from tracim_backend.views.core_api.schemas import WorkspaceMemberDigestSchema
from tracim_backend.views.core_api.schemas import WorkspaceSchema

_USER_FIELD = "user"
_AUTHOR_FIELD = "author"
_WORKSPACE_FIELD = "workspace"
_CONTENT_FIELD = "content"
_MEMBER_FIELD = "member"


RQ_QUEUE_NAME = "event"


class EventApi:
    """Api to query event & messages"""

    def __init__(self, current_user: User, session: TracimSession, config: CFG) -> None:
        self._current_user = current_user
        self._session = session
        self._config = config

    def get_messages_for_user(self, user_id: int, read_status: ReadStatus) -> typing.List[Message]:
        query = (
            self._session.query(Message)
            .filter(Message.receiver_id == user_id)
            .options(joinedload(Message.event))
        )
        if read_status == ReadStatus.READ:
            query = query.filter(Message.read != null())
        elif read_status == ReadStatus.UNREAD:
            query = query.filter(Message.read == null())
        else:
            # ALL doesn't need any filtering an is the only other handled case
            assert read_status == ReadStatus.ALL
        return query.all()


class EventBuilder:
    """Create Event objects from the database crud hooks."""

    _user_schema = UserSchema()
    _workspace_schema = WorkspaceSchema()
    _content_schemas = {
        COMMENT_TYPE: CommentSchema(),
        HTML_DOCUMENTS_TYPE: TextBasedContentSchema(),
        FILE_TYPE: FileContentSchema(),
        FOLDER_TYPE: TextBasedContentSchema(),
        THREAD_TYPE: TextBasedContentSchema(),
    }
    _event_schema = EventSchema()
    _workspace_user_role_schema = WorkspaceMemberDigestSchema()

    def __init__(self, config: CFG) -> None:
        self._config = config
        # NOTE S.G. 2020-06-04: need thread local storage as EventBuilder()
        # is created only once/wsgi application
        self._thread_local = threading.local()

    @property
    def _current_user(self) -> typing.Optional[User]:
        try:
            return self._thread_local.current_user
        except AttributeError:
            return None

    @hookimpl
    def on_current_user_set(self, user: User) -> None:
        self._thread_local.current_user = user

    @hookimpl
    def on_request_session_created(self, request: TracimRequest, session: TracimSession) -> None:
        commit_event = "after_flush"
        if self._config.JOBS__PROCESSING_MODE == self._config.CST.ASYNC:
            # We need after commit event when processing in async
            # Otherwise we can't be sure that events will be visible
            # to the RQ worker when it queries the database.
            commit_event = "after_commit"

        sqlalchemy_event.listen(session, commit_event, self._publish_events)
        sqlalchemy_event.listen(
            session,
            "after_soft_rollback",
            lambda session, previous_transaction: self._clear_pending_events,
        )
        self._thread_local.pending_events = []

    @hookimpl
    def on_request_finished(self) -> None:
        self._thread_local.current_user = None

    # User events
    @hookimpl
    def on_user_created(self, user: User, db_session: TracimSession) -> None:
        self._create_user_event(OperationType.CREATED, user, db_session)

    @hookimpl
    def on_user_modified(self, user: User, db_session: TracimSession) -> None:
        if self._has_just_been_deleted(user):
            self._create_user_event(OperationType.DELETED, user, db_session)
        elif self._has_just_been_undeleted(user):
            self._create_user_event(OperationType.UNDELETED, user, db_session)
        else:
            self._create_user_event(OperationType.MODIFIED, user, db_session)

    def _create_user_event(
        self, operation: OperationType, user: User, db_session: TracimSession
    ) -> None:
        user_api = UserApi(self._current_user, db_session, self._config, show_deleted=True)
        fields = {
            _AUTHOR_FIELD: self._user_schema.dump(
                user_api.get_user_with_context(self._current_user)
            ).data,
            _USER_FIELD: self._user_schema.dump(user_api.get_user_with_context(user)).data,
        }
        event = Event(entity_type=EntityType.USER, operation=operation, fields=fields)
        self._add_event(event, db_session)

    # Workspace events
    @hookimpl
    def on_workspace_created(self, workspace: Workspace, db_session: TracimSession) -> None:
        self._create_workspace_event(OperationType.CREATED, workspace, db_session)

    @hookimpl
    def on_workspace_modified(self, workspace: Workspace, db_session: TracimSession) -> None:
        if self._has_just_been_deleted(workspace):
            self._create_workspace_event(OperationType.DELETED, workspace, db_session)
        elif self._has_just_been_undeleted(workspace):
            self._create_workspace_event(OperationType.UNDELETED, workspace, db_session)
        else:
            self._create_workspace_event(OperationType.MODIFIED, workspace, db_session)

    def _create_workspace_event(
        self, operation: OperationType, workspace: Workspace, db_session: TracimSession
    ) -> None:
        api = WorkspaceApi(db_session, self._current_user, self._config)
        user_api = UserApi(self._current_user, db_session, self._config, show_deleted=True)
        workspace_in_context = api.get_workspace_with_context(workspace)
        fields = {
            _AUTHOR_FIELD: self._user_schema.dump(
                user_api.get_user_with_context(self._current_user)
            ).data,
            _WORKSPACE_FIELD: self._workspace_schema.dump(workspace_in_context).data,
        }
        event = Event(entity_type=EntityType.WORKSPACE, operation=operation, fields=fields)
        self._add_event(event, db_session)

    # Content events
    @hookimpl
    def on_content_created(self, content: Content, db_session: TracimSession) -> None:
        self._create_content_event(OperationType.CREATED, content, db_session)

    @hookimpl
    def on_content_modified(self, content: Content, db_session: TracimSession) -> None:
        if content.current_revision.revision_type == ActionDescription.DELETION:
            self._create_content_event(OperationType.DELETED, content, db_session)
        elif content.current_revision.revision_type == ActionDescription.UNDELETION:
            self._create_content_event(OperationType.UNDELETED, content, db_session)
        else:
            self._create_content_event(OperationType.MODIFIED, content, db_session)

    def _create_content_event(
        self, operation: OperationType, content: Content, db_session: TracimSession
    ) -> None:
        content_api = ContentApi(db_session, self._current_user, self._config)
        content_in_context = content_api.get_content_in_context(content)
        content_dict = self._content_schemas[content.type].dump(content_in_context).data

        workspace_api = WorkspaceApi(db_session, self._current_user, self._config)
        workspace_in_context = workspace_api.get_workspace_with_context(
            workspace_api.get_one(content_in_context.workspace.workspace_id)
        )
        user_api = UserApi(self._current_user, db_session, self._config, show_deleted=True)
        fields = {
            _AUTHOR_FIELD: self._user_schema.dump(
                user_api.get_user_with_context(self._current_user)
            ).data,
            _CONTENT_FIELD: content_dict,
            _WORKSPACE_FIELD: self._workspace_schema.dump(workspace_in_context).data,
        }
        event = Event(
            entity_type=EntityType.CONTENT,
            operation=operation,
            fields=fields,
            entity_subtype=content.type,
        )
        self._add_event(event, db_session)

    # UserRoleInWorkspace events
    @hookimpl
    def on_user_role_in_workspace_created(
        self, role: UserRoleInWorkspace, db_session: TracimSession
    ) -> None:
        self._create_role_event(OperationType.CREATED, role, db_session)

    @hookimpl
    def on_user_role_in_workspace_modified(
        self, role: UserRoleInWorkspace, db_session: TracimSession
    ) -> None:
        self._create_role_event(OperationType.MODIFIED, role, db_session)

    @hookimpl
    def on_user_role_in_workspace_deleted(
        self, role: UserRoleInWorkspace, db_session: TracimSession
    ) -> None:
        self._create_role_event(OperationType.DELETED, role, db_session)

    def _create_role_event(
        self, operation: OperationType, role: UserRoleInWorkspace, db_session: TracimSession
    ) -> None:
        workspace_api = WorkspaceApi(db_session, self._current_user, self._config)
        workspace_in_context = workspace_api.get_workspace_with_context(role.workspace)
        user_api = UserApi(self._current_user, db_session, self._config, show_deleted=True)
        role_api = RoleApi(current_user=self._current_user, session=db_session, config=self._config)
        try:
            user_field = self._user_schema.dump(
                user_api.get_user_with_context(user_api.get_one(role.user_id))
            ).data
        except UserDoesNotExist:
            # It is possible to have an already deleted user when deleting his roles.
            user_field = None

        role_in_context = role_api.get_user_role_workspace_with_context(role)
        fields = {
            _AUTHOR_FIELD: self._user_schema.dump(
                user_api.get_user_with_context(self._current_user)
            ).data,
            _USER_FIELD: user_field,
            _WORKSPACE_FIELD: self._workspace_schema.dump(workspace_in_context).data,
            _MEMBER_FIELD: self._workspace_user_role_schema.dump(role_in_context).data,
        }
        event = Event(entity_type=EntityType.WORKSPACE_MEMBER, operation=operation, fields=fields)
        self._add_event(event, db_session)

    def _add_event(self, event: Event, db_session: TracimSession) -> None:
        db_session.add(event)
        self._thread_local.pending_events.append(event)

    def _publish_events(self, db_session: TracimSession, flush_context=None) -> None:
        if self._config.JOBS__PROCESSING_MODE == self._config.CST.ASYNC:
            message_builder = AsyncLiveMessageBuilder(
                config=self._config
            )  # type: BaseLiveMessageBuilder
        else:
            message_builder = SyncLiveMessageBuilder(session=db_session, config=self._config)

        # We only publish events that have an event_id from the DB.
        # we can have `new` events here as we add events in the session
        # in a `after_flush` sqlalchemy event and _publish_events is also
        # called during the same `after_flush` event.
        publishable_events = []
        not_publishable_events = []
        for event in self._thread_local.pending_events:
            if event.event_id:
                publishable_events.append(event)
            else:
                not_publishable_events.append(event)
        for event in publishable_events:
            message_builder.publish_messages_for_event(event.event_id)
        self._thread_local.pending_events = not_publishable_events

    def _clear_pending_events(self) -> None:
        self._thread_local.pending_events.clear()

    def _has_just_been_deleted(self, obj: typing.Union[User, Workspace, ContentRevisionRO]) -> bool:
        """Check that an object has been deleted since it has been queried from database."""
        if obj.is_deleted:
            history = inspect(obj).attrs.is_deleted.history
            was_changed = not history.unchanged and (history.deleted or history.added)
            return was_changed
        return False

    def _has_just_been_undeleted(
        self, obj: typing.Union[User, Workspace, ContentRevisionRO]
    ) -> bool:
        """Check whether an object has been undeleted since queried from database."""
        if not obj.is_deleted:
            history = inspect(obj).attrs.is_deleted.history
            was_changed = not history.unchanged and (history.deleted or history.added)
            return was_changed
        return False


class BaseLiveMessageBuilder(abc.ABC):
    """"Base class for message building with most implementation."""

    _event_schema = EventSchema()

    def __init__(self, config: CFG) -> None:
        self._config = config

    @contextlib.contextmanager
    @abc.abstractmethod
    def session(self) -> typing.Generator[TracimSession, None, None]:
        pass

    @abc.abstractmethod
    def publish_messages_for_event(self, event_id: int) -> None:
        pass

    def _publish_messages_for_event(self, event_id: int) -> None:
        with self.session() as session:
            event = session.query(Event).filter(Event.event_id == event_id).one()
            if event.entity_type == EntityType.USER:
                receiver_ids = self._get_user_event_receiver_ids(event, session)
            elif event.entity_type == EntityType.WORKSPACE:
                receiver_ids = self._get_workspace_event_receiver_ids(event, session)
            elif event.entity_type == EntityType.CONTENT:
                receiver_ids = self._get_workspace_event_receiver_ids(event, session)
            elif event.entity_type == EntityType.WORKSPACE_MEMBER:
                receiver_ids = self._get_workspace_event_receiver_ids(event, session)

            messages = [
                Message(
                    receiver_id=receiver_id,
                    event=event,
                    event_id=event.event_id,
                    sent=datetime.utcnow(),
                )
                for receiver_id in receiver_ids
            ]
            session.add_all(messages)
        live_message_lib = LiveMessagesLib(self._config)
        for message in messages:
            live_message_lib.publish_message_to_user(message)

    def _get_user_event_receiver_ids(self, event: Event, session: TracimSession) -> typing.Set[int]:
        user_api = UserApi(current_user=None, session=session, config=self._config)
        receiver_ids = set(user_api.get_user_ids_from_profile(Profile.ADMIN))
        if event.user:
            receiver_ids.add(event.user["user_id"])
        return receiver_ids

    def _get_workspace_event_receiver_ids(
        self, event: Event, session: TracimSession,
    ) -> typing.Set[int]:
        user_api = UserApi(current_user=None, session=session, config=self._config)
        administrators = user_api.get_user_ids_from_profile(Profile.ADMIN)
        role_api = RoleApi(current_user=None, session=session, config=self._config)
        workspace_members = role_api.get_workspace_member_ids(event.workspace["workspace_id"])
        return set(administrators + workspace_members)


class AsyncLiveMessageBuilder(BaseLiveMessageBuilder):
    """"Live message building + sending executed in a RQ job."""

    @contextlib.contextmanager
    def session(self) -> typing.Generator[TracimSession, None, None]:
        with worker_session() as session:
            yield session

    def publish_messages_for_event(self, event_id: int) -> None:
        redis_connection = get_redis_connection(self._config)
        queue = get_rq_queue(redis_connection, RQ_QUEUE_NAME)
        logger.debug(
            self,
            "publish event(id={}) asynchronously to RQ queue {}".format(event_id, RQ_QUEUE_NAME),
        )
        queue.enqueue(self._publish_messages_for_event, event_id)


class SyncLiveMessageBuilder(BaseLiveMessageBuilder):
    """"Live message building + sending executed in tracim web application."""

    def __init__(self, session: TracimSession, config: CFG) -> None:
        super().__init__(config)
        self._session = session

    @contextlib.contextmanager
    def session(self) -> typing.Generator[TracimSession, None, None]:
        yield self._session

    def publish_messages_for_event(self, event_id: int) -> None:
        logger.debug(self, "publish event(id={}) synchronously".format(event_id))
        self._publish_messages_for_event(event_id)
