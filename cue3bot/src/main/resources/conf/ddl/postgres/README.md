# Cuebot PostgreSQL Schema

Schema files are provided in two formats.

1. Migration files, in `migrations/`. These can be applied incrementally to construct the entire 
   current schema. Your schema can be rolled forward and back using the management tool of your
   choice.
1. Full schema, in `schema.sql`. This contains the same schema as the migrations, but flattened
   into a single file for convenience. This can be applied in a single operation using `pg_restore`
   or similar.

For example migrations can be applied using [Flyway](https://flywaydb.org/):

```
createdb cuebot_local_test
flyway -url=jdbc:postgresql://localhost/cuebot_local_test -user=$USER -locations=filesystem:cue3bot/src/main/resources/conf/ddl/postgres/migrations migrate
``` 

Once migrations have been applied you can use `pg_dump` to update the full schema from the
created database.

```
pg_dump --no-privileges --no-owner -s cuebot_local_test > cue3bot/src/main/resources/conf/ddl/postgres/schema.sql
```
