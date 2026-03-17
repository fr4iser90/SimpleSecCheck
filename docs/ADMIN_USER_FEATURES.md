# Admin & User Features Documentation

This document describes the admin and user features, GitHub integration, and API access for SimpleSecCheck.

## Table of Contents

1. [Header Navigation Structure](#header-navigation-structure)
2. [Admin Area Features](#admin-area-features)
3. [User Area Features](#user-area-features)
4. [GitHub Integration](#github-integration)
5. [API Access & Webhooks](#api-access--webhooks)
6. [UI/UX Guidelines](#uiux-guidelines)

---

## Header Navigation Structure

### Navigation Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 🛡️ SimpleSecCheck  [Scan Status]  [User Info] [Admin Menu]    │
│                                                                 │
│ Main Navigation:                                                 │
│ [New Scan] [My Scans] [My Repos] [Queue] [Statistics]          │
│                                                                 │
│ User Menu (Dropdown - appears when authenticated):             │
│   - Profile                                                     │
│   - My GitHub Repos                                             │
│   - API Keys                                                    │
│   - Logout                                                      │
│                                                                 │
│ Admin Menu (Dropdown - only for admins):                      │
│   - System Settings                                             │
│   - User Management                                             │
│   - Feature Flags                                               │
│   - Security Policies                                           │
│   - Audit Log                                                   │
│   - IP & Abuse Protection                                       │
│   - Scan Engine Management                                      │
│   - Vulnerability Database                                      │
│   - Scan Policies                                               │
│   - Notification Management                                     │
│   - System Health                                               │
└─────────────────────────────────────────────────────────────────┘
```

### Navigation Rules

- **Public (No Auth)**: New Scan, Queue (if enabled), Statistics
- **Authenticated Users**: All public + My Scans, My Repos, Profile, API Keys
- **Admins**: All user features + Admin menu items

---

## Admin Area Features

### 1. System Settings (`/admin/settings`)

**Purpose**: Configure system-wide settings and deployment mode.

**Features**:
- **Security Mode**: Toggle between Permissive/Restricted
  - Permissive: Allows local filesystem access (single-user only)
  - Restricted: No local filesystem access (multi-user safe)
- **Auth Mode**: Configure authentication
  - Free: No authentication required
  - Basic: Username/password authentication
  - JWT: Token-based authentication (SSO)
- **Scanner Configuration**:
  - Scanner Timeout (60-7200 seconds)
  - Max Concurrent Scans (1-20)
- **SMTP Configuration**:
  - Enable/disable SMTP
  - SMTP Host, Port, Username, Password
  - TLS/SSL settings
  - From Email/Name
- **Rate Limits**: Configure per user type
  - Guest users
  - Authenticated users
  - Admin users
- **Use Case Management**: View/change current deployment use case
  - Solo, Network Intern, Public Web, Enterprise

**Access**: Admin only

---

### 2. User Management (`/admin/users`)

**Purpose**: Manage user accounts, roles, and permissions.

**Features**:
- **User List View**:
  - Table with: Email, Role, Status, Created, Last Login
  - Search and filter functionality
  - Pagination
- **User Actions**:
  - Create new user
  - Edit user (email, role)
  - Delete user
  - Activate/deactivate user
  - Reset password (send reset email)
- **Role Management**:
  - Admin: Full system access
  - User: Standard user access (scans, repos, API keys)
- **User Details View**:
  - Profile information
  - Scan history
  - GitHub repos connected
  - API keys
  - Activity log

**Access**: Admin only

---

### 3. Feature Flags (`/admin/feature-flags`)

**Purpose**: Granular control over which target types are allowed.

**Features**:
- **Feature Flag Toggles**:
  - `ALLOW_LOCAL_PATHS`: Allow local filesystem paths as scan targets
  - `ALLOW_NETWORK_SCANS`: Allow network/website scans
  - `ALLOW_REMOTE_CONTAINERS`: Allow remote container scans
  - `ALLOW_GIT_REPOS`: Allow Git repository scans
  - `ALLOW_ZIP_UPLOAD`: Allow ZIP file uploads as scan targets
- **Live Preview**: See how changes affect available scan types
- **Use Case Override**: Override defaults for specific use cases
- **Validation**: Prevent invalid combinations (e.g., Restricted + Local Paths)

**Access**: Admin only

---

### 4. Security Policies (`/admin/security`)

**Purpose**: Manage security policies, use cases, and rate limits.

**Features**:
- **Use Case Configuration**:
  - View all available use cases
  - Edit use case defaults (Security Mode, Auth Mode, Feature Flags)
  - Create custom use cases
- **Rate Limit Management**:
  - Configure rate limits per use case
  - Per user type (guest, authenticated, admin)
  - Requests per hour
- **Security Mode Mapping**:
  - View mapping between Use Cases and Security Modes
  - Edit mappings
- **Audit Log**:
  - View security policy changes
  - Who changed what and when
  - Rollback capability

**Access**: Admin only

---

### 5. System Health (`/admin/health`)

**Purpose**: Monitor system status and resources.

**Features**:
- **Service Status**:
  - Database connection status
  - Redis connection status
  - Docker daemon status
- **Resource Usage**:
  - Disk space (used/available)
  - Memory usage
  - CPU usage (if available)
- **Active Operations**:
  - Currently running scans
  - Queue status
  - Active users
- **System Metrics**:
  - Total scans (today/week/month)
  - Average scan duration
  - Error rate
  - System uptime

**Access**: Admin only

---

### 6. Audit Log (`/admin/audit-log`)

**Purpose**: Centralized audit logging for all security-relevant events.

**Features**:
- **Event Tracking**:
  - User login/logout
  - API key creation/revocation
  - Admin configuration changes
  - Feature flag changes
  - Repository registration/removal
  - Webhook events
  - Failed authentication attempts
  - Security policy changes
  - User management actions
- **Event Details**:
  - Timestamp
  - User (who performed action)
  - Action type
  - Target (what was changed)
  - IP address
  - User agent
  - Result (success/failure)
- **Filtering & Search**:
  - Filter by user
  - Filter by action type
  - Filter by date range
  - Search by target/description
- **Export**:
  - Export audit log (CSV, JSON)
  - Retention policy configuration

**UI Example**:
```
┌─────────────────────────────────────────────────────────────┐
│ Audit Log                                    [Export] [Filter]│
├─────────────────────────────────────────────────────────────┤
│ Time        User        Action              Target           │
├─────────────────────────────────────────────────────────────┤
│ 10:22:15    admin       USER_CREATED        user@test.com   │
│ 10:25:30    admin       FEATURE_FLAG_CHANGED ALLOW_LOCAL_... │
│ 10:30:45    user123     REPO_ADDED          github.com/a/b  │
│ 10:31:12    system      SCAN_STARTED        scan_123        │
│ 10:32:00    user456     API_KEY_CREATED     api_key_789     │
│ 10:33:22    unknown     LOGIN_FAILED        192.168.1.100   │
└─────────────────────────────────────────────────────────────┘
```

**Event Types**:
- `USER_CREATED`, `USER_UPDATED`, `USER_DELETED`
- `USER_LOGIN`, `USER_LOGOUT`, `LOGIN_FAILED`
- `API_KEY_CREATED`, `API_KEY_REVOKED`
- `FEATURE_FLAG_CHANGED`
- `SECURITY_POLICY_CHANGED`
- `REPO_ADDED`, `REPO_REMOVED`, `REPO_UPDATED`
- `SCAN_STARTED`, `SCAN_COMPLETED`, `SCAN_FAILED`
- `WEBHOOK_RECEIVED`, `WEBHOOK_PROCESSED`
- `SYSTEM_SETTINGS_CHANGED`

**Access**: Admin only

---

### 7. IP & Abuse Protection (`/admin/security/ip-control`)

**Purpose**: Monitor and protect against abuse, brute force, and suspicious activity.

**Features**:
- **IP Monitoring**:
  - Blocked IPs list
  - Suspicious activity detection
  - Request spike detection
  - Brute force detection
  - Geographic location (optional)
- **IP Actions**:
  - Block IP (permanent or temporary)
  - Rate limit specific IP
  - Temporary ban (with expiration)
  - Whitelist IP
  - Unblock IP
- **Activity Dashboard**:
  - Failed login attempts per IP
  - Request rate per IP
  - Suspicious patterns
  - Geographic distribution
- **Auto-Block Rules**:
  - Auto-block after N failed logins
  - Auto-block on request spike (X requests in Y seconds)
  - Auto-block on suspicious patterns
- **Whitelist Management**:
  - Trusted IPs (never block)
  - Trusted networks (CIDR)

**UI Example**:
```
┌─────────────────────────────────────────────────────────────┐
│ IP Control & Abuse Protection                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Blocked IPs:                                                 │
│ 192.168.1.100  [Blocked]  Reason: Brute force  [Unblock]   │
│ 10.0.0.50      [Blocked]  Reason: Request spike [Unblock]  │
│                                                              │
│ Suspicious Activity:                                         │
│ 203.0.113.42   [Monitor]  15 failed logins in 5min        │
│                                                              │
│ [Block IP] [Whitelist IP] [View Statistics]                │
└─────────────────────────────────────────────────────────────┘
```

**Access**: Admin only

---

### 8. Scan Engine Management (`/admin/scanner`)

**Purpose**: Monitor and manage the scan engine, workers, and queue.

**Features**:
- **Engine Status**:
  - Workers running: X
  - Queue size: Y
  - Active scans: Z
  - Average scan time: Xm Ys
  - Timeouts today: N
  - Errors today: M
- **Worker Management**:
  - View worker status (healthy/unhealthy)
  - Restart worker
  - Pause scanning (stop processing new scans)
  - Resume scanning
  - Scale workers (if supported)
- **Queue Management**:
  - View queue contents
  - Queue position per scan
  - Estimated wait times
  - Clear queue (emergency)
  - Prioritize scan
- **Performance Metrics**:
  - Scans per hour
  - Average scan duration by type
  - Error rate
  - Timeout rate
  - Resource usage per worker
- **Debugging Tools**:
  - View worker logs
  - Test scanner connectivity
  - Validate scanner configuration

**UI Example**:
```
┌─────────────────────────────────────────────────────────────┐
│ Scan Engine Management                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Status:                                                      │
│ Workers: 4/4 running  [Restart All] [Pause] [Resume]       │
│ Queue: 12 scans waiting                                      │
│ Active: 3 scans running                                      │
│                                                              │
│ Metrics (Last 24h):                                          │
│ Average scan time: 3m 21s                                    │
│ Timeouts: 2                                                  │
│ Errors: 1                                                    │
│ Scans completed: 145                                        │
│                                                              │
│ [View Queue] [View Logs] [Test Connection]                  │
└─────────────────────────────────────────────────────────────┘
```

**Access**: Admin only

---

## User Area Features

### 1. My Scans (`/my-scans`)

**Purpose**: View and manage personal scan history.

**Features**:
- **Scan List**:
  - All scans created by the user
  - Filter by: Status, Scan Type, Date Range
  - Search by target URL/name
  - Sort by: Date, Status, Score
- **Scan Details**:
  - View scan results
  - Download reports (HTML, JSON)
  - View logs
  - Share scan results (if enabled)
- **Bulk Actions**:
  - Delete multiple scans
  - Export scan data

**Access**: Authenticated users

---

### 2. My Repos (`/my-repos`) - **NEW**

**Purpose**: Manage GitHub repositories with automatic scanning.

**Features**:
- **Repository Management**:
  - Add GitHub repository (URL or GitHub API)
  - Remove repository
  - Configure auto-scan settings
- **Repository List View**:
  ```
  ┌─────────────────────────────────────────────────────────┐
  │ My GitHub Repos                    [+ Add Repo]           │
  ├─────────────────────────────────────────────────────────┤
  │                                                           │
  │ 📦 user/repo1                    [Scanning...] ⏱️ 2m   │
  │    Last scan: 2h ago | Score: 85/100 | 12 vulnerabilities│
  │    Branch: main | Auto-scan: ON | Scan on push: ON      │
  │    [View Results] [Settings] [Remove]                    │
  │                                                           │
  │ 📦 user/repo2                    [Queued #3]            │
  │    Last scan: 1d ago | Score: 92/100 | 5 vulnerabilities│
  │    Branch: main | Auto-scan: ON | Scan on push: ON      │
  │    [View Results] [Settings] [Remove]                   │
  │                                                           │
  │ 📦 user/repo3                    [Idle]                 │
  │    Last scan: 3d ago | Score: 78/100 | 20 vulnerabilities│
  │    Branch: main | Auto-scan: OFF                         │
  │    [Scan Now] [Settings] [Remove]                        │
  │                                                           │
  └─────────────────────────────────────────────────────────┘
  ```
- **Repository Details**:
  - Scan history (timeline)
  - Score trends (chart)
  - Vulnerability trends
  - Branch information
  - Auto-scan configuration
- **Auto-Scan Settings**:
  - Enable/disable auto-scan
  - Scan frequency (on push, daily, weekly, manual)
  - Branch selection
  - Scan on pull requests (optional)

**Access**: Authenticated users

---

### 3. Profile (`/profile`)

**Purpose**: Manage user account and preferences.

**Features**:
- **Account Information**:
  - Email address (editable)
  - Username
  - Account created date
  - Last login
- **Password Management**:
  - Change password
  - Password requirements display
- **GitHub Integration**:
  - Connect GitHub account (OAuth or Personal Access Token)
  - View connected repositories
  - Disconnect GitHub
- **API Keys**:
  - View all API keys
  - Create new API key
  - Revoke API key
  - Key usage statistics
- **Preferences**:
  - Email notifications (scan complete, vulnerabilities found)
  - Default scan settings
  - Language preference

**Access**: Authenticated users

---

## GitHub Integration

### Overview

The GitHub integration allows users to automatically scan their repositories when code changes are pushed. The system uses a "round-robin" (Reißverschluss) approach to ensure fair resource distribution.

### Architecture

#### 1. Repository Registration

**User Flow**:
1. User navigates to `/my-repos`
2. Clicks "Add Repo"
3. Enters GitHub repository URL or selects from connected GitHub account
4. Configures auto-scan settings
5. System validates repository access
6. Repository is added to user's repo list

**API Endpoint**:
```
POST /api/user/github/repos
{
  "repo_url": "https://github.com/user/repo",
  "branch": "main",
  "auto_scan": true,
  "scan_on_push": true,
  "scan_on_pr": false,
  "github_token": "optional-if-oauth-connected"
}
```

#### 2. Auto-Scan System (Round-Robin)

**Principle**: One scan per user at a time, fair distribution across all users.

**Algorithm**:
```
1. User A has 3 repos → Queue: [repo1, repo2, repo3]
2. User B has 2 repos → Queue: [repo1, repo2]
3. User C has 1 repo → Queue: [repo1]

Scan Order (Round-Robin):
- User A: repo1 (scanning)
- User B: repo1 (queued)
- User C: repo1 (queued)
- User A: repo2 (queued, after repo1 completes)
- User B: repo2 (queued, after User A's repo2)
- User A: repo3 (queued, after User B's repo2)
```

**Implementation**:
- Each user has a personal queue
- Global queue manager ensures one scan per user at a time
- When user's current scan completes → next repo from their queue
- If user has no queued repos → skip to next user

**Benefits**:
- Fair resource distribution
- No user can monopolize the system
- Predictable wait times
- Users can see their position in queue

#### 3. Webhook Integration

**GitHub Webhook Setup**:
1. User connects GitHub account or provides Personal Access Token
2. System creates webhook in GitHub repository
3. Webhook URL: `https://your-domain.com/api/webhooks/github`
4. Events: `push`, `pull_request` (optional)

**Webhook Payload Handling**:
```json
{
  "ref": "refs/heads/main",
  "repository": {
    "full_name": "user/repo",
    "clone_url": "https://github.com/user/repo.git"
  },
  "commits": [...],
  "action": "opened" // for pull requests
}
```

**Processing**:
1. Validate webhook signature (GitHub secret)
2. Check if repository is registered for auto-scan
3. Check if event should trigger scan (push/PR)
4. Add to user's personal queue
5. Process via round-robin system

#### 4. Repository Dashboard

**Features**:
- **Score Overview**: Current security score (0-100)
- **Trend Chart**: Score over time
- **Vulnerability Breakdown**:
  - Critical: X
  - High: Y
  - Medium: Z
  - Low: W
- **Recent Scans**: Last 10 scans with results
- **Branch Information**: Which branches are monitored
- **Auto-Scan Status**: Enabled/disabled, next scan time

**Score Calculation**:
```
Score = 100 - (critical * 10 + high * 5 + medium * 2 + low * 1)
Max penalty: 100 points
```

---

## API Access & Webhooks

### API Key Management

**Endpoints**:
```
GET  /api/user/api-keys          → List all API keys for user
POST /api/user/api-keys          → Create new API key
     {
       "name": "My API Key",
       "expires_in_days": 90  // optional, null = never expires
     }
DELETE /api/user/api-keys/:id    → Revoke API key
```

**API Key Format**:
```
ssc_<user_id>_<random_32_chars>
Example: ssc_abc123_4f8a9b2c3d4e5f6a7b8c9d0e1f2a3b4c
```

**Usage**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -X POST https://your-domain.com/api/scans \
     -d '{"target": "https://github.com/user/repo", "scan_type": "code"}'
```
Replace `YOUR_API_KEY` with your actual API key (e.g. from Setup or API keys page).

### Webhook Endpoints

#### 1. GitHub Webhook (`/api/webhooks/github`)

**Purpose**: Receive GitHub push/PR events and trigger scans.

**Authentication**: GitHub webhook secret (HMAC signature)

**Payload Example**:
```json
{
  "ref": "refs/heads/main",
  "repository": {
    "full_name": "user/repo",
    "clone_url": "https://github.com/user/repo.git"
  },
  "commits": [
    {
      "id": "abc123",
      "message": "Fix security issue",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Response**:
```json
{
  "status": "queued",
  "scan_id": "scan_xyz789",
  "queue_position": 3,
  "estimated_wait": 300  // seconds
}
```

#### 2. GitLab Webhook (`/api/webhooks/gitlab`)

**Purpose**: Receive GitLab push events.

**Authentication**: GitLab webhook token

**Similar structure to GitHub webhook**

#### 3. Generic Webhook (`/api/webhooks/generic`)

**Purpose**: Generic webhook for any Git service or CI/CD.

**Authentication**: API Key in header

**Payload**:
```json
{
  "event": "push",
  "repo_url": "https://github.com/user/repo",
  "branch": "main",
  "commit": "abc123",
  "user_id": "optional-if-api-key-provided"
}
```

### Pre-Commit Hook Integration

**Use Case**: Scan code before commit (via ZIP upload).

**Flow**:
1. Pre-commit hook triggers
2. Creates ZIP of changed files
3. POST to `/api/webhooks/pre-commit` with ZIP
4. System scans ZIP
5. Returns results
6. Pre-commit hook blocks commit if critical vulnerabilities found

**Endpoint**:
```
POST /api/webhooks/pre-commit
Content-Type: multipart/form-data

{
  "zip_file": <binary>,
  "repo_url": "https://github.com/user/repo",
  "branch": "feature-branch",
  "commit_message": "Add new feature"
}
```

**Response**:
```json
{
  "scan_id": "scan_xyz",
  "status": "completed",
  "score": 85,
  "critical_vulnerabilities": 0,
  "high_vulnerabilities": 2,
  "should_block": false  // true if critical > 0
}
```

---

## UI/UX Guidelines

### Navigation Structure

**Main Navigation** (always visible):
- **New Scan**: Start a new security scan
- **My Scans**: View personal scan history
- **My Repos**: Manage GitHub repositories (if authenticated)
- **Queue**: View scan queue (if enabled)
- **Statistics**: View system statistics (if production mode)

**User Menu** (dropdown, authenticated users):
- Profile
- My GitHub Repos
- API Keys
- Logout

**Admin Menu** (dropdown, admin only):
- System Settings
- User Management
- Feature Flags
- Security Policies
- System Health

### Page Organization

**User Pages**:
- `/` - New Scan (HomePage)
- `/my-scans` - Personal scan history
- `/my-repos` - GitHub repository management
- `/profile` - User profile and settings
- `/queue` - Scan queue view
- `/statistics` - Statistics dashboard

**Admin Pages**:
- `/admin/settings` - System settings
- `/admin/users` - User management
- `/admin/feature-flags` - Feature flag management
- `/admin/security` - Security policies
- `/admin/audit-log` - Centralized audit log
- `/admin/security/ip-control` - IP & abuse protection
- `/admin/scanner` - Scan engine management
- `/admin/vulnerabilities` - Vulnerability database
- `/admin/scan-policies` - Scan templates/policies
- `/admin/notifications` - Notification management
- `/admin/health` - System health monitoring

### Design Principles

1. **Clear Hierarchy**: Admin features clearly separated from user features
2. **Progressive Disclosure**: Advanced features in dropdowns/sidebars
3. **Contextual Actions**: Actions available where they're needed
4. **Status Indicators**: Clear visual feedback for scan status, queue position
5. **Responsive Design**: Works on desktop and mobile

---

## Advanced Admin Features

### 9. Vulnerability Database (`/admin/vulnerabilities`)

**Purpose**: Centralized management of known vulnerabilities, suppression rules, and custom security rules.

**Features**:
- **Vulnerability Management**:
  - View known vulnerabilities database
  - Add custom vulnerabilities
  - Update vulnerability severity
  - Mark as false positive
- **Suppression Rules**:
  - Create suppression rules (ignore specific findings)
  - Suppress by path pattern
  - Suppress by vulnerability ID
  - Suppress by severity
  - Time-based suppressions (expire after X days)
- **False Positive Management**:
  - Mark findings as false positives
  - Learn from false positives (improve rules)
  - False positive patterns
- **Custom Security Rules**:
  - Create custom security rules
  - Edit rule severity
  - Enable/disable rules
  - Rule categories (secrets, dependencies, SAST, etc.)

**UI Example**:
```
┌─────────────────────────────────────────────────────────────┐
│ Vulnerability Database                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Rules:                                                       │
│ Hardcoded secrets        [High]  [Enabled]  [Edit] [Disable]│
│ Weak cryptography        [Medium] [Enabled] [Edit] [Disable]│
│ SQL injection            [Critical] [Enabled] [Edit]        │
│                                                              │
│ Suppressions:                                               │
│ /test/**                  [Active]  [Expires: Never]        │
│ CVE-2024-1234             [Active]  [Expires: 2024-12-31]  │
│                                                              │
│ [Add Rule] [Add Suppression] [Import Rules]                  │
└─────────────────────────────────────────────────────────────┘
```

**Access**: Admin only

---

### 10. Scan Templates / Policies (`/admin/scan-policies`)

**Purpose**: Define reusable scan templates that users can select when starting scans.

**Features**:
- **Policy Management**:
  - Create scan policies/templates
  - Edit existing policies
  - Delete policies
  - Set as default policy
- **Policy Configuration**:
  - Policy name and description
  - Enabled scanners (secrets, dependency, SAST, container, etc.)
  - Scan depth (quick, medium, deep)
  - Timeout settings
  - Severity thresholds
  - Custom rules to include/exclude
- **Policy Examples**:
  - **Default Web Scan**: secrets + dependency + container scan
  - **Strict Policy**: secrets + dependency + license + SAST scan
  - **Quick Scan**: secrets scan only
  - **Comprehensive Scan**: All scanners enabled
- **User Selection**:
  - Users can select policy when starting scan
  - Default policy for new scans
  - Policy-specific rate limits (optional)

**UI Example**:
```
┌─────────────────────────────────────────────────────────────┐
│ Scan Policies / Templates                                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Default Web Scan                    [Default] [Edit] [Delete]│
│   Scanners: secrets, dependency, container                  │
│   Depth: Medium | Timeout: 3600s                            │
│                                                              │
│ Strict Policy                      [Edit] [Delete]         │
│   Scanners: secrets, dependency, license, SAST             │
│   Depth: Deep | Timeout: 7200s                              │
│                                                              │
│ Quick Scan                         [Edit] [Delete]         │
│   Scanners: secrets only                                    │
│   Depth: Quick | Timeout: 600s                              │
│                                                              │
│ [Create New Policy]                                          │
└─────────────────────────────────────────────────────────────┘
```

**User Experience**:
When user starts scan, they see:
```
Scan Policy: [Dropdown: Default Web Scan ▼]
  - Default Web Scan
  - Strict Policy
  - Quick Scan
  - Comprehensive Scan
```

**Access**: Admin only

---

### 11. Notification Management (`/admin/notifications`)

**Purpose**: Configure notification channels and rules for system events.

**Features**:
- **Notification Channels**:
  - Email (SMTP)
  - Slack (webhook)
  - Discord (webhook)
  - Generic webhook
  - Custom integrations
- **Event Configuration**:
  - Scan completed
  - Critical vulnerability found
  - High vulnerability found
  - System error
  - User action required
  - Security alert
- **Notification Rules**:
  - Per-channel configuration
  - Per-event configuration (which events trigger which channels)
  - Severity filters (only notify on critical/high)
  - Rate limiting (don't spam)
  - Template customization
- **Test Notifications**:
  - Test each channel
  - Preview notification format
  - Verify webhook connectivity

**UI Example**:
```
┌─────────────────────────────────────────────────────────────┐
│ Notification Management                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Channels:                                                    │
│ Email (SMTP)              [Configured] [Test] [Edit]        │
│ Slack                     [Not configured] [Setup]         │
│ Discord                   [Not configured] [Setup]         │
│                                                              │
│ Event Rules:                                                 │
│ Scan Completed            [Email ✓] [Slack ✗] [Discord ✗]  │
│ Critical Vulnerability     [Email ✓] [Slack ✓] [Discord ✓]│
│ High Vulnerability         [Email ✓] [Slack ✗] [Discord ✗]  │
│ System Error               [Email ✓] [Slack ✓] [Discord ✓] │
│                                                              │
│ [Add Channel] [Test All] [Edit Templates]                   │
└─────────────────────────────────────────────────────────────┘
```

**Access**: Admin only

---

## Implementation Roadmap

### Phase 1: Core Admin Area (Priority: High)
- [ ] System Settings page
- [ ] User Management page
- [ ] Feature Flags page
- [ ] Header navigation with admin menu
- [ ] Audit Log page (centralized)

### Phase 2: Security & Monitoring (Priority: High)
- [ ] IP & Abuse Protection page
- [ ] Scan Engine Management page
- [ ] System Health page enhancements

### Phase 3: User Repos (Priority: High)
- [ ] My Repos page
- [ ] GitHub repository registration
- [ ] Repository dashboard with scores
- [ ] Auto-scan configuration

### Phase 4: Auto-Scan System (Priority: Medium)
- [ ] Round-robin queue system
- [ ] GitHub webhook integration
- [ ] Auto-scan scheduler
- [ ] Queue position tracking

### Phase 5: API & Webhooks (Priority: Medium)
- [ ] API key management
- [ ] GitHub webhook endpoint
- [ ] Generic webhook endpoint
- [ ] Pre-commit hook support

### Phase 6: Advanced Features (Priority: Medium)
- [ ] Vulnerability Database management
- [ ] Scan Templates / Policies
- [ ] Notification Management
- [ ] Custom security rules

### Phase 7: Integrations (Priority: Low)
- [ ] GitLab integration
- [ ] Bitbucket integration
- [ ] CI/CD integration (GitHub Actions, GitLab CI)
- [ ] Slack/Discord notifications

---

## Security Considerations

### Admin Access
- Only users with `admin` role can access admin pages
- All admin actions logged in audit log
- Sensitive operations require confirmation

### API Keys
- Keys stored hashed (never plaintext)
- Keys can be revoked immediately
- Rate limiting per API key
- Usage tracking and monitoring

### Webhooks
- GitHub webhooks validated with HMAC signature
- Generic webhooks require API key authentication
- Webhook payloads validated and sanitized
- Rate limiting on webhook endpoints

### GitHub Integration
- Personal Access Tokens stored encrypted
- OAuth tokens refreshed automatically
- Repository access validated before scanning
- User can only manage their own repositories

---

## Database Schema Additions

### New Tables Needed

```sql
-- User GitHub repositories
CREATE TABLE user_github_repos (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    repo_url TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    branch TEXT DEFAULT 'main',
    auto_scan BOOLEAN DEFAULT false,
    scan_on_push BOOLEAN DEFAULT true,
    scan_on_pr BOOLEAN DEFAULT false,
    github_token_encrypted TEXT,  -- Encrypted GitHub token
    last_scan_id UUID,
    last_scan_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    key_hash TEXT NOT NULL,  -- Hashed API key
    key_prefix TEXT NOT NULL,  -- First 8 chars for display
    name TEXT,
    expires_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Webhook Events
CREATE TABLE webhook_events (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    event_type TEXT NOT NULL,  -- 'github_push', 'gitlab_push', 'generic'
    repo_url TEXT,
    payload JSONB,
    scan_id UUID,
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Repository Scan History
CREATE TABLE repo_scan_history (
    id UUID PRIMARY KEY,
    repo_id UUID REFERENCES user_github_repos(id),
    scan_id UUID REFERENCES scans(id),
    branch TEXT,
    commit_hash TEXT,
    score INTEGER,  -- 0-100
    vulnerabilities JSONB,  -- {critical: 0, high: 2, medium: 5, low: 10}
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints Summary

### User Repos
```
GET    /api/user/github/repos              → List user's repos
POST   /api/user/github/repos              → Add new repo
GET    /api/user/github/repos/:id          → Get repo details
PUT    /api/user/github/repos/:id          → Update repo settings
DELETE /api/user/github/repos/:id          → Remove repo
POST   /api/user/github/repos/:id/scan     → Trigger manual scan
GET    /api/user/github/repos/:id/history  → Get scan history
```

### API Keys
```
GET    /api/user/api-keys                  → List API keys
POST   /api/user/api-keys                  → Create API key
DELETE /api/user/api-keys/:id              → Revoke API key
GET    /api/user/api-keys/:id/usage        → Get usage statistics
```

### Webhooks
```
POST   /api/webhooks/github                → GitHub webhook
POST   /api/webhooks/gitlab                → GitLab webhook
POST   /api/webhooks/generic               → Generic webhook
POST   /api/webhooks/pre-commit            → Pre-commit hook
```

### Admin
```
GET    /api/admin/users                    → List all users
POST   /api/admin/users                    → Create user
PUT    /api/admin/users/:id                → Update user
DELETE /api/admin/users/:id                → Delete user
GET    /api/admin/feature-flags            → Get feature flags
PUT    /api/admin/feature-flags            → Update feature flags
GET    /api/admin/health                   → System health
GET    /api/admin/audit-log                → Audit log (filtered, paginated)
POST   /api/admin/audit-log/export         → Export audit log
GET    /api/admin/security/ip-control       → IP control dashboard
POST   /api/admin/security/ip-control/block → Block IP
POST   /api/admin/security/ip-control/unblock → Unblock IP
GET    /api/admin/scanner                  → Scanner engine status
POST   /api/admin/scanner/pause            → Pause scanning
POST   /api/admin/scanner/resume           → Resume scanning
POST   /api/admin/scanner/restart-worker   → Restart worker
GET    /api/admin/vulnerabilities          → List vulnerabilities/rules
POST   /api/admin/vulnerabilities          → Create custom rule
PUT    /api/admin/vulnerabilities/:id      → Update rule
DELETE /api/admin/vulnerabilities/:id       → Delete rule
POST   /api/admin/vulnerabilities/suppress → Create suppression
GET    /api/admin/scan-policies            → List scan policies
POST   /api/admin/scan-policies            → Create policy
PUT    /api/admin/scan-policies/:id        → Update policy
DELETE /api/admin/scan-policies/:id        → Delete policy
GET    /api/admin/notifications            → Get notification config
PUT    /api/admin/notifications            → Update notification config
POST   /api/admin/notifications/test       → Test notification channel
```

---

## Next Steps

1. **Review this documentation** and provide feedback
2. **Prioritize features** for implementation
3. **Create database migrations** for new tables
4. **Implement backend API endpoints**
5. **Build frontend pages** (Admin + User areas)
6. **Implement GitHub integration**
7. **Add webhook support**
8. **Test round-robin queue system**

---

**Last Updated**: 2024-01-15
**Version**: 1.1

## Changelog

### Version 1.1 (2024-01-15)
- Added centralized Audit Log (`/admin/audit-log`)
- Added IP & Abuse Protection (`/admin/security/ip-control`)
- Added Scan Engine Management (`/admin/scanner`)
- Added Vulnerability Database (`/admin/vulnerabilities`)
- Added Scan Templates / Policies (`/admin/scan-policies`)
- Added Notification Management (`/admin/notifications`)
- Extended database schema with new tables
- Added API endpoints for new features
