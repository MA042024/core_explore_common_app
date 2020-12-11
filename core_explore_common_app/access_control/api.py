""" Set of functions to define the rules for access control
"""
import logging

from django.contrib.auth.models import User, AnonymousUser

from core_explore_common_app.components.query.models import Query
from core_explore_common_app.settings import CAN_ANONYMOUS_ACCESS_PUBLIC_DOCUMENT
from core_main_app.access_control.exceptions import AccessControlError

from core_explore_common_app.components.abstract_persistent_query.models import (
    AbstractPersistentQuery,
)

logger = logging.getLogger(__name__)


def can_read(func, id_query, user):
    """Can user read

    Args:
        func:
        id_query:
        user:

    Returns:

    """

    if user.is_superuser:
        return func(id_query, user)

    query = func(id_query, user)

    if query.user_id == str(user.id):
        return query
    # user is not owner or document
    raise AccessControlError("The user doesn't have enough rights")


def can_access(func, *args, **kwargs):
    """Can user access the query, only owner and superuser can update the query given as parameter

    Args:
        func:
        *args:
        **kwargs:

    Returns:

    """
    # Get user from parameters
    user = next(
        (
            arg
            for arg in args
            if isinstance(arg, User) or isinstance(arg, AnonymousUser)
        ),
        None,
    )
    # No user, raise ACL error
    if user is None:
        raise AccessControlError(
            "The user doesn't have enough rights to access this query"
        )
    # Superuser can access the query
    if user.is_superuser:
        return func(*args, **kwargs)

    # Get the query from parameters
    query = next((arg for arg in args if isinstance(arg, Query)), None)
    # Check owner of the query
    if query.user_id != str(user.id):
        raise AccessControlError(
            "The user doesn't have enough rights to access this query"
        )
    # Anonymous user cannot create a query if cannot access data
    if (
        isinstance(user, AnonymousUser)
        and not query.id
        and not CAN_ANONYMOUS_ACCESS_PUBLIC_DOCUMENT
    ):
        raise AccessControlError(
            "The user doesn't have enough rights to create a query."
        )

    return func(*args, **kwargs)


def can_read_persistent_query(func, *args, **kwargs):
    """Can user read

    Args:
        func:
        *args:
        **kwargs:

    Returns:

    """
    user = next(
        (
            arg
            for arg in args
            if isinstance(arg, User) or isinstance(arg, AnonymousUser)
        ),
        None,
    )
    if user is None:
        raise AccessControlError(
            "The user doesn't have enough rights to read this query."
        )

    # Anonymous can read when CAN_ANONYMOUS_ACCESS_PUBLIC_DOCUMENT
    if user.is_anonymous:
        if CAN_ANONYMOUS_ACCESS_PUBLIC_DOCUMENT:
            return func(*args, **kwargs)
        else:
            raise AccessControlError(
                "The user doesn't have enough rights to read this query."
            )

    # Superuser and user can always read queries
    return func(*args, **kwargs)


def can_write_persistent_query(func, *args, **kwargs):
    """Can user read

    Args:
        func:
        *args:
        **kwargs:

    Returns:

    """
    user = next(
        (
            arg
            for arg in args
            if isinstance(arg, User) or isinstance(arg, AnonymousUser)
        ),
        None,
    )
    if user is None:
        raise AccessControlError(
            "The user doesn't have enough rights to access this query."
        )
    # Superuser can create and update any query
    if user.is_superuser:
        return func(*args, **kwargs)

    query = next(
        (arg for arg in args if isinstance(arg, AbstractPersistentQuery)),
        None,
    )

    # Anonymous can only create new query
    if user.is_anonymous:
        if query.id is None and CAN_ANONYMOUS_ACCESS_PUBLIC_DOCUMENT:
            return func(*args, **kwargs)
        else:
            raise AccessControlError(
                "The user doesn't have enough rights to access this query."
            )

    # Owner can create and update own queries
    if query.user_id == str(user.id):
        return func(*args, **kwargs)

    # Non-Owner
    raise AccessControlError(
        "The user doesn't have enough rights to access this query."
    )
