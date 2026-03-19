"""
Email Service

Handles sending emails via SMTP for password resets and notifications.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from infrastructure.logging_config import get_logger

logger = get_logger("api.services.email")


class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self):
        from config.settings import get_settings
        self.settings = get_settings()
        self.enabled = self.settings.SMTP_ENABLED
        self._load_smtp_config_from_db()
    
    def _load_smtp_config_from_db(self):
        """Load SMTP config from SystemState via repository if available."""
        try:
            import asyncio

            async def get_config():
                try:
                    from infrastructure.container import get_system_state_repository
                    repo = get_system_state_repository()
                    state = await repo.get_singleton()
                    if state and state.config:
                        smtp_config = state.config.get("smtp")
                        if smtp_config and smtp_config.get("enabled"):
                            self.settings.SMTP_ENABLED = True
                            self.settings.SMTP_HOST = smtp_config.get("host", self.settings.SMTP_HOST)
                            self.settings.SMTP_PORT = smtp_config.get("port", self.settings.SMTP_PORT)
                            self.settings.SMTP_USER = smtp_config.get("user", self.settings.SMTP_USER)
                            self.settings.SMTP_PASSWORD = smtp_config.get("password", self.settings.SMTP_PASSWORD)
                            self.settings.SMTP_USE_TLS = smtp_config.get("use_tls", self.settings.SMTP_USE_TLS)
                            self.settings.SMTP_FROM_EMAIL = smtp_config.get("from_email", self.settings.SMTP_FROM_EMAIL)
                            self.settings.SMTP_FROM_NAME = smtp_config.get("from_name", self.settings.SMTP_FROM_NAME)
                            self.enabled = True
                except Exception as e:
                    logger.debug("Could not load SMTP config from DB", error=str(e))

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(get_config())
                else:
                    loop.run_until_complete(get_config())
            except RuntimeError:
                pass
        except Exception as e:
            logger.debug("Could not load SMTP config from DB", error=str(e))
    
    def is_enabled(self) -> bool:
        """Check if email service is enabled."""
        return self.enabled and bool(self.settings.SMTP_HOST and self.settings.SMTP_USER)
    
    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        reset_url: str
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            to_email: Recipient email address
            reset_token: Password reset token
            reset_url: Full URL for password reset
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Email service not enabled, cannot send password reset email")
            return False
        
        subject = "Password Reset Request - SimpleSecCheck"
        body = f"""
Hello,

You have requested to reset your password for SimpleSecCheck.

Click the following link to reset your password:
{reset_url}

This link will expire in {self.settings.PASSWORD_RESET_TOKEN_EXPIRY_HOURS} hour(s).

If you did not request this password reset, please ignore this email.

Best regards,
SimpleSecCheck Team
"""
        
        html_body = f"""
<html>
  <body>
    <h2>Password Reset Request</h2>
    <p>Hello,</p>
    <p>You have requested to reset your password for SimpleSecCheck.</p>
    <p>
      <a href="{reset_url}" style="background-color: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
        Reset Password
      </a>
    </p>
    <p>Or copy and paste this link into your browser:</p>
    <p style="word-break: break-all;">{reset_url}</p>
    <p>This link will expire in {self.settings.PASSWORD_RESET_TOKEN_EXPIRY_HOURS} hour(s).</p>
    <p>If you did not request this password reset, please ignore this email.</p>
    <p>Best regards,<br>SimpleSecCheck Team</p>
  </body>
</html>
"""
        
        return await self._send_email(
            to_email=to_email,
            subject=subject,
            text_body=body,
            html_body=html_body
        )
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: Optional[str] = None
    ) -> bool:
        """
        Send email via SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            text_body: Plain text email body
            html_body: Optional HTML email body
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.settings.SMTP_FROM_NAME} <{self.settings.SMTP_FROM_EMAIL}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add text part
            text_part = MIMEText(text_body, 'plain')
            msg.attach(text_part)
            
            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                if self.settings.SMTP_USE_TLS:
                    server.starttls()
                
                if self.settings.SMTP_USER and self.settings.SMTP_PASSWORD:
                    server.login(self.settings.SMTP_USER, self.settings.SMTP_PASSWORD)
                
                server.send_message(msg)
            
            logger.info("Password reset email sent", email=to_email)
            return True
            
        except Exception as e:
            logger.error("Failed to send email", error=str(e), email=to_email)
            return False
    
    def get_reset_url(self, token: str) -> str:
        """
        Generate password reset URL.
        
        Args:
            token: Password reset token
            
        Returns:
            Full URL for password reset
        """
        base_url = getattr(self.settings, "FRONTEND_BASE_URL", None) or "http://localhost:8080"
        return f"{base_url}/password-reset?token={token}"

    def get_verify_email_url(self, token: str) -> str:
        """
        Generate email verification URL (for sign-up verification email).
        
        Args:
            token: Email verification token
            
        Returns:
            Full URL for verify-email page
        """
        base_url = getattr(self.settings, "FRONTEND_BASE_URL", None) or "http://localhost:8080"
        return f"{base_url}/verify-email?token={token}"

    async def send_verification_email(
        self,
        to_email: str,
        verify_url: str,
        expiry_hours: int = 24,
    ) -> bool:
        """
        Send email verification email (after sign-up).
        
        Args:
            to_email: Recipient email address
            verify_url: Full URL for verification link
            expiry_hours: Token expiry in hours (for message text)
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Email service not enabled, cannot send verification email")
            return False

        subject = "Verify your email - SimpleSecCheck"
        body = f"""
Hello,

Thank you for signing up for SimpleSecCheck.

Please verify your email address by clicking the link below:
{verify_url}

This link will expire in {expiry_hours} hour(s).

If you did not create an account, please ignore this email.

Best regards,
SimpleSecCheck Team
"""
        html_body = f"""
<html>
  <body>
    <h2>Verify your email</h2>
    <p>Thank you for signing up for SimpleSecCheck.</p>
    <p>Please verify your email address by clicking the button below:</p>
    <p>
      <a href="{verify_url}" style="background-color: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
        Verify Email
      </a>
    </p>
    <p>Or copy and paste this link into your browser:</p>
    <p style="word-break: break-all;">{verify_url}</p>
    <p>This link will expire in {expiry_hours} hour(s).</p>
    <p>If you did not create an account, please ignore this email.</p>
    <p>Best regards,<br>SimpleSecCheck Team</p>
  </body>
</html>
"""
        return await self._send_email(
            to_email=to_email,
            subject=subject,
            text_body=body,
            html_body=html_body,
        )
