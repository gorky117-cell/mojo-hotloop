# Maintainer Notification Architecture & GitHub Configuration

**Maintainer:** Gaurav Kumar Singh (`@gorky117-cell`)  
**Repository:** `gorky117-cell/mojo-hotloop`

This document defines how GitHub-native notifications, review routing, and security alerts are configured to ensure critical project events reach the maintainer without notification fatigue.

---

## 1. Native Routing Mechanisms

### A. Automatic Code Review Routing (`.github/CODEOWNERS`)
The repository specifies:
```text
* @gorky117-cell
```
- **How it works**: Whenever an external contributor opens a pull request against `main`, GitHub automatically requests review from `@gorky117-cell`.
- **Result**: The maintainer receives an immediate GitHub notification and email (depending on account preferences) without requiring manual PR assignment.

### B. CI Failure Notifications (`.github/workflows/ci.yml`)
- GitHub Actions automatically notifies the repository maintainer and commit author whenever a workflow run fails on `main` or an official pull request.
- Routine successful workflow runs do **not** trigger emails, keeping inbox noise minimal.

### C. Automated Contributor Assistant (`.github/workflows/contributor-assistant.yml`)
- Runs only on `pull_request_target: types: [opened]`.
- Checks for DCO sign-off and provides deterministic onboarding instructions.
- Skips comments when the PR is opened by `@gorky117-cell`.
- Posts at most one comment per PR to avoid comment spam.

### D. Private Security Vulnerability Alerts
- When a researcher submits a private vulnerability disclosure via GitHub Security Advisories, GitHub routes confidential alerts directly to repository administrators.

---

## 2. Recommended Account Notification Settings for Maintainer

To ensure zero missed events while avoiding routine noise:

1. **Repository Watch Settings**:
   - Navigate to [`https://github.com/gorky117-cell/mojo-hotloop`](https://github.com/gorky117-cell/mojo-hotloop).
   - Click the **Watch** button at the top right.
   - Select **Custom**:
     - [x] **Issues** (notified when bugs or feature proposals are filed)
     - [x] **Pull requests** (notified when external PRs are opened)
     - [x] **Discussions** (notified when community questions are asked)
     - [x] **Security alerts** (notified of dependabot / secret scanning / advisories)
   - Click **Apply**.

2. **Global Notification Settings**:
   - Go to [GitHub Notification Settings](https://github.com/settings/notifications).
   - Under **Watching**: Ensure notifications are enabled via **Email** and/or **Web**.
   - Under **Automatically watch**: Check "Automatically watch repositories when you are given push access".
   - Under **Actions**: Enable notifications for "Only failures" to suppress emails for successful CI jobs.

---

## 3. Event Notification Matrix

| Event Type | Priority | Delivery Channel | Automated Action |
| :--- | :---: | :--- | :--- |
| **New External Pull Request** | High | GitHub Inbox & Email | Assigned for review via CODEOWNERS; welcome posted |
| **Compiler Adversarial Failure (CI)** | Critical | GitHub Inbox & Email | PR status check blocked; maintainer alerted |
| **Security Advisory Disclosure** | Urgent | Encrypted Email & Security Tab | Private advisory channel opened; no public disclosure |
| **Community Discussion Question** | Medium | GitHub Inbox | Community / maintainer response in Discussions |
| **Release Tag Tampering Attempt** | Blocked | Audit Log | Rejected automatically by "Protect Release Tags" ruleset |
| **Direct Push to `main` Attempt** | Blocked | Terminal error | Rejected automatically by "Protect main branch" ruleset |

---

*Last updated: 2026-11-16*
