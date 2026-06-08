# Hand-written migration to replace the old DissLine structure
# with the new archetype-linked pre-written burn lines,
# and to update Diss with custom_note, selected_lines, parent_diss, is_riposte.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dissers', '0002_roastcategory_targetarchetype_avatar_and_more'),
        ('disses', '0002_dissline_category'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ── 1. Tear down the old DissLine completely ──────────────────────
        migrations.DeleteModel(
            name='DissLine',
        ),

        # ── 2. Rebuild DissLine in its new form ───────────────────────────
        migrations.CreateModel(
            name='DissLine',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True,
                    serialize=False, verbose_name='ID')),
                ('line_type', models.CharField(
                    choices=[
                        ('trait', 'Trait'),
                        ('weakness', 'Weakness'),
                        ('catchphrase', 'Catchphrase'),
                    ],
                    default='trait',
                    max_length=20,
                )),
                ('content', models.TextField(
                    help_text='The actual burn line')),
                ('status', models.CharField(
                    choices=[
                        ('approved', 'Approved'),
                        ('pending', 'Pending Approval'),
                        ('rejected', 'Rejected'),
                    ],
                    default='approved',
                    max_length=20,
                )),
                ('display_order', models.PositiveIntegerField(default=0)),
                ('archetype', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='diss_lines',
                    to='dissers.targetarchetype',
                )),
                ('roast_style', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='diss_lines',
                    to='dissers.roaststyle',
                )),
                ('suggested_by', models.ForeignKey(
                    blank=True,
                    help_text='Null if written by admin',
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='suggested_lines',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Diss Line',
                'verbose_name_plural': 'Diss Lines',
                'ordering': ['line_type', 'display_order'],
            },
        ),

        # ── 3. Update Diss — remove old fields, add new ones ─────────────

        # Remove fields that existed in the old Diss model
        migrations.RemoveField(model_name='diss', name='title'),
        migrations.RemoveField(model_name='diss', name='context_notes'),

        # Fix the status choices (old had 'commissioned'/'delivered')
        migrations.AlterField(
            model_name='diss',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('published', 'Published'),
                ],
                default='draft',
                max_length=20,
            ),
        ),

        # Add the new fields to Diss
        migrations.AddField(
            model_name='diss',
            name='custom_note',
            field=models.TextField(
                blank=True,
                help_text='Optional personal context',
            ),
        ),
        migrations.AddField(
            model_name='diss',
            name='parent_diss',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ripostes',
                to='disses.diss',
            ),
        ),
        migrations.AddField(
            model_name='diss',
            name='is_riposte',
            field=models.BooleanField(default=False),
        ),

        # Add the M2M through selected_lines
        migrations.AddField(
            model_name='diss',
            name='selected_lines',
            field=models.ManyToManyField(
                blank=True,
                help_text='The lines the user picked',
                related_name='used_in_disses',
                to='disses.dissline',
            ),
        ),

        # Fix roast_style and target_archetype related_names
        # (old migration didn't set related_name='disses')
        migrations.AlterField(
            model_name='diss',
            name='roast_style',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='disses',
                to='dissers.roaststyle',
            ),
        ),
        migrations.AlterField(
            model_name='diss',
            name='target_archetype',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='disses',
                to='dissers.targetarchetype',
            ),
        ),
    ]
