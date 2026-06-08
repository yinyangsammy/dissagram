# Hand-written migration — adds is_free flag to TargetArchetype and RoastStyle
# This powers the freemium "temptation" mechanic:
#   - one archetype is_free=True → shown fully to all users
#   - one roast style is_free=True → available to free tier
#   - everything else is greyed out / locked in the UI

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dissers', '0003_alter_targetarchetype_catchphrase_disser'),
    ]

    operations = [
        migrations.AddField(
            model_name='targetarchetype',
            name='is_free',
            field=models.BooleanField(
                default=False,
                help_text='If True, this archetype is available to free-tier users.'
            ),
        ),
        migrations.AddField(
            model_name='roaststyle',
            name='is_free',
            field=models.BooleanField(
                default=False,
                help_text='If True, this roast style is available to free-tier users.'
            ),
        ),
    ]
