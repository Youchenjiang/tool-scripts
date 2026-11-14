"""Single source of the PR body shape every PR tool validates.

The preflight, PR creation, the PR wrapper and the body helper read these names, so a
body one tool drafts is accepted by the next.
"""

import re

SUMMARY = "## Summary"
CHANGES = "## Changes"
VALIDATION = "## Validation"
REVIEW_CHECKLIST = "## Review Checklist"
REQUIRED_SECTIONS = (SUMMARY, CHANGES, VALIDATION, REVIEW_CHECKLIST)

# The template and the helper emit PROVIDER_ITEM; group 1 of PROVIDER_LINE is the
# checkbox state and group 2 the stated reason.
PROVIDER_ITEM = ("- [ ] **External provider**: no new named provider is introduced, or any new "
                 "provider was explicitly selected by the user before implementation "
                 "(required acknowledgement).")
PROVIDER_LINE = re.compile(r"(?mi)^- \[([ xX])\] \*\*External provider\*\*:[ \t]*(\S[^\r\n]*)$")
PLACEHOLDER = re.compile(r"(?i)\b(?:todo|tbd|placeholder|describe the|assign the|add an appropriate|"
                         r"choose the|not run: full pre-push)\b")
