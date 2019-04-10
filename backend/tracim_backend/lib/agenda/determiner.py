# coding: utf-8
import typing

from tracim_backend.lib.agenda.utils import DavAuthorization
from tracim_backend.lib.utils.logger import logger

if typing.TYPE_CHECKING:
    from tracim_backend import TracimRequest


CALDAV_READ_METHODS = [
    'GET',
    'HEAD',
    'OPTIONS',
    'PROPFIND',
    'LOCK',
    'UNLOCK',
    'REPORT',
]
CALDAV_WRITE_METHODS = [
    'PUT',
    'POST',
    'PROPPATCH',
    'COPY',
    'MOVE',
    'MKCOL',
    'MKAGENDA',
]
CALDAV_MANAGER_METHODS = [
    'DELETE',
    'MOVE',
]


class CaldavAuthorizationDeterminer(object):
    def determine_requested_mode(self, request: 'TracimRequest') -> DavAuthorization:
        if request.method in CALDAV_READ_METHODS:
            return DavAuthorization.READ
        elif request.method in CALDAV_WRITE_METHODS:
            return DavAuthorization.WRITE
        elif request.method in CALDAV_MANAGER_METHODS:
            return DavAuthorization.MANAGER
        else:
            logger.warning(
                self,
                'Unknown http method "{}" authorization will be MANAGER'.format(request.method),
            )
            return DavAuthorization.MANAGER
