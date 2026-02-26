# Frontend Error Log

All frontend errors, bugs, and issues are documented here. Each entry must be marked as **open** or **fixed** once resolved.

---

## Error Log

| Date | Version | Error | Cause | Fix | Status |
|------|---------|-------|-------|-----|--------|
| 2026-02-26 | v0.5.1 | Login returns 500 Internal Server Error | `last_login` column is `TIMESTAMP WITHOUT TIME ZONE` but `datetime.now(timezone.utc)` produces timezone-aware datetime; asyncpg rejects the mismatch | Changed `routers/auth.py` line 49: `.replace(tzinfo=None)` strips timezone before DB update | fixed |
| 2026-02-26 | v0.5.1 | Login returns 500 — permission denied for table users | `woms_user` DB user was freshly created but tables in `woms_db` were owned by `postgres`; no table-level GRANT existed | Ran `GRANT ALL PRIVILEGES ON ALL TABLES/SEQUENCES IN SCHEMA public TO woms_user` + `ALTER DEFAULT PRIVILEGES` for future tables | fixed |

---

## Template for New Entries

```
| YYYY-MM-DD | vX.Y.Z | Brief error description | Root cause analysis | What was done to fix it | open / fixed |
```
