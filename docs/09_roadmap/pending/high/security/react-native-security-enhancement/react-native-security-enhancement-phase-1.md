# Phase 1: Foundation Setup

## Overview
- **Phase**: 1/3
- **Status**: completed
- **Estimated Time**: 4 hours
- **Progress**: 100%
- **Completed**: 2025-10-28T16:20:07.000Z

## Objectives
- Build project detection for native apps
- Add mobile language detection to CodeQL
- Create scanner templates
- Test basic detection

## Tasks

### Task 1.1: Create Project Detector (1h)
- [ ] Create `scripts/project_detector.py`
- [ ] Add detection logic:
  - [ ] Check for `android/` folder
  - [ ] Check for `ios/` folder
  - [ ] Check for `package.json` with `react-native`
  - [ ] Check for `AndroidManifest.xml`
  - [ ] Check for `Info.plist`
- [ ] Return JSON results
- [ ] Add logging

### Task 1.2: Update Language Detection (1h)
- [ ] Update `scripts/tools/run_codeql.sh` lines 37-43
- [ ] Add Kotlin: `*.kt`, `*.kts`
- [ ] Add Swift: `*.swift`
- [ ] Add Objective-C: `*.m`, `*.mm`
- [ ] Test detection on sample apps

### Task 1.3: Create Android Scanner Template (1h)
- [ ] Create `scripts/tools/run_android_manifest_scanner.sh`
- [ ] Find `AndroidManifest.xml` files
- [ ] Add basic XML parsing
- [ ] Create output structure

### Task 1.4: Create iOS Scanner Template (1h)
- [ ] Create `scripts/tools/run_ios_plist_scanner.sh`
- [ ] Find `Info.plist` files
- [ ] Add basic plist parsing
- [ ] Create output structure

## Test Cases
- [ ] Expo React Native app
- [ ] Bare React Native app
- [ ] Android only project
- [ ] iOS only project
- [ ] Non-native project (should skip)

## Success Criteria
- [ ] Project detector works
- [ ] Language detection works
- [ ] Scanner templates exist
- [ ] All tests pass

## Dependencies
None

