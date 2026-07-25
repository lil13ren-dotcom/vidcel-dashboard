# knowledge/

Tracks the PM OS project (店舗IT担当 PM管理体制の構築) that lives on the
`claude/pm-os-spreadsheet-n5a4ga` branch of this repo. This repo itself
(`vidcel-dashboard`) is unrelated to the 店舗IT担当 service — this folder
exists here only because it is the branch the PM OS work is tracked on.

- `Decision_Log.md` — append-only log of decisions made while building/
  maintaining the PM OS.
- `Architecture.md` — where things actually live: which repo/spreadsheet
  contains which part of the 店舗IT担当 business, as verified by direct
  inspection (not assumption).
- `Backlog.md` — open questions and follow-up work surfaced during PM OS
  tasks, not yet assigned a Task ID.
- `ADD_*.md` — standalone Architecture Decision Documents for individual
  design questions (e.g. `ADD_G1-06D_Onboarding_Data_Bridge.md`), referenced
  from `Architecture.md` and `Decision_Log.md` rather than inlined there.
- `SPEC_*.md` — standalone specifications (e.g.
  `SPEC_G1-09_Onboarding_Data_Model.md` — field-level data model), same
  referencing convention as `ADD_*.md`.
