# Database artifact ownership

Django migrations under `backend/src/lms/**/migrations/` are the only executable
application schema authority. Files in `database/generated/` and `database/security/`
are review evidence and are never deployed independently. Supabase or ad hoc SQL
migration histories are prohibited.
