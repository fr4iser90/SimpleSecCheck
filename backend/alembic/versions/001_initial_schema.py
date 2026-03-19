"""Initial schema – single source of truth. No create_all, no IF NOT EXISTS.

Revision ID: 001
Revises:
Create Date: 2025-03-19

All tables: users, system_state, scans, scanners, user_scan_targets, scan_steps, etc.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extension + ENUM types (single source of truth at DB level)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE TYPE user_role_enum AS ENUM ('admin', 'user', 'guest')")
    op.execute("CREATE TYPE scan_status_enum AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled', 'interrupted')")
    op.execute("CREATE TYPE severity_enum AS ENUM ('critical', 'high', 'medium', 'low', 'info')")
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    DECLARE
        old_json jsonb;
        new_json jsonb;
        i int;
    BEGIN
        old_json := row_to_json(OLD)::jsonb;
        new_json := row_to_json(NEW)::jsonb;
        IF TG_NARGS > 0 THEN
            FOR i IN 0..TG_NARGS - 1 LOOP
                old_json := old_json - TG_ARGV[i];
                new_json := new_json - TG_ARGV[i];
            END LOOP;
        END IF;
        IF old_json IS DISTINCT FROM new_json THEN
            NEW.updated_at := NOW();
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 1. users (no FK)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", postgresql.ENUM("admin", "user", "guest", name="user_role_enum", create_type=False), nullable=False, server_default=sa.text("'user'::user_role_enum")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("user_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("idx_users_username", "users", ["username"], unique=True)
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_role", "users", ["role"])

    # 2. password_reset_tokens
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])

    # 3. system_state (singleton: exactly one row, fixed ID)
    op.create_table(
        "system_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("'00000000-0000-0000-0000-000000000001'::uuid")),
        sa.Column("setup_status", sa.String(50), nullable=False, server_default="not_initialized"),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.Column("auth_mode", sa.String(20), nullable=False, server_default="free"),
        sa.Column("setup_token_hash", sa.String(255), nullable=True),
        sa.Column("setup_token_created_at", sa.DateTime(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("setup_completed_at", sa.DateTime(), nullable=True),
        sa.Column("database_initialized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("admin_user_created", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("system_configured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("setup_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_setup_attempt", sa.DateTime(), nullable=True),
        sa.Column("setup_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint(
            "id = '00000000-0000-0000-0000-000000000001'::uuid",
            name="ck_system_state_singleton",
        ),
    )
    # Insert singleton row so table is never empty; app only ever UPDATEs.
    op.execute(
        """
        INSERT INTO system_state (id, setup_status, version, auth_mode, created_at, updated_at,
            database_initialized, admin_user_created, system_configured, setup_attempts, setup_locked)
        VALUES (
            '00000000-0000-0000-0000-000000000001'::uuid,
            'not_initialized', '1.0.0', 'free', NOW(), NOW(),
            false, false, false, 0, false
        )
        ON CONFLICT (id) DO NOTHING;
        """
    )

    # 4. scans
    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True, server_default=""),
        sa.Column("scan_type", sa.String(50), nullable=False),
        sa.Column("status", postgresql.ENUM("pending", "running", "completed", "failed", "cancelled", "interrupted", name="scan_status_enum", create_type=False), nullable=False, server_default=sa.text("'pending'::scan_status_enum")),
        sa.Column("target_url", sa.String(500), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("scanners", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_vulnerabilities", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("critical_vulnerabilities", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("high_vulnerabilities", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("medium_vulnerabilities", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("low_vulnerabilities", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("info_vulnerabilities", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("project_id", sa.String(255), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("scan_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.CheckConstraint(
            "target_type IN ('git_repo', 'container_registry', 'local_mount')",
            name="ck_scans_target_type_valid",
        ),
    )
    op.create_index("idx_scans_user_id", "scans", ["user_id"])
    op.create_index("idx_scans_status", "scans", ["status"])
    op.create_index("idx_scans_created_at", "scans", ["created_at"])
    op.create_index(
        "idx_scans_status_created_at",
        "scans",
        ["status", "created_at"],
    )
    op.create_index("idx_scans_target_url", "scans", ["target_url"])
    op.create_index("idx_scans_priority", "scans", ["priority"])
    op.create_index(
        "idx_scans_active",
        "scans",
        ["status"],
        postgresql_where=sa.text("status IN ('pending', 'running')"),
    )
    op.create_index("idx_scans_config", "scans", ["config"], postgresql_using="gin")
    op.create_index("idx_scans_results", "scans", ["results"], postgresql_using="gin")
    op.create_index(
        "idx_scans_results_completed",
        "scans",
        ["results"],
        postgresql_using="gin",
        postgresql_where=sa.text("status = 'completed' AND results IS NOT NULL"),
    )

    # 5. vulnerabilities (FK CASCADE for referential integrity)
    op.create_table(
        "vulnerabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "scan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", postgresql.ENUM("critical", "high", "medium", "low", "info", name="severity_enum", create_type=False), nullable=False),
        sa.Column("cwe_id", sa.String(20), nullable=True),
        sa.Column("cvss_score", sa.String(10), nullable=True),
        sa.Column("file_path", sa.String(500), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("column_number", sa.Integer(), nullable=True),
        sa.Column("scanner", sa.String(100), nullable=False),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("vuln_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_vulnerabilities_scan_id", "vulnerabilities", ["scan_id"])
    op.create_index("idx_vulnerabilities_severity", "vulnerabilities", ["severity"])
    op.create_index("idx_vulnerabilities_scanner", "vulnerabilities", ["scanner"])
    op.create_index(
        "idx_vuln_scan_severity",
        "vulnerabilities",
        ["scan_id", "severity"],
    )

    # 6. scanners
    op.create_table(
        "scanners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("scan_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("requires_condition", sa.String(100), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scanner_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("last_discovered_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_scanners_name", "scanners", ["name"], unique=True)
    op.create_index("idx_scanners_enabled", "scanners", ["enabled"])

    # 7. scanner_tool_settings
    op.create_table(
        "scanner_tool_settings",
        sa.Column("scanner_key", sa.String(128), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("idx_scanner_tool_settings_updated_by_user_id", "scanner_tool_settings", ["updated_by_user_id"])

    # 8. audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("target", sa.String(500), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("result", sa.String(20), nullable=False, server_default=sa.text("'success'")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("idx_audit_log_action_type", "audit_log", ["action_type"])
    op.create_index("idx_audit_log_created_at", "audit_log", ["created_at"])

    # 9. blocked_ips
    op.create_table(
        "blocked_ips",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ip_address", postgresql.INET(), nullable=False),
        sa.Column("reason", sa.String(100), nullable=True),
        sa.Column("blocked_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("blocked_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("idx_blocked_ips_ip_address", "blocked_ips", ["ip_address"], unique=True)
    op.create_index("idx_blocked_ips_is_active", "blocked_ips", ["is_active"])

    # 10. ip_activity
    op.create_table(
        "ip_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ip_address", postgresql.INET(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("window_start", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("window_end", sa.DateTime(), nullable=True),
        sa.Column("activity_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_ip_activity_ip_address", "ip_activity", ["ip_address"])
    op.create_index("idx_ip_activity_event_type", "ip_activity", ["event_type"])
    op.create_index("idx_ip_activity_window", "ip_activity", ["window_start", "window_end"])

    # 11. vulnerability_rules
    op.create_table(
        "vulnerability_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", postgresql.ENUM("critical", "high", "medium", "low", "info", name="severity_enum", create_type=False), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("custom", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_vulnerability_rules_rule_id", "vulnerability_rules", ["rule_id"], unique=True)

    # 12. suppression_rules
    op.create_table(
        "suppression_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", sa.String(100), sa.ForeignKey("vulnerability_rules.rule_id"), nullable=True),
        sa.Column("pattern", sa.String(500), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    # 13. scan_policies
    op.create_table(
        "scan_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("enabled_scanners", postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("scan_depth", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("timeout", sa.Integer(), nullable=False, server_default=sa.text("3600")),
        sa.Column("severity_threshold", sa.String(20), nullable=True),
        sa.Column("custom_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    # 14. notification_channels
    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    # 15. notification_rules
    op.create_table(
        "notification_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notification_channels.id"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("severity_filter", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("rate_limit", sa.Integer(), nullable=True),
        sa.Column("template", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    # 16. user_github_repos
    op.create_table(
        "user_github_repos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("repo_url", sa.String(500), nullable=False),
        sa.Column("repo_owner", sa.String(255), nullable=True),
        sa.Column("repo_name", sa.String(255), nullable=False),
        sa.Column("branch", sa.String(100), nullable=False, server_default="main"),
        sa.Column("auto_scan_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scan_on_push", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scan_frequency", sa.String(20), nullable=False, server_default="on_push"),
        sa.Column("scanners", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("github_token", sa.Text(), nullable=True),
        sa.Column("webhook_secret", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_user_github_repos_user_id", "user_github_repos", ["user_id"])

    # 17. user_scan_targets (My Targets)
    op.create_table(
        "user_scan_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(1000), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("auto_scan", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "type IN ('git_repo', 'container_registry', 'local_mount')",
            name="ck_user_scan_targets_type_valid",
        ),
    )
    op.create_index("idx_user_scan_targets_user_id", "user_scan_targets", ["user_id"])
    op.create_index("idx_user_scan_targets_type", "user_scan_targets", ["type"])
    op.create_unique_constraint(
        "uq_user_scan_targets_user_source",
        "user_scan_targets",
        ["user_id", "source"],
    )
    op.create_index(
        "idx_user_scan_targets_config",
        "user_scan_targets",
        ["config"],
        postgresql_using="gin",
    )

    # 18. repo_scan_history
    op.create_table(
        "repo_scan_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("user_github_repos.id"), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id"), nullable=True),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("commit_hash", sa.String(100), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("vulnerabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_repo_scan_history_repo_id", "repo_scan_history", ["repo_id"])
    op.create_index("idx_repo_scan_history_created_at", "repo_scan_history", ["created_at"])

    # 19. scanner_duration_stats
    op.create_table(
        "scanner_duration_stats",
        sa.Column("scanner_name", sa.String(100), primary_key=True),
        sa.Column("avg_duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("120")),
        sa.Column("min_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("max_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_updated", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

    # 20. api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("idx_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    # 21. scan_steps (DB-backed step UI; scan_id UUID + FK for consistency with scans)
    op.create_table(
        "scan_steps",
        sa.Column(
            "scan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("step_number", sa.Integer(), primary_key=True),
        sa.Column("step_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column(
            "substeps",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
    )
    op.create_index("ix_scan_steps_scan_id", "scan_steps", ["scan_id"])

    # Triggers: parametrized (exclude JSONB from "changed" check) and/or column-based (large tables)
    op.execute("CREATE TRIGGER set_updated_at_users BEFORE UPDATE ON users FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();")
    op.execute("CREATE TRIGGER set_updated_at_system_state BEFORE UPDATE ON system_state FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('config');")
    op.execute("""
    CREATE TRIGGER set_updated_at_scans
    BEFORE UPDATE OF name, description, scan_type, status, target_url, target_type, created_at, started_at, completed_at,
        scheduled_at, last_heartbeat_at, total_vulnerabilities, critical_vulnerabilities, high_vulnerabilities,
        medium_vulnerabilities, low_vulnerabilities, info_vulnerabilities, duration, error_message, retry_count,
        user_id, project_id, priority
    ON scans
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('scanners', 'config', 'results', 'tags', 'scan_metadata');
    """)
    op.execute("CREATE TRIGGER set_updated_at_scanners BEFORE UPDATE ON scanners FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('scan_types', 'scanner_metadata');")
    op.execute("CREATE TRIGGER set_updated_at_scanner_tool_settings BEFORE UPDATE ON scanner_tool_settings FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('config');")
    op.execute("CREATE TRIGGER set_updated_at_vulnerability_rules BEFORE UPDATE ON vulnerability_rules FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('config');")
    op.execute("CREATE TRIGGER set_updated_at_scan_policies BEFORE UPDATE ON scan_policies FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('custom_rules');")
    op.execute("CREATE TRIGGER set_updated_at_notification_channels BEFORE UPDATE ON notification_channels FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('config');")
    op.execute("CREATE TRIGGER set_updated_at_notification_rules BEFORE UPDATE ON notification_rules FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();")
    op.execute("CREATE TRIGGER set_updated_at_user_github_repos BEFORE UPDATE ON user_github_repos FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('scanners');")
    op.execute("""
    CREATE TRIGGER set_updated_at_user_scan_targets
    BEFORE UPDATE OF user_id, type, source, display_name, created_at
    ON user_scan_targets
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('auto_scan', 'config');
    """)
    op.execute("CREATE TRIGGER set_updated_at_scan_steps BEFORE UPDATE ON scan_steps FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column('substeps');")


def downgrade() -> None:
    # Reverse order (dependents first); triggers are dropped with tables
    op.drop_table("scan_steps")
    op.drop_table("api_keys")
    op.drop_table("scanner_duration_stats")
    op.drop_table("repo_scan_history")
    op.drop_table("user_scan_targets")
    op.drop_table("user_github_repos")
    op.drop_table("notification_rules")
    op.drop_table("notification_channels")
    op.drop_table("scan_policies")
    op.drop_table("suppression_rules")
    op.drop_table("vulnerability_rules")
    op.drop_table("ip_activity")
    op.drop_table("blocked_ips")
    op.drop_table("audit_log")
    op.drop_table("scanner_tool_settings")
    op.drop_table("scanners")
    op.drop_table("vulnerabilities")
    op.drop_table("scans")
    op.drop_table("system_state")
    op.drop_table("password_reset_tokens")
    op.drop_table("users")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
    op.execute("DROP TYPE IF EXISTS severity_enum CASCADE")
    op.execute("DROP TYPE IF EXISTS scan_status_enum CASCADE")
    op.execute("DROP TYPE IF EXISTS user_role_enum CASCADE")
