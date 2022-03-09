import logging
from copy import copy
from typing import List, Optional

from brewtils.models import Event, Events, Operation
from marshmallow import ValidationError

from beer_garden import config
from beer_garden.db.mongo.models import Garden, RemoteUser, User
from beer_garden.events import publish

logger = logging.getLogger(__name__)


def create_user(**kwargs) -> User:
    """Creates a User using the provided kwargs. The created user is saved to the
    database and returned.

    Args:
        **kwargs: Keyword arguments accepted by the User __init__

    Returns:
        User: The created User instance
    """
    user = User(**kwargs)

    if user.password:
        user.set_password(user.password)

    user.save()

    return user


def update_user(user: User, hashed_password: Optional[str] = None, **kwargs) -> User:
    """Updates the provided User by setting its attributes to those provided by kwargs.
    The updated user object is then saved to the database and returned.

    Args:
        user: The User instance to be updated
        hashed_password: A pre-hashed password that should be stored as is. This will
            override a password kwarg if one is supplied.
        **kwargs: Keyword arguments corresponding to User model attributes

    Returns:
        User: the updated User instance
    """
    for key, value in kwargs.items():
        if key == "password" and hashed_password is None:
            user.set_password(value)
        else:
            setattr(user, key, value)

    if hashed_password:
        user.password = hashed_password

    user.save()
    _publish_user_updated(user)

    return user


def initiate_user_sync() -> None:
    """Syncs all users from this garden down to all remote gardens. Only the role
    assignments relevant to each remote garden will be included in the sync.

    Returns:
        None
    """
    # Avoiding circular imports
    from beer_garden.api.http.schemas.v1.user import UserSyncSchema
    from beer_garden.router import route

    users = User.objects.all()
    gardens = Garden.objects.filter(connection_type__nin=["LOCAL", None])

    for garden in gardens:
        filtered_users = [
            _filter_role_assigments_by_garden(user, garden) for user in users
        ]
        serialized_users = (
            UserSyncSchema(many=True, strict=True).dump(filtered_users).data
        )
        operation = Operation(
            operation_type="USER_SYNC",
            target_garden_name=garden.name,
            kwargs={"serialized_users": serialized_users},
        )

        route(operation)


def user_sync(serialized_users: List[dict]) -> None:
    """Function called for the USER_SYNC operation type. This imports the supplied list
    of serialized_users and then initiates a USER_SYNC on any remote gardens. The
    serialized_users dicts are expected to have been generated via UserSyncSchema.
    NOTE: Existing users (matched by username) will be updated if present in the
    serialized_users list.

    Args:
        serialized_users: Serialized list of users

    Returns:
        None
    """
    _import_users(serialized_users)
    initiate_user_sync()


def user_synced_with_garden(user: User, garden: Garden) -> bool:
    """Checks if the supplied user is currently synced to the supplied garden, based
    on the corresponding RemoteUser entry. A user is considered synced if there is a
    RemoteUser entry for the specified garden and the role assignments of that entry
    match those of the User (for the relevant gardens).

    Args:
        user: The user for which we are checking the sync status
        garden: The remote garden to check the status against

    Returns:
        bool: True if the user is currently synced. False otherwise.
    """
    # Avoiding circular imports
    from beer_garden.api.http.schemas.v1.user import UserSyncSchema

    try:
        remote_user = RemoteUser.objects.get(username=user.username, garden=garden.name)
    except RemoteUser.DoesNotExist:
        return False

    user = _filter_role_assigments_by_garden(user, garden)
    role_assignments = UserSyncSchema().dump(user).data["role_assignments"]

    return role_assignments == remote_user.role_assignments


def handle_event(event: Event) -> None:
    # Only handle events from downstream gardens
    if event.garden == config.get("garden.name"):
        return

    if event.name == "USER_UPDATED":
        _handle_user_updated_event(event)


def _import_users(serialized_users: List[dict]) -> None:
    """Imports users from a list of dictionaries."""
    # Avoiding circular import. Schemas should probably be moved outside of the http
    # heirarchy.
    from beer_garden.api.http.schemas.v1.user import UserPatchSchema

    for serialized_user in serialized_users:
        username = serialized_user["username"]

        try:
            updated_user_data = UserPatchSchema(strict=True).load(serialized_user).data

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                if len(updated_user_data["role_assignments"]) > 0:
                    user = User(username=username)
                    user.save()
                else:
                    continue

            update_user(user, **updated_user_data)

        except ValidationError as exc:
            logger.info(f"Failed to import user {username} due to error: {exc}")


def _handle_user_updated_event(event):
    """Handling for USER_UPDATED events"""
    # NOTE: This event stores its data in the metadata field as a workaround to the
    # brewtils models dependency inherent in the more typical event publishing flow
    try:
        garden = event.metadata["garden"]
        updated_user = event.metadata["user"]
        updated_at = event.timestamp

        username = updated_user["username"]
        role_assignments = updated_user["role_assignments"]

        try:
            remote_user = RemoteUser.objects.get(garden=garden, username=username)
        except RemoteUser.DoesNotExist:
            remote_user = RemoteUser(garden=garden, username=username)

        remote_user.role_assignments = role_assignments
        remote_user.updated_at = updated_at
        remote_user.save()
    except KeyError:
        logger.error("Error parsing %s event from garden %s", event.name, event.garden)


def _filter_role_assigments_by_garden(user, garden) -> User:
    """Filters the role assignments of the supplied user down to those that apply to
    the namespaces of the supplied garden"""
    namespaces = garden.namespaces
    filtered_user = copy(user)

    filtered_user.role_assignments = [
        assignment
        for assignment in filtered_user.role_assignments
        if (assignment.domain.scope == "Global")
        or (
            assignment.domain.scope == "Garden"
            and assignment.domain.identifiers.get("name") in namespaces
        )
        or (
            assignment.domain.scope == "System"
            and assignment.domain.identifiers.get("namespace") in namespaces
        )
    ]

    return filtered_user


def _publish_user_updated(user):
    """Publish an event with the updated user information"""
    # Avoiding circular imports
    from beer_garden.api.http.schemas.v1.user import UserSyncSchema

    serialized_user = UserSyncSchema().dump(user).data

    # We use publish rather than publish_event here so that we can hijack the metadata
    # field to store our actual data. This is done to avoid needing to deal in brewtils
    # models, which the publish_event decorator requires us to do.
    publish(
        Event(
            name=Events.USER_UPDATED.name,
            metadata={
                "garden": config.get("garden.name"),
                "user": serialized_user,
            },
        )
    )
