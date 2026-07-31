"""Firebase Admin SDK adapter for ID-token verification."""

from threading import Lock
from uuid import uuid4

import firebase_admin  # type: ignore[import-untyped]
from anyio import to_thread
from firebase_admin import App, auth
from firebase_admin import exceptions as firebase_exceptions
from google.auth import exceptions as google_auth_exceptions
from app.auth.models import (
    AuthenticatedPrincipal,
    AuthenticationServiceUnavailableError,
    InvalidAuthenticationTokenError,
)

MAX_FIREBASE_UID_LENGTH = 128


class FirebaseAdminTokenVerifier:
    """Verify Firebase ID tokens with ADC and an explicitly scoped app."""

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._app_name = f"travel-assistant-{uuid4()}"
        self._app: App | None = None
        self._app_lock = Lock()

    async def verify_id_token(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        """Run the synchronous Admin SDK away from the event loop."""
        return await to_thread.run_sync(
            self._verify_id_token_sync,
            raw_token,
            abandon_on_cancel=True,
        )

    def _verify_id_token_sync(
        self,
        raw_token: str,
    ) -> AuthenticatedPrincipal:
        try:
            firebase_app = self._firebase_app()
        except (
            ValueError,
            firebase_exceptions.FirebaseError,
            google_auth_exceptions.GoogleAuthError,
        ) as error:
            raise AuthenticationServiceUnavailableError from error

        try:
            decoded_token = auth.verify_id_token(
                raw_token,
                app=firebase_app,
                check_revoked=True,
            )
        except (
            ValueError,
            auth.InvalidIdTokenError,
            auth.UserDisabledError,
            auth.UserNotFoundError,
        ) as error:
            raise InvalidAuthenticationTokenError from error
        except (
            firebase_exceptions.FirebaseError,
            google_auth_exceptions.GoogleAuthError,
        ) as error:
            raise AuthenticationServiceUnavailableError from error

        uid = decoded_token.get("uid")
        if (
            not isinstance(uid, str)
            or not uid.strip()
            or len(uid) > MAX_FIREBASE_UID_LENGTH
        ):
            raise InvalidAuthenticationTokenError
        return AuthenticatedPrincipal(uid=uid)

    def _firebase_app(self) -> App:
        app = self._app
        if app is not None:
            return app

        with self._app_lock:
            app = self._app
            if app is None:
                app = firebase_admin.initialize_app(
                    options={"projectId": self._project_id},
                    name=self._app_name,
                )
                self._app = app
            return app
