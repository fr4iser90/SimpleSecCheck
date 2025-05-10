# SecuLite Roles & Rules Index

| Role/Rule                | Purpose                                      | When Active         | Dependencies         |
|--------------------------|----------------------------------------------|---------------------|----------------------|
| master_of_repo.mdc       | Central authority, full autonomy             | Always              | core_critical_rules  |
| core_critical_rules.mdc  | AI-driven, user-minimal workflow             | Always              |                      |
| role_analysis_planning.mdc| Methodical planning before changes           | Before any change   | master_of_repo       |
| role_coding_phase.mdc    | Implementation, testing, refinement          | During coding       | analysis_planning    |
| role_task_manager.mdc    | Task sequencing and tracking                 | Always              |                      |
| role_documentation.mdc   | Documentation quality, cross-linking, onboarding | Always          | all roles            |

## Relationships Diagram

(master_of_repo) → (analysis_planning) → (task_manager) → (coding_phase)
                                 ↘
                              (documentation)

## Documentation Hub
- [../INDEX.md](../INDEX.md)

## How to Add/Modify Roles

- Add a new `.mdc` file in the `roles/` directory.
- Follow the standard header: Name, Activation, Core Principle, Workflow, Prohibitions, Tools, Interaction Points, Exit Conditions, Dependencies.
- Add a "See also" section linking to this index and related roles.
- Update this index with the new role and its relationships.

## Rule Documentation
- See [../rules/README.md](../../rules/README.md) for a summary of all Semgrep rules, their purpose, and links to feature documentation. 