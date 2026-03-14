"""
Setup CLI Commands

This module provides CLI commands for managing the Enterprise Setup Security System.
Designed for enterprise users and administrators to manage setup operations.
"""
import asyncio
import click
import sys
from datetime import datetime, timedelta
from typing import Optional

from config.settings import settings
from infrastructure.database.adapter import db_adapter
from infrastructure.database.models import SystemState, SetupStatusEnum
from infrastructure.redis.client import redis_client
from api.services.setup_token_service import SetupTokenService
from api.services.setup_expiry_service import SetupExpiryService
from api.services.security_event_service import SecurityEventService


@click.group(name="setup", help="Setup management commands")
def setup_group():
    """Setup management commands for Enterprise Setup Security System."""
    pass


@setup_group.command(name="init", help="Initialize setup system")
@click.option('--force', is_flag=True, help="Force initialization even if setup exists")
@click.option('--admin-email', type=str, help="Admin user email")
@click.option('--admin-password', type=str, help="Admin user password")
def init_setup(force: bool, admin_email: Optional[str], admin_password: Optional[str]):
    """
    Initialize the setup system with enterprise security features.
    
    This command:
    - Creates database tables
    - Generates initial setup token
    - Sets up system state
    - Logs security events
    """
    try:
        asyncio.run(_async_init_setup(force, admin_email, admin_password))
        click.echo("✅ Setup system initialized successfully")
    except Exception as e:
        click.echo(f"❌ Setup initialization failed: {e}", err=True)
        sys.exit(1)


@setup_group.command(name="status", help="Check setup status")
def check_status():
    """Check current setup status and configuration."""
    try:
        status = asyncio.run(_async_check_status())
        _print_status(status)
    except Exception as e:
        click.echo(f"❌ Failed to check status: {e}", err=True)
        sys.exit(1)


@setup_group.command(name="token", help="Manage setup tokens")
@click.option('--generate', is_flag=True, help="Generate new setup token")
@click.option('--invalidate', is_flag=True, help="Invalidate current token")
@click.option('--show', is_flag=True, help="Show current token info")
def manage_tokens(generate: bool, invalidate: bool, show: bool):
    """Manage setup tokens for enterprise security."""
    try:
        if generate:
            token = asyncio.run(_async_generate_token())
            click.echo(f"✅ New setup token generated: {token}")
        elif invalidate:
            success = asyncio.run(_async_invalidate_token())
            if success:
                click.echo("✅ Setup token invalidated successfully")
            else:
                click.echo("❌ No token to invalidate")
        elif show:
            info = asyncio.run(_async_show_token_info())
            if info:
                _print_token_info(info)
            else:
                click.echo("ℹ️ No setup token found")
        else:
            click.echo("Please specify --generate, --invalidate, or --show")
    except Exception as e:
        click.echo(f"❌ Token management failed: {e}", err=True)
        sys.exit(1)


@setup_group.command(name="lock", help="Lock setup permanently")
@click.option('--reason', type=str, help="Reason for locking setup")
def lock_setup(reason: Optional[str]):
    """Lock setup permanently to prevent unauthorized access."""
    try:
        success = asyncio.run(_async_lock_setup(reason))
        if success:
            click.echo("✅ Setup locked permanently")
        else:
            click.echo("❌ Failed to lock setup")
    except Exception as e:
        click.echo(f"❌ Setup lock failed: {e}", err=True)
        sys.exit(1)


@setup_group.command(name="reset", help="Reset setup (development only)")
@click.option('--confirm', is_flag=True, help="Confirm reset operation")
@click.option('--force', is_flag=True, help="Force reset even in production")
def reset_setup(confirm: bool, force: bool):
    """Reset setup to initial state (development/testing only)."""
    if settings.ENVIRONMENT != "development" and not force:
        click.echo("❌ Setup reset is only allowed in development environment")
        click.echo("Use --force to override (NOT RECOMMENDED)")
        sys.exit(1)
    
    if not confirm:
        click.echo("⚠️ This will reset all setup data and create a new setup token")
        click.echo("Use --confirm to proceed")
        sys.exit(1)
    
    try:
        success = asyncio.run(_async_reset_setup())
        if success:
            click.echo("✅ Setup reset successfully")
            click.echo("ℹ️ New setup token generated")
        else:
            click.echo("❌ Failed to reset setup")
    except Exception as e:
        click.echo(f"❌ Setup reset failed: {e}", err=True)
        sys.exit(1)


