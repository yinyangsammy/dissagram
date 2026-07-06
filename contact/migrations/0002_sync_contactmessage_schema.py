from django.db import migrations, models
from django.utils import timezone


def get_column_names(schema_editor, table_name):
    with schema_editor.connection.cursor() as cursor:
        return {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }


def sync_contactmessage_schema(apps, schema_editor):
    ContactMessage = apps.get_model("contact", "ContactMessage")
    table_name = ContactMessage._meta.db_table
    existing_columns = get_column_names(schema_editor, table_name)
    quoted_table = schema_editor.quote_name(table_name)

    # Heroku currently has old created_at.
    # Current model/admin expect created_on.
    # Rename preserves old contact timestamps.
    if "created_at" in existing_columns and "created_on" not in existing_columns:
        schema_editor.execute(
            f"ALTER TABLE {quoted_table} "
            f"RENAME COLUMN {schema_editor.quote_name('created_at')} "
            f"TO {schema_editor.quote_name('created_on')}"
        )
        existing_columns.remove("created_at")
        existing_columns.add("created_on")

    # Add reason if missing.
    # Existing old messages get "general".
    if "reason" not in existing_columns:
        reason_field = ContactMessage._meta.get_field("reason")
        schema_editor.add_field(ContactMessage, reason_field)
        existing_columns.add("reason")

    # Add is_resolved if missing.
    # Existing old messages get False.
    if "is_resolved" not in existing_columns:
        resolved_field = ContactMessage._meta.get_field("is_resolved")
        schema_editor.add_field(ContactMessage, resolved_field)
        existing_columns.add("is_resolved")

    # Safety fallback only.
    # Heroku should hit the rename above, but this protects any DB
    # that has neither created_at nor created_on.
    if "created_on" not in existing_columns:
        created_field = models.DateTimeField(default=timezone.now)
        created_field.set_attributes_from_name("created_on")
        schema_editor.add_field(ContactMessage, created_field)
        existing_columns.add("created_on")

    # Add nullable user FK if missing.
    if "user_id" not in existing_columns:
        user_field = ContactMessage._meta.get_field("user")
        schema_editor.add_field(ContactMessage, user_field)
        existing_columns.add("user_id")


class Migration(migrations.Migration):

    dependencies = [
        ("contact", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    sync_contactmessage_schema,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[],
        ),
    ]