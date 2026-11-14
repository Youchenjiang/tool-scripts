<!--
PR descriptions are separate from commit bodies. Keep the description in English and
concise. The default structure is Summary + Changes + Validation, with Scope only when
a boundary or exclusion matters to review.

GitHub assignees, labels and milestones are checked from actual PR metadata, not from
self-reported checkboxes. The External provider acknowledgement stays required, because
tooling cannot infer that the user authorized a new named provider.

Title rule: use a plain descriptive title (type(scope): what changed), never internal
roadmap codes; those belong in the milestone only.
-->

## Summary
<!-- 1-2 sentences on what changed and why. Do not list file names here. -->

## Changes
<!-- Short reviewer-relevant bullets describing behavior and contracts, not a commit ledger. -->
- Describe the change.

## Validation
<!-- Summarize the build, test, or manual verification performed. -->
- Describe the build, test, or manual verification performed.

## Scope
<!-- Optional: include only when exclusions or ownership boundaries matter to review. -->

## Review Checklist
<!-- Check only what you actually reviewed. Reviewer prompts never replace evidence. -->
- [ ] **Behavior**: reviewed intentional behavior changes and unintended side effects.
- [ ] **Regression**: assessed affected paths and recorded the relevant evidence in Validation.
- [ ] **Compatibility**: reviewed compatibility and migration impact, if applicable.
- [ ] **Security**: assessed security implications, if applicable.
- [ ] **Documentation**: updated relevant docs or confirmed no change is required.
- [ ] **External provider**: no new named provider is introduced, or any new provider was explicitly selected by the user before implementation (required acknowledgement).
