"""
WOMS Users Module Models

This module contains all user and audit-related models:
- User: User accounts with authentication
- Role: User role definitions
- ActionType: Audit action type lookup
- AuditLog: System-wide audit trail with JSONB change tracking
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Index, Text
from sqlalchemy.dialects.postgresql import JSONB


# =============================================================================
# Action Type Lookup Table
# =============================================================================

class ActionType(SQLModel, table=True):
    """
    Audit action type lookup table.
    
    Normalizes action types for audit logging instead of using VARCHAR.
    
    Examples: INSERT, UPDATE, DELETE, SOFT_DELETE, LOGIN, LOGOUT, etc.
    """
    __tablename__ = "action_type"
    
    action_id: Optional[int] = Field(default=None, primary_key=True)
    action_name: str = Field(max_length=50, unique=True, index=True)
    description: Optional[str] = Field(default=None, max_length=200)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    audit_logs: List["AuditLog"] = Relationship(back_populates="action_type")


# =============================================================================
# Role Table
# =============================================================================

class Role(SQLModel, table=True):
    """
    User role definitions.
    
    Examples: Admin, Manager, Warehouse Staff, Driver, Picker, Packer, etc.
    """
    __tablename__ = "roles"
    __table_args__ = (
        # GIN index on permissions JSONB — enables permission-level queries
        Index("idx_roles_permissions_gin", "permissions",
              postgresql_using="gin",
              postgresql_ops={"permissions": "jsonb_path_ops"}),
    )

    role_id: Optional[int] = Field(default=None, primary_key=True)
    role_name: str = Field(max_length=100, unique=True, index=True)
    
    # Role description
    description: Optional[str] = Field(default=None, max_length=500)
    
    # Permissions (can be extended with JSONB for granular permissions)
    permissions: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Role permissions in JSONB format"
    )
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    users: List["User"] = Relationship(back_populates="role")
    drivers: List["Driver"] = Relationship(back_populates="role")


# =============================================================================
# User Table
# =============================================================================

class User(SQLModel, table=True):
    """
    User account model.
    
    Features:
    - Secure password storage (hash only)
    - Active/inactive status
    - Role-based access control
    """
    __tablename__ = "users"
    
    user_id: Optional[int] = Field(default=None, primary_key=True)
    
    # Authentication
    username: str = Field(max_length=100, unique=True, index=True)
    email: str = Field(max_length=255, unique=True, index=True)
    password_hash: str = Field(sa_column=Column(Text))
    
    # Profile information
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    
    # Role assignment
    role_id: Optional[int] = Field(default=None, foreign_key="roles.role_id", index=True)
    
    # Account status
    is_active: bool = Field(default=True, index=True)
    is_superuser: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    
    # Relationships
    role: Optional[Role] = Relationship(back_populates="users")
    driver: Optional["Driver"] = Relationship(back_populates="user")
    audit_logs: List["AuditLog"] = Relationship(back_populates="changed_by_user")
    driver_teams: List["DriverTeam"] = Relationship(back_populates="user")
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p) or self.username


# =============================================================================
# Audit Log Table
# =============================================================================

class AuditLog(SQLModel, table=True):
    """
    System-wide audit trail.
    
    Tracks all changes across the system with JSONB for old/new values.
    Provides comprehensive audit capabilities for compliance and debugging.
    
    Features:
    - Links to items_history for item-specific changes
    - JSONB storage for old and new data
    - Tracks table name and action type (via FK to action_type)
    - Links to user who made the change
    
    Example entry:
    {
        "table_name": "items",
        "action_id": 2,  // References action_type.UPDATE
        "old_data": {"status_id": 1, "item_name": "Old Name"},
        "new_data": {"status_id": 2, "item_name": "New Name"}
    }
    """
    __tablename__ = "audit_log"
    __table_args__ = (
        # GIN indexes on JSONB change-data — enables queries like old_data @> '{"status": 1}'
        Index("idx_audit_old_data_gin", "old_data",
              postgresql_using="gin",
              postgresql_ops={"old_data": "jsonb_path_ops"}),
        Index("idx_audit_new_data_gin", "new_data",
              postgresql_using="gin",
              postgresql_ops={"new_data": "jsonb_path_ops"}),
    )

    audit_id: Optional[int] = Field(default=None, primary_key=True)
    
    # What was changed
    table_name: str = Field(max_length=100, index=True)
    record_id: Optional[str] = Field(
        default=None, 
        max_length=100, 
        index=True,
        description="Primary key of the changed record"
    )
    
    # Link to items_history if applicable
    history_id: Optional[int] = Field(
        default=None, 
        foreign_key="items_history.history_id",
        index=True
    )
    
    # Action type: FK to action_type lookup table
    action_id: int = Field(
        foreign_key="action_type.action_id",
        index=True,
        description="Reference to action type (INSERT, UPDATE, DELETE, etc.)"
    )
    
    # JSONB for change data
    old_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="Previous state of the record"
    )
    new_data: Optional[Dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSONB),
        description="New state of the record"
    )
    
    # Who made the change
    changed_by_user_id: Optional[int] = Field(
        default=None, 
        foreign_key="users.user_id",
        index=True
    )
    
    # When the change occurred
    changed_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Additional context
    ip_address: Optional[str] = Field(default=None, max_length=50)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    
    # Relationships
    changed_by_user: Optional[User] = Relationship(back_populates="audit_logs")
    action_type: Optional[ActionType] = Relationship(back_populates="audit_logs")


# Forward references
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.delivery import Driver, DriverTeam
