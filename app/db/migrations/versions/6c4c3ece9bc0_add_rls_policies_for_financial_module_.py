"""Add RLS policies for financial module tables

Revision ID: 6c4c3ece9bc0
Revises: 0125bc721c61
Create Date: 2026-11-14 00:29:52.887198

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6c4c3ece9bc0'
down_revision: str | Sequence[str] | None = '0125bc721c61'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable RLS and create policies for financial module tables."""
    
    # 1. Enable RLS on all financial tables
    op.execute("ALTER TABLE cash_accounts ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE weekly_periods ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE financial_movements ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE cash_closures ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE closure_adjustments ENABLE ROW LEVEL SECURITY;")
    
    # 2. CASH_ACCOUNTS table policies
    op.execute("""
        CREATE POLICY cash_accounts_select_policy ON cash_accounts
        FOR SELECT USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY cash_accounts_insert_policy ON cash_accounts
        FOR INSERT WITH CHECK (
            current_is_superuser()
            OR (tenant_id = current_tenant_id())
        );
    """)
    
    op.execute("""
        CREATE POLICY cash_accounts_update_policy ON cash_accounts
        FOR UPDATE USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        ) WITH CHECK (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY cash_accounts_delete_policy ON cash_accounts
        FOR DELETE USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    # 3. WEEKLY_PERIODS table policies
    op.execute("""
        CREATE POLICY weekly_periods_select_policy ON weekly_periods
        FOR SELECT USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY weekly_periods_insert_policy ON weekly_periods
        FOR INSERT WITH CHECK (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND created_by_id = current_user_id())
        );
    """)
    
    op.execute("""
        CREATE POLICY weekly_periods_update_policy ON weekly_periods
        FOR UPDATE USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        ) WITH CHECK (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY weekly_periods_delete_policy ON weekly_periods
        FOR DELETE USING (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND created_by_id = current_user_id())
        );
    """)
    
    # 4. FINANCIAL_MOVEMENTS table policies
    op.execute("""
        CREATE POLICY financial_movements_select_policy ON financial_movements
        FOR SELECT USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY financial_movements_insert_policy ON financial_movements
        FOR INSERT WITH CHECK (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND created_by_id = current_user_id())
        );
    """)
    
    op.execute("""
        CREATE POLICY financial_movements_update_policy ON financial_movements
        FOR UPDATE USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        ) WITH CHECK (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY financial_movements_delete_policy ON financial_movements
        FOR DELETE USING (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND created_by_id = current_user_id())
        );
    """)
    
    # 5. CASH_CLOSURES table policies
    op.execute("""
        CREATE POLICY cash_closures_select_policy ON cash_closures
        FOR SELECT USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY cash_closures_insert_policy ON cash_closures
        FOR INSERT WITH CHECK (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND closed_by_id = current_user_id())
        );
    """)
    
    op.execute("""
        CREATE POLICY cash_closures_update_policy ON cash_closures
        FOR UPDATE USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        ) WITH CHECK (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY cash_closures_delete_policy ON cash_closures
        FOR DELETE USING (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND closed_by_id = current_user_id())
        );
    """)
    
    # 6. CLOSURE_ADJUSTMENTS table policies
    op.execute("""
        CREATE POLICY closure_adjustments_select_policy ON closure_adjustments
        FOR SELECT USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY closure_adjustments_insert_policy ON closure_adjustments
        FOR INSERT WITH CHECK (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND created_by_id = current_user_id())
        );
    """)
    
    op.execute("""
        CREATE POLICY closure_adjustments_update_policy ON closure_adjustments
        FOR UPDATE USING (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        ) WITH CHECK (
            current_is_superuser()
            OR tenant_id = current_tenant_id()
        );
    """)
    
    op.execute("""
        CREATE POLICY closure_adjustments_delete_policy ON closure_adjustments
        FOR DELETE USING (
            current_is_superuser()
            OR (tenant_id = current_tenant_id() AND created_by_id = current_user_id())
        );
    """)


def downgrade() -> None:
    """Remove RLS policies for financial module tables."""
    
    # Drop policies
    op.execute("DROP POLICY IF EXISTS cash_accounts_select_policy ON cash_accounts;")
    op.execute("DROP POLICY IF EXISTS cash_accounts_insert_policy ON cash_accounts;")
    op.execute("DROP POLICY IF EXISTS cash_accounts_update_policy ON cash_accounts;")
    op.execute("DROP POLICY IF EXISTS cash_accounts_delete_policy ON cash_accounts;")
    
    op.execute("DROP POLICY IF EXISTS weekly_periods_select_policy ON weekly_periods;")
    op.execute("DROP POLICY IF EXISTS weekly_periods_insert_policy ON weekly_periods;")
    op.execute("DROP POLICY IF EXISTS weekly_periods_update_policy ON weekly_periods;")
    op.execute("DROP POLICY IF EXISTS weekly_periods_delete_policy ON weekly_periods;")
    
    op.execute("DROP POLICY IF EXISTS financial_movements_select_policy ON financial_movements;")
    op.execute("DROP POLICY IF EXISTS financial_movements_insert_policy ON financial_movements;")
    op.execute("DROP POLICY IF EXISTS financial_movements_update_policy ON financial_movements;")
    op.execute("DROP POLICY IF EXISTS financial_movements_delete_policy ON financial_movements;")
    
    op.execute("DROP POLICY IF EXISTS cash_closures_select_policy ON cash_closures;")
    op.execute("DROP POLICY IF EXISTS cash_closures_insert_policy ON cash_closures;")
    op.execute("DROP POLICY IF EXISTS cash_closures_update_policy ON cash_closures;")
    op.execute("DROP POLICY IF EXISTS cash_closures_delete_policy ON cash_closures;")
    
    op.execute("DROP POLICY IF EXISTS closure_adjustments_select_policy ON closure_adjustments;")
    op.execute("DROP POLICY IF EXISTS closure_adjustments_insert_policy ON closure_adjustments;")
    op.execute("DROP POLICY IF EXISTS closure_adjustments_update_policy ON closure_adjustments;")
    op.execute("DROP POLICY IF EXISTS closure_adjustments_delete_policy ON closure_adjustments;")
    
    # Disable RLS
    op.execute("ALTER TABLE closure_adjustments DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE cash_closures DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE financial_movements DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE weekly_periods DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE cash_accounts DISABLE ROW LEVEL SECURITY;")