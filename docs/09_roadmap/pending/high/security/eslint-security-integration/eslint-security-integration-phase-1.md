# ESLint Security Integration – Phase 1: Foundation Setup

## Overview
Set up the basic foundation for ESLint security integration by installing ESLint, security plugins, and creating configuration files.

## Objectives
- [ ] Install Node.js and npm in Docker container
- [ ] Install ESLint globally
- [ ] Install ESLint security plugins
- [ ] Create eslint/ configuration directory
- [ ] Add ESLint configuration file
- [ ] Set up ESLint environment variables in Dockerfile

## Deliverables
- File: `Dockerfile` - Updated with ESLint installation
- Directory: `eslint/` - ESLint configuration directory
- File: `eslint/config.yaml` - ESLint configuration file
- Environment variables: ESLint-related environment variables set up

## Dependencies
- Requires: None
- Blocks: Phase 2 - ESLint Script Creation

## Estimated Time
2 hours

## Success Criteria
- [ ] ESLint CLI installed and functional in Docker container
- [ ] ESLint security plugins installed
- [ ] ESLint configuration file created
- [ ] Environment variables set correctly
- [ ] ESLint can be run from command line

## Implementation Steps

### Step 1: Install Node.js and npm
```dockerfile
# Add to Dockerfile before Copy SimpleSecCheck files
# Install Node.js and npm for ESLint
RUN apt-get update && apt-get install -y nodejs npm
```

### Step 2: Install ESLint and Security Plugins
```dockerfile
# Install ESLint globally
RUN npm install -g eslint

# Install ESLint security plugins
RUN npm install -g eslint-plugin-security
RUN npm install -g eslint-config-security
RUN npm install -g @typescript-eslint/parser
RUN npm install -g @typescript-eslint/eslint-plugin
```

### Step 3: Create ESLint Configuration Directory
Create the directory structure:
```bash
mkdir -p eslint/
```

### Step 4: Create ESLint Configuration File
Create `eslint/config.yaml`:
```yaml
# ESLint Configuration for SimpleSecCheck

eslint:
  # Enable security rules
  security:
    enable_security_rules: true
    security_plugin: true
    
  # Output formats
  output:
    json: true
    text: true
    html: false
    
  # Severity levels to include
  severity:
    error: true
    warning: true
    info: true
    
  # File extensions to scan
  extensions:
    - .js
    - .jsx
    - .ts
    - .tsx
    
  # Additional configuration
  config:
    use_default: true
    custom_rules: []
```

### Step 5: Set Environment Variables
Add to Dockerfile:
```dockerfile
# Set ESLint environment variables
ENV ESLINT_CONFIG_PATH=/SimpleSecCheck/eslint/config.yaml
ENV ESLINT_NODE_HOME=/usr/bin/node
```

## Testing
- [ ] Build Docker image successfully
- [ ] Run ESLint from command line
- [ ] Verify ESLint security plugins are installed
- [ ] Test ESLint on sample JavaScript file

## Notes
- ESLint will be used for static code analysis of JavaScript and TypeScript files
- Security plugins will focus on detecting security vulnerabilities in JavaScript code
- Configuration follows the standard SimpleSecCheck pattern