@setup_group.command(name="expiry", help="Manage setup expiry")
@click.option('--extend', type=int, help="Extend setup window by N days")
@click.option('--check', is_flag=True, help="Check current expiry status")
@click.option('--reset', is_flag=True, help="Reset expiry timer")
def manage_expiry(extend: Optional[int], check: bool, reset: bool):
    """Manage setup expiry and automatic disabling."""
    try:
        if extend:
            success = asyncio.run(_async_extend_expiry(extend))
            if success:
                click.echo(f"✅ Setup window extended by {extend} days")
            else:
                click.echo("❌ Failed to extend setup window")
        elif check:
            info = asyncio.run(_async_check_expiry())
            if info:
                _print_expiry_info(info)
            else:
                click.echo("ℹ️ No setup expiry information available")
        elif reset:
            success = asyncio.run(_async_reset_expiry())
            if success:
                click.echo("✅ Setup expiry timer reset")
            else:
                click.echo("❌ Failed to reset expiry timer")
        else:
            click.echo("Please specify --extend, --check, or --reset")
    except Exception as e:
        click.echo(f"❌ Expiry management failed: {e}", err=True)
        sys.exit(1)


@setup_group.command(name="monitor", help="Start expiry monitor")
@click.option('--daemon', is_flag=True, help="Run as daemon")
def start_monitor(daemon: bool):
    """Start the setup expiry monitor."""
    try:
        if daemon:
            click.echo("Starting expiry monitor as daemon...")
            asyncio.run(_async_start_monitor_daemon())
        else:
            click.echo("Starting expiry monitor...")
            asyncio.run(_async_start_monitor())
    except KeyboardInterrupt:
        click.echo("\n⏹️ Monitor stopped by user")
    except Exception as e:
        click.echo(f"❌ Monitor failed: {e}", err=True)
        sys.exit(1)


# Async helper functions

async def _async_init_setup(force: bool, admin_email: Optional[str], admin_password: Optional[str]):
    """Initialize setup system asynchronously."""
    security_logger = SecurityEventService()
    
    # Check if setup already exists
    if not force:
        async with db_adapter.get_session() as session:
            result = await session.execute(
                select(SystemState).where(SystemState.id == "system_state")
            )
            existing_state = result.scalar_one_or_none()
            
            if existing_state and existing_state.setup_status != SetupStatusEnum.NOT_INITIALIZED:
                raise Exception("Setup already initialized. Use --force to override.")
    
    # Create database tables
    await db_adapter.create_tables()
    
    # Create system state
    system_state = SystemState()
    system_state.id = "system_state"
    system_state.setup_status = SetupStatusEnum.TOKEN_GENERATED
    
    async with db_adapter.get_session() as session:
        session.add(system_state)
        await session.commit()
    
    # Generate setup token
    token_service = SetupTokenService()
    token = token_service.generate_token()
    token_hash = token_service.hash_token(token)
    
    # Store token in database
    await token_service.store_setup_token(token_hash, datetime.utcnow())
    
    # Log initialization
    security_logger.log_setup_token_generated(
        ip="cli",
        user_agent="setup-cli",
        token_hash=token_hash
    )
    
    # Print token to stdout only
    token_service.log_token_generation(token)


async def _async_check_status() -> dict:
    """Check setup status asynchronously."""
    async with db_adapter.get_session() as session:
        result = await session.execute(
            select(SystemState).where(SystemState.id == "system_state")
        )
        system_state = result.scalar_one_or_none()
    
    if not system_state:
        return {
            "setup_required": True,
            "setup_complete": False,
            "status": "not_initialized",
            "database_initialized": False,
            "admin_user_created": False,
            "system_configured": False,
            "setup_locked": False
        }
    
    return {
        "setup_required": not system_state.is_setup_complete(),
        "setup_complete": system_state.is_setup_complete(),
        "status": system_state.setup_status.value,
        "database_initialized": system_state.database_initialized,
        "admin_user_created": system_state.admin_user_created,
        "system_configured": system_state.system_configured,
        "setup_locked": system_state.setup_locked,
        "setup_attempts": system_state.setup_attempts,
        "last_setup_attempt": system_state.last_setup_attempt.isoformat() if system_state.last_setup_attempt else None,
        "setup_completed_at": system_state.setup_completed_at.isoformat() if system_state.setup_completed_at else None,
        "token_created_at": system_state.setup_token_created_at.isoformat() if system_state.setup_token_created_at else None,
    }


async def _async_generate_token() -> str:
    """Generate new setup token."""
    token_service = SetupTokenService()
    token = token_service.generate_token()
    token_hash = token_service.hash_token(token)
    
    await token_service.store_setup_token(token_hash, datetime.utcnow())
    
    # Log token generation
    security_logger = SecurityEventService()
    security_logger.log_setup_token_generated(
        ip="cli",
        user_agent="setup-cli",
        token_hash=token_hash
    )
    
    return token


