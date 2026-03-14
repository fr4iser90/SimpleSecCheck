# SimpleSecCheck Authentication Modes

This document explains the three authentication modes available in SimpleSecCheck and how to configure them.

## Overview

SimpleSecCheck supports three authentication modes, all based on sessions but with different login requirements:

1. **FREE Mode** (Default) - Public service, no login required
2. **BASIC Mode** - Username/password login required
3. **JWT Mode** - Token-based authentication (Enterprise)

## Configuration

### Environment Variables

Add these variables to your `.env` file:

```bash
# Authentication mode: free|basic|jwt
AUTH_MODE=free

# Whether login is required (derived from AUTH_MODE)
# FREE: false, BASIC/JWT: true
LOGIN_REQUIRED=false

# Session secret key for session management
SESSION_SECRET=your-session-secret-key-here
```

### Mode Descriptions

#### FREE Mode (Default)

**Configuration:**
```bash
AUTH_MODE=free
LOGIN_REQUIRED=false
```

**Features:**
- ✅ No login required
- ✅ Everyone gets automatic session
- ✅ Can start scans immediately
- ✅ Public security check service
- ✅ Rate limited for abuse prevention
- ✅ Guest sessions with 30-day cookie expiration

**Use Case:**
- Public security scanning service
- Open access for community use
- Quick security checks without barriers

**Example `.env` for FREE Mode:**
```bash
AUTH_MODE=free
LOGIN_REQUIRED=false
SESSION_SECRET=my-super-secret-session-key
```

#### BASIC Mode

**Configuration:**
```bash
AUTH_MODE=basic
LOGIN_REQUIRED=true
```

**Features:**
- 🔒 Username/password login required
- ✅ Session-based after login
- ✅ Controlled access
- ✅ User management capabilities
- ✅ Admin privileges for all authenticated users

**Use Case:**
- Corporate environments
- Closed user groups
- Organizations that want to control access

**Example `.env` for BASIC Mode:**
```bash
AUTH_MODE=basic
LOGIN_REQUIRED=true
SESSION_SECRET=my-super-secret-session-key
```

#### JWT Mode (Enterprise)

**Configuration:**
```bashash
AUTH_MODE=jwt
LOGIN_REQUIRED=true
```

**Features:**
- 🔒 Token-based authentication
- ✅ Integration with Keycloak, Auth0, Azure AD
- ✅ Enterprise SSO support
- ✅ Session-based with token validation
- ✅ Enterprise-grade security

**Use Case:**
- Enterprise environments
- Organizations with existing SSO
- High-security requirements

**Example `.env` for JWT Mode:**
```bash
AUTH_MODE=jwt
LOGIN_REQUIRED=true
SESSION_SECRET=my-super-secret-session-key
```

## API Endpoints

### Authentication Endpoints

All authentication modes support these endpoints:

