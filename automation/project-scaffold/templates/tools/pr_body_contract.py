"""Single source of the PR body shape that every PR tool validates.

The preflight, PR creation, the PR wrapper and the body helper all read these names, so
a body one tool drafts is accepted by the next. Workflow parity is handled separately.
"""

import re

SUMMARY = "## Summary"
CHANGES = "## Changes"
VALIDATION = "## Validation"
REVIEW_CHECKLIST = "## Review Checklist"
REQUIRED_SECTIONS = (SUMMARY, CHANGES, VALIDATION, REVIEW_CHECKLIST)

PROVIDER_ITEM = ("- [ ] **External provider**: no new named provider is introduced, or any new "
                 "provider was explicitly selected by the user before implementation "
                 "(required acknowledgement).")
PROVIDER_LINE_PATTERN = re.compile(r"^- \[[ xX]\] \*\*External provider\*\*:\s*\S")
PROVIDER_ACKNOWLEDGEMENT = re.compile(
    r"(?mi)^- \[x\] \*\*External provider\*\*:[ \t]*(\S[^\r\n]*)$")
PLACEHOLDER = re.compile(
    r"(?i)\b(?:todo|tbd|placeholder|describe the|assign the|add an appropriate|"
    r"choose the|not run: full pre-push)\b")
