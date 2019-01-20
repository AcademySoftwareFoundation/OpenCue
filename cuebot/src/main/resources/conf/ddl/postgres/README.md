# Cuebot PostgreSQL Schema

The database schema is provided in the form of "migrations", SQL files which
can be incrementally applied to construct the entire current schema. Your
schema can be rolled forward and back using the management tool of your choice.

For example migrations can be applied using [Flyway](https://flywaydb.org/):

```
createdb cuebot_local_test
flyway -url=jdbc:postgresql://localhost/cuebot_local_test -user=$USER -locations=filesystem:cuebot/src/main/resources/conf/ddl/postgres/migrations migrate
```

Once migrations have been applied you can use `pg_dump` to update the full schema from the
created database.

```
pg_dump --no-privileges --no-owner -s cuebot_local_test > cuebot/src/main/resources/conf/ddl/postgres/schema.sql
```

