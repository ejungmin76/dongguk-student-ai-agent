import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("conversations", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ConversationStreamRun",
            fields=[
                ("run_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("running", "실행 중"), ("completed", "완료"), ("canceled", "취소"), ("failed", "실패")], default="running", max_length=16)),
                ("next_sequence", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("session", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="stream_runs", to="conversations.conversationsession")),
            ],
        ),
        migrations.CreateModel(
            name="ConversationStreamEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveIntegerField()),
                ("event_type", models.CharField(max_length=24)),
                ("payload", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("run", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="events", to="conversations.conversationstreamrun")),
            ],
            options={"ordering": ["sequence"]},
        ),
        migrations.AddIndex(model_name="conversationstreamrun", index=models.Index(fields=["session", "created_at"], name="conversatio_session_079069_idx")),
        migrations.AddConstraint(model_name="conversationstreamevent", constraint=models.UniqueConstraint(fields=("run", "sequence"), name="conversation_stream_event_sequence_unique")),
    ]
