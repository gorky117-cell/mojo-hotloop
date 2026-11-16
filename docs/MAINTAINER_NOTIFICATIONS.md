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
- **How it works**: Whenever an external contributor opens a pull request against `main`, GitHub automatically assigns `@gorky117-cell` as the required reviewer.
- **Result**: The maintainer receives an immediate GitHub notification and email (depending on account preferences) without requiring manual PR assignment.

### B. CI Failure Notifications (`.github/workflows/ci.yml`)
- GitHub Actions automatically notifies the repository maintainer and commit author whenever a workflow run fails on `main` or an official pull request.
- Routine successful workflow runs do **not** trigger emails, keeping inbox noise minimal.

### C. Unprivileged Contributor Checks (`.github/workflows/contributor-assistant.yml`)
- Runs on unprivileged `pull_request: types: [opened, synchronize, reopened]` with strict read-only permissions (`contents: read`).
- Validates DCO sign-off across all commits via GitHub's REST API without checking out untrusted PR source code or executing untrusted scripts.
- Automatically reruns when contributors push new commits, providing instant pass/fail status without comment noise.

### D. Private Security Vulnerability Alerts
- With Private Vulnerability Reporting enabled, researchers can submit private disclosures via `https://github.com/gorky117-cell/mojo-hotloop/security/advisories/new`.
- GitHub routes confidential alerts directly to repository administrators without public issue disclosure.

---

## 2. Notification Configuration: Repository vs. Personal Settings

To guarantee that critical notifications reach you while routine noise is filtered out, configure both repository-level and personal account-level settings:

### A. Repository-Level Settings (`gorky117-cell/mojo-hotloop`)
*Controls which events in this specific repository generate notifications for your account.*

1. Navigate to: [https://github.com/gorky117-cell/mojo-hotloop](https://github.com/gorky117-cell/mojo-hotloop)
2. Click the **Watch** dropdown button at the top-right of the page.
3. Select **Custom**:
   - [x] **Issues** (notified when new bugs, crashes, or feature proposals are opened)
   - [x] **Pull requests** (notified when external PRs are submitted or updated)
   - [x] **Discussions** (notified when community members ask questions)
   - [x] **Security alerts** (notified of secret scanning or dependabot alerts)
4. Click **Apply**.

### B. Personal Account-Level Preferences (Your GitHub Account)
*Controls how and where GitHub delivers those notifications (web inbox, email address, push).*

1. Navigate to: [https://github.com/settings/notifications](https://github.com/settings/notifications)
2. **Default notification email**: Verify your preferred email address is selected.
3. **Watching**:
   - Check **Notify me**: `Email` and/or `Web`.
   - Check: `Automatically watch repositories` (ensures repositories you create are monitored).
4. **Actions (CI/CD)**:
   - Select: **Send notifications for failed workflows only**.
   - *Crucial*: This suppresses emails when CI runs succeed, alerting you only when compiler tests or DCO checks fail.
5. **Dependabot & Security Alerts**:
   - Under **Vulnerability alerts**: Ensure `Email` is enabled for immediate notice of private disclosures.
6. Click **Save** at the bottom of the page.

---

## 3. Event Notification Matrix

| Event Type | Priority | Delivery Channel | Automated Action |
| :--- | :---: | :--- | :--- |
| **New External Pull Request** | High | GitHub Inbox & Email | Assigned for review via CODEOWNERS; DCO check runs |
| **Compiler Adversarial Failure (CI)** | Critical | GitHub Inbox & Email | PR status check blocked; maintainer alerted to failing commit |
| **DCO Sign-off Missing** | Medium | Status Check (Red) | Commit author guided on remediation; PR blocked |
| **Security Advisory Disclosure** | Urgent | Encrypted Email & Security Tab | Private advisory channel opened; no public disclosure |
| **Community Discussion Question** | Medium | GitHub Inbox | Community / maintainer response in Discussions |
| **Release Tag Tampering Attempt** | Blocked | Audit Log | Rejected automatically by "Protect Release Tags" ruleset |
| **Direct Push to `main` Attempt** | Blocked | Terminal Error | Rejected automatically by "Protect main branch" ruleset |

---

*Last updated: 2026-11-16*