async def _async_invalidate_token() -> bool:
    """Invalidate current setup token."""
    token_service = SetupTokenService()
    return await token_service.invalidate_setup_token()


async def _async_show_token_info():
    """Show current token information."""
    token_service = SetupTokenService()
    return await token_service.get_setup_token_info()


async def _async_lock_setup(reason: Optional[str]) -> bool:
    """Lock setup permanently."""
    security_logger = SecurityEventService()
    
    async with db_adapter.get_session() as session:
        result = await session.execute(
            select(SystemState).where(SystemState.id == "system_state")
        )
        system_state = result.scalar_one_or_none()
        
        if not system_state:
            return False
        
        system_state.lock_setup_permanently()
        await session.commit()
    
    # Log setup lock
    security_logger.log_setup_locked(
        ip="cli",
        user_agent="setup-cli"
    )
    
    return True


async def _async_reset_setup() -> bool:
    """Reset setup to initial state."""
    security_logger = SecurityEventService()
    
    async with db_adapter.get_session() as session:
        result = await session.execute(
            select(SystemState).where(SystemState.id == "system_state")
        )
        system_state = result.scalar_one_or_none()
        
        if system_state:
            system_state.reset_setup()
            await session.commit()
    
    # Generate new token
    token_service = SetupTokenService()
    token = token_service.generate_token()
    token_hash = token_service.hash_token(token)
    await token_service.store_setup_token(token_hash, datetime.utcnow())
    
    # Log reset
    security_logger.log_event("SETUP_RESET", {
        "reason": "cli_reset",
        "action": "setup_reset"
    })
    
    return True


async def _async_extend_expiry(days: int) -> bool:
    """Extend setup expiry window."""
    expiry_service = SetupExpiryService()
    return await expiry_service.extend_setup_window(days)


async def _async_check_expiry():
    """Check setup expiry status."""
    expiry_service = SetupExpiryService()
    return await expiry_service.get_setup_expiry_info()


async def _async_reset_expiry() -> bool:
    """Reset setup expiry timer."""
    expiry_service = SetupExpiryService()
    return await expiry_service.reset_setup_expiry()


async def _async_start_monitor():
    """Start expiry monitor."""
    expiry_service = SetupExpiryService()
    await expiry_service.start_expiry_monitor()
    
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        await expiry_service.stop_expiry_monitor()


async def _async_start_monitor_daemon():
    """Start expiry monitor as daemon."""
    expiry_service = SetupExpiryService()
    await expiry_service.start_expiry_monitor()
    
    # Run forever
    while True:
        await asyncio.sleep(3600)  # Check every hour


# Helper functions for output formatting

def _print_status(status: dict):
    """Print setup status in formatted output."""
    click.echo("\n📋 Setup Status:")
    click.echo(f"  Setup Required: {'✅ Yes' if status['setup_required'] else '❌ No'}")
    click.echo(f"  Setup Complete: {'✅ Yes' if status['setup_complete'] else '❌ No'}")
    click.echo(f"  Status: {status['status']}")
    click.echo(f"  Database Initialized: {'✅ Yes' if status['database_initialized'] else '❌ No'}")
    click.echo(f"  Admin User Created: {'✅ Yes' if status['admin_user_created'] else '❌ No'}")
    click.echo(f"  System Configured: {'✅ Yes' if status['system_configured'] else '❌ No'}")
    click.echo(f"  Setup Locked: {'✅ Yes' if status['setup_locked'] else '❌ No'}")
    
    if status.get('setup_completed_at'):
        click.echo(f"  Setup Completed: {status['setup_completed_at']}")
    
    if status.get('token_created_at'):
        click.echo(f"  Token Created: {status['token_created_at']}")


def _print_token_info(info: dict):
    """Print token information."""
    click.echo("\n🔑 Token Information:")
    click.echo(f"  Token Hash: {info['token_hash']}")
    click.echo(f"  Created At: {info['created_at']}")


def _print_expiry_info(info: dict):
    """Print expiry information."""
    click.echo("\n⏰ Expiry Information:")
    click.echo(f"  Setup Status: {info['setup_status']}")
    click.echo(f"  Token Created: {info['token_created_at']}")
    click.echo(f"  Expiry Date: {info['expiry_date']}")
    click.echo(f"  Time Remaining: {info['time_remaining_days']} days, {info['time_remaining_hours']} hours")
    click.echo(f"  Is Expired: {'✅ Yes' if info['is_expired'] else '❌ No'}")


# Register the setup group with the main CLI
def register_setup_commands(cli):
    """Register setup commands with the main CLI."""
    cli.add_command(setup_group)