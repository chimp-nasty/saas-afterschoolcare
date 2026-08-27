from uuid import UUID
from secrets import token_urlsafe
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, hash_token
from app.auth.jwt.tokens import TokenService
from app.auth.models.user import User
from app.auth.repositories.user import UserRepository
from app.auth.repositories.permission import PermissionRepository
from app.auth.repositories.location_user_role import LocationUserRoleRepository
from app.auth.repositories.role import RoleRepository
from app.auth.repositories.password_reset_token import PasswordResetTokenRepository
from app.auth.schemas.auth import (
    LoginRequest,
    RegistrationRequest,
    ResetPasswordRequest,
    ForgotPasswordRequest,
)
from app.errors.auth import (
    AuthenticationFailedError,
    UserCollisionError,
    InvalidPasswordResetError
)


class AuthService:
    def __init__(self, *, db: Session):
        self.db = db
        self.users = UserRepository(db=db)
        self.permissions = PermissionRepository(db=db)
        self.roles = RoleRepository(db=db)
        self.location_user_roles = LocationUserRoleRepository(db=db)
        self.password_reset_tokens = PasswordResetTokenRepository(db=db)
        
    def login(
        self,
        *,
        body: LoginRequest,
        location_id: UUID,
    ) -> str:
        """
        Authenticate a user for a location and issue an access token.

        The token is scoped to the requested location and contains the
        user's roles and effective permissions for that location.
        """
        try:
            user = self.users.get_by_email(
                email=body.email
            )
            
            if not user:
                raise AuthenticationFailedError()
            
            check_password = verify_password(
                password=body.password,
                hashed_password=user.password_hash
            )
            
            if not check_password:
                raise AuthenticationFailedError()
            
            # Resolve authorization for the requested location.
            location_user_roles = self.location_user_roles.list_roles_by_user_and_location(
                user_id=user.id,
                location_id=location_id,
            )

            if not location_user_roles:
                raise AuthenticationFailedError()

            role_ids = [
                location_user_role.role_id
                for location_user_role in location_user_roles
            ]
                        
            roles = [
                role.code
                for role in self.roles.list_by_ids(
                    role_ids=role_ids,
                )
            ]
            
            permissions = self.permissions.list_by_role_ids(
                role_ids=[
                    location_user_role.role_id
                    for location_user_role in location_user_roles
                ],
            )

            permission_map = TokenService.build_permission_map(
                permissions=permissions,
            )
            
            self.users.update_last_login(
                user=user
            )
            
            access_token = TokenService.create_access_token(
                user_id=user.id,
                location_id=location_id,
                roles=roles,
                permissions=permission_map
            )
            
            self.db.commit()
            return access_token
            
        except Exception:
            self.db.rollback()
            raise
        
    def register_user(
        self,
        *,
        body: RegistrationRequest
    ) -> User:
        """
        Register a new user account.

        Validates account uniqueness, hashes the supplied password,
        and creates the authentication user record.
        """
        try:
            existing_user = self.users.get_by_email(
                email=body.email
            )
            
            if existing_user:
                raise UserCollisionError()
            
            password_hash = hash_password(
                password=body.password
            )
            
            user = self.users.create(
                email=body.email,
                password_hash=password_hash,
                
                first_name=body.first_name,
                last_name=body.last_name,
                
                terms_accepted_at=datetime.now(timezone.utc)
            )
            
            self.db.commit()
            return user
            
        except Exception:
            self.db.rollback()
            raise
        
    def reset_password(
        self,
        *,
        body: ResetPasswordRequest
    ) -> None:
        """
        Reset a user's password using a valid reset token.

        Validates the reset token, resolves the associated user,
        updates the password, and marks the token as used.
        """
        try:
            token_hash = hash_token(
                token=body.token
            )
            
            reset_token = self.password_reset_tokens.get_valid_by_token_hash(
                token_hash=token_hash,
            )

            if not reset_token:
                raise InvalidPasswordResetError()
            
            user = self.users.get_by_id(
                id=reset_token.user_id,
            )

            if not user:
                raise InvalidPasswordResetError()
        
            password_hash = hash_password(
                password=body.password
            )
            
            self.users.update_password_hash(
                user=user,
                password_hash=password_hash
            )
            
            self.db.commit()
            
        except Exception:
            self.db.rollback()
            raise
        
    def request_password_reset(
        self,
        *,
        body: ForgotPasswordRequest
    ) -> None:
        """
        Create a password reset token for an existing user.

        Stores only the hashed token and leaves delivery of the raw
        token to the email integration.
        """
        try:
            user = self.users.get_by_email(
                email=body.email
            )
            
            if not user:
                return
            
            raw_token = token_urlsafe(32)
            
            token_hash = hash_token(
                token=raw_token,
            )
            
            self.password_reset_tokens.create(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=(
                    datetime.now(timezone.utc)
                    + timedelta(minutes=30)
                ),
            )
            
            self.db.commit()
        
        except Exception:
            self.db.rollback()
            raise