- `POST /api/v1/auth/login` - Login (BASIC/JWT modes)
- `POST /api/v1/auth/logout` - Logout
- `GET /api/v1/auth/session` - Get session info
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/guest` - Create guest session

### Scan Endpoints

**FREE Mode:**
- All scan endpoints are publicly accessible
- No authentication required
- Automatic guest session creation

**BASIC/JWT Modes:**
- Scan endpoints require authentication
- Protected paths: `/api/v1/scans`, `/api/v1/results`, `/api/v1/queue`, `/api/v1/stats`
- Public paths: Auth endpoints, health check

## Session Management

### Session Creation

**FREE Mode:**
- Sessions created automatically on first request
- No login required
- Guest sessions with anonymous user ID

**BASIC Mode:**
- Sessions created after successful login
- Username/password authentication
- User ID based on authenticated user

**JWT Mode:**
- Sessions created after token validation
- Token-based authentication
- User ID extracted from JWT claims

### Session Storage

- Sessions stored in cookies (`session_id`)
- Cookie expiration: 30 days
- Secure cookies in production (HTTPS only)
- HttpOnly cookies for security

### Session Cleanup

- Automatic cleanup of expired sessions
- Guest sessions cleaned up after expiration
- No manual session management required

## Rate Limiting

All modes include rate limiting:

- **Guest users:** 100 requests/hour
- **Authenticated users:** 1000 requests/hour
- **Admin users:** 5000 requests/hour

Rate limits are enforced per session/user.

## Security Features

### FREE Mode Security
- Rate limiting to prevent abuse
- Guest session isolation
- No sensitive data access
- Public scan results only

### BASIC Mode Security
- Username/password authentication
- Session-based security
- User isolation
- Admin privileges for authenticated users

### JWT Mode Security
- Enterprise-grade token validation
- SSO integration support
- Claims-based authorization
- Enterprise session management

## Migration Between Modes

### FREE to BASIC/JWT
1. Update `AUTH_MODE` in `.env`
2. Restart services
3. Users will need to login
4. Existing guest sessions become invalid

### BASIC/JWT to FREE
1. Update `AUTH_MODE` in `.env`
2. Restart services
3. All endpoints become public
4. New guest sessions created automatically

## Troubleshooting

### Common Issues

**Sessions not persisting:**
- Check `SESSION_SECRET` is set
- Verify cookie settings in browser
- Ensure HTTPS in production

**Authentication failing:**
- Verify `AUTH_MODE` is correct
- Check login credentials (BASIC mode)
- Validate JWT tokens (JWT mode)

**Rate limiting too restrictive:**
- Adjust rate limits in middleware
- Monitor usage patterns
- Consider upgrading plan for higher limits

### Debug Mode

Enable debug logging to troubleshoot authentication issues:

```bash
LOG_LEVEL=DEBUG
```

Check logs for:
- Session creation/deletion
- Authentication attempts
- Rate limit violations
- Middleware processing

## Best Practices

### FREE Mode
- Monitor usage patterns
- Implement additional rate limiting if needed
- Consider implementing abuse detection
- Regularly review scan results

### BASIC Mode
- Use strong passwords
- Implement password policies
- Regular user account reviews
- Monitor login attempts

### JWT Mode
- Secure token storage
- Implement token rotation
- Validate token claims
- Monitor SSO integration health

## Example Configurations

### Public Service (FREE Mode)
```bash
# .env for public security scanning service
AUTH_MODE=free
LOGIN_REQUIRED=false
SESSION_SECRET=public-service-secret-key
RATE_LIMIT_PER_SESSION_REQUESTS=50
RATE_LIMIT_PER_IP_REQUESTS=500
```

### Corporate Environment (BASIC Mode)
```bash
# .env for corporate security scanning
AUTH_MODE=basic
LOGIN_REQUIRED=true
SESSION_SECRET=corporate-secret-key
RATE_LIMIT_PER_SESSION_REQUESTS=200
RATE_LIMIT_PER_IP_REQUESTS=1000
```

### Enterprise (JWT Mode)
```bash
# .env for enterprise security scanning
AUTH_MODE=jwt
LOGIN_REQUIRED=true
SESSION_SECRET=enterprise-secret-key
JWT_SECRET_KEY=enterprise-jwt-secret
JWT_ALGORITHM=RS256
```

## API Usage Examples

### FREE Mode - Start Scan
```bash
curl -X POST http://localhost:8080/api/v1/scans/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Public Scan",
    "scan_type": "repository",
    "target_url": "https://github.com/example/repo",
    "target_type": "git"
  }'
```

### BASIC Mode - Login and Scan
```bash
# Login
LOGIN_RESPONSE=$(curl -X POST http://localhost:8080/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

# Start scan with token
curl -X POST http://localhost:8080/api/v1/scans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Authenticated Scan",
    "scan_type": "repository",
    "target_url": "https://github.com/example/repo",
    "target_type": "git"
  }'
```

### JWT Mode - Token-based Scan
```bash
# Get token from your SSO provider
TOKEN="your-jwt-token-from-sso"

# Start scan with JWT
curl -X POST http://localhost:8080/api/v1/scans/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Enterprise Scan",
    "scan_type": "repository",
    "target_url": "https://github.com/example/repo",
    "target_type": "git"
  }'
```

This authentication system provides flexibility for different deployment scenarios while maintaining security and ease of use.