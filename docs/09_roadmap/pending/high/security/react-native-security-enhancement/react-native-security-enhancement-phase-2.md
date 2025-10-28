# Phase 2: Core Implementation

## Overview
- **Phase**: 2/3
- **Status**: completed
- **Estimated Time**: 5 hours
- **Progress**: 100%
- **Completed**: 2025-10-28T16:20:07.000Z

## Objectives
- Build Android manifest security scanner
- Build iOS plist security scanner
- Create processors for findings
- Test with real apps

## Tasks

### Task 2.1: Android Manifest Scanner (2h)
- [ ] Update `run_android_manifest_scanner.sh`
- [ ] Parse XML with ElementTree
- [ ] Extract permissions:
  - [ ] INTERNET usage
  - [ ] CALL_PHONE usage
  - [ ] SEND_SMS usage
  - [ ] WRITE_EXTERNAL_STORAGE usage
  - [ ] CAMERA usage
- [ ] Check cleartext traffic
- [ ] Check backup enabled
- [ ] Check debug mode
- [ ] Generate JSON output

### Task 2.2: Android Processor (1h)
- [ ] Create `scripts/android_manifest_processor.py`
- [ ] Parse JSON findings
- [ ] Build HTML report section
- [ ] Add severity levels
- [ ] Add fix suggestions

### Task 2.3: iOS Plist Scanner (1.5h)
- [ ] Update `run_ios_plist_scanner.sh`
- [ ] Parse plist with plistlib
- [ ] Check for security issues:
  - [ ] NSAllowsArbitraryLoads (HTTP allowed)
  - [ ] NSAppTransportSecurity misconfig
  - [ ] Weak encryption settings
  - [ ] Debug settings in production
  - [ ] Keychain usage
- [ ] Check ATS configuration
- [ ] Generate JSON output

### Task 2.4: iOS Processor (0.5h)
- [ ] Create `scripts/ios_plist_processor.py`
- [ ] Parse JSON findings
- [ ] Build HTML report section
- [ ] Add severity levels
- [ ] Add fix suggestions

## Security Rules

### Android Checks:
1. Dangerous permissions usage
2. Cleartext traffic allowed
3. Backup enabled (data leakage)
4. Debug mode in production
5. No certificate pinning
6. Insecure WebView configs

### iOS Checks:
1. Arbitrary loads allowed (HTTP)
2. Weak ATS setup
3. Keychain sharing issues
4. Debug settings enabled
5. Insecure URL schemes
6. No jailbreak detection

## Test Cases
- [ ] Manifest with dangerous permissions
- [ ] Cleartext traffic enabled
- [ ] ATS disabled
- [ ] Multiple manifest/plist files
- [ ] Malformed files (graceful handling)

## Success Criteria
- [ ] Android scanner finds issues
- [ ] iOS scanner finds issues
- [ ] Processors generate HTML
- [ ] Security rules work
- [ ] Error handling works

## Dependencies
- Phase 1 must be completed

