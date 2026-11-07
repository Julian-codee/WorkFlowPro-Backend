"""Add RLS policies for multi-tenant isolation

Revision ID: 16de51dc251a
Revises: 8a54602000ec
Create Date: 2026-11-05 19:40:37.573444

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '16de51dc251a'
down_revision: str | Sequence[str] | None = '8a54602000ec'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable RLS and create policies for multi-tenant isolation."""
    
    # 1. Enable RLS on all tenant-scoped tables
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE user_tenant_roles ENABLE ROW LEVEL SECURITY;")
    
    # 2. Create function to get current tenant_id from JWT claims
    # This will be set by the application via SET LOCAL
    op.execute("""
        CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid AS $$
        BEGIN
            RETURN current_setting('app.current_tenant_id', true)::uuid;
        EXCEPTION WHEN OTHERS THEN
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # 3. Create function to get current user_id from JWT claims
    op.execute("""
        CREATE OR REPLACE FUNCTION current_user_id() RETURNS uuid AS $$
        BEGIN
            RETURN current_setting('app.current_user_id', true)::uuid;
        EXCEPTION WHEN OTHERS THEN
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # 4. Create function to check if current user is superuser
    op.execute("""
        CREATE OR REPLACE FUNCTION current_is_superuser() RETURNS boolean AS $$
        BEGIN
            RETURN current_setting('app.current_is_superuser', true)::boolean;
        EXCEPTION WHEN OTHERS THEN
            RETURN false;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
    """)
    
    # 5. TENANTS table policies
    # Superusers can see all tenants, regular users only their own
    op.execute("""
        CREATE POLICY tenants_select_policy ON tenants
        FOR SELECT USING (
            current_is_superuser() 
            OR id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY tenants_insert_policy ON tenants
        FOR INSERT WITH CHECK (
            current_is_superuser()
        );
    """)
    
    op.execute("""
        CREATE POLICY tenants_update_policy ON tenants
        FOR UPDATE USING (
            current_is_superuser() 
            OR id = current_tenant_id()
        ) WITH CHECK (
            current_is_superuser() 
            OR id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY tenants_delete_policy ON tenants
        FOR DELETE USING (
            current_is_superuser()
        );
    """)
    
    # 6. USERS table policies
    op.execute("""
        CREATE POLICY users_select_policy ON users
        FOR SELECT USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY users_insert_policy ON users
        FOR INSERT WITH CHECK (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY users_update_policy ON users
        FOR UPDATE USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        ) WITH CHECK (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY users_delete_policy ON users
        FOR DELETE USING (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND id != current_user_id())
        );
    """)
    
    # 7. TASKS table policies
    op.execute("""
        CREATE POLICY tasks_select_policy ON tasks
        FOR SELECT USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY tasks_insert_policy ON tasks
        FOR INSERT WITH CHECK (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND created_by_id = current_user_id())
        );
    """)
    
    op.execute("""
        CREATE POLICY tasks_update_policy ON tasks
        FOR UPDATE USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        ) WITH CHECK (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY tasks_delete_policy ON tasks
        FOR DELETE USING (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND created_by_id = current_user_id())
        );
    """)
    
    # 8. USER_TENANT_ROLES table policies
    op.execute("""
        CREATE POLICY user_tenant_roles_select_policy ON user_tenant_roles
        FOR SELECT USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
            OR user_id = current_user_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY user_tenant_roles_insert_policy ON user_tenant_roles
        FOR INSERT WITH CHECK (
            current_is_superuser()
        );
    """)
    
    op.execute("""
        CREATE POLICY user_tenant_roles_update_policy ON user_tenant_roles
        FOR UPDATE USING (
            current_is_superuser()
        ) WITH CHECK (
            current_is_superuser()
        );
    """)
    
    op.execute("""
        CREATE POLICY user_tenant_roles_delete_policy ON user_tenant_roles
        FOR DELETE USING (
            current_is_superuser()
        );
    """)


def downgrade() -> None:
    """Remove RLS policies."""
    
    # Drop policies
    op.execute("DROP POLICY IF EXISTS tenants_select_policy ON tenants;")
    op.execute("DROP POLICY IF EXISTS tenants_insert_policy ON tenants;")
    op.execute("DROP POLICY IF EXISTS tenants_update_policy ON tenants;")
    op.execute("DROP POLICY IF EXISTS tenants_delete_policy ON tenants;")
    
    op.execute("DROP POLICY IF EXISTS users_select_policy ON users;")
    op.execute("DROP POLICY IF EXISTS users_insert_policy ON users;")
    op.execute("DROP POLICY IF EXISTS users_update_policy ON users;")
    op.execute("DROP POLICY IF EXISTS users_delete_policy ON users;")
    
    op.execute("DROP POLICY IF EXISTS tasks_select_policy ON tasks;")
    op.execute("DROP POLICY IF EXISTS tasks_insert_policy ON tasks;")
    op.execute("DROP POLICY IF EXISTS tasks_update_policy ON tasks;")
    op.execute("DROP POLICY IF EXISTS tasks_delete_policy ON tasks;")
    
    op.execute("DROP POLICY IF EXISTS user_tenant_roles_select_policy ON user_tenant_roles;")
    op.execute("DROP POLICY IF EXISTS user_tenant_roles_insert_policy ON user_tenant_roles;")
    op.execute("DROP POLICY IF EXISTS user_tenant_roles_update_policy ON user_tenant_roles;")
    op.execute("DROP POLICY IF EXISTS user_tenant_roles_delete_policy ON user_tenant_roles;")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS current_tenant_id();")
    op.execute("DROP FUNCTION IF EXISTS current_user_id();")
    op.execute("DROP FUNCTION IF EXISTS current_is_superuser();")
    
    # Disable RLS
    op.execute("ALTER TABLE user_tenant_roles DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tasks DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY;")