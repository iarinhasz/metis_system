import django.db.models.deletion
from django.db import migrations, models

import projects.correction.attempts.status


class Migration(migrations.Migration):
    dependencies = [
        ("attempts", "0003_llmcall"),
        ("extractor", "0002_extractionstep"),
        ("questions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="run",
            name="config_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="run",
            name="profile",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="run",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("evaluation", "evaluation"),
                    ("rubric_check", "rubric_check"),
                    ("ab_test", "ab_test"),
                ],
                db_index=True,
                default=projects.correction.attempts.status.RunPurpose["EVALUATION"],
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="run",
            name="question",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="runs",
                to="questions.question",
            ),
        ),
        migrations.AddConstraint(
            model_name="run",
            constraint=models.CheckConstraint(
                condition=models.Q(("purpose__in", ["evaluation", "rubric_check", "ab_test"])),
                name="run_purpose_valid",
            ),
        ),
    ]
