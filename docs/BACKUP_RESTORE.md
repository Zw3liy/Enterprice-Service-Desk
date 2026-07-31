# Backup and Restore

## SQLite development
```bash
./deployment/scripts/backup.sh
# creates backups/db_TIMESTAMP.sqlite3 and media_TIMESTAMP.tar.gz
```

Restore:
```bash
cp backups/db_YYYYMMDD_HHMMSS.sqlite3 db.sqlite3
tar -xzf backups/media_YYYYMMDD_HHMMSS.tar.gz
```

## PostgreSQL production
```bash
pg_dump -Fc -h $DATABASE_HOST -U $DATABASE_USER $DATABASE_NAME > esd_$(date +%F).dump
# media
tar -czf media_$(date +%F).tar.gz media/
```

Restore:
```bash
pg_restore -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME --clean esd_YYYY-MM-DD.dump
tar -xzf media_YYYY-MM-DD.tar.gz
python manage.py migrate
```

## Disaster recovery
1. Restore database from latest verified backup.
2. Restore media volume.
3. Deploy application image/commit matching backup era.
4. Verify `/healthz/`, `/ready/`, admin login, ticket list.
5. Re-run `scan_sla` and `run_due_reports` after recovery.
6. Rotate secrets if breach-related.
