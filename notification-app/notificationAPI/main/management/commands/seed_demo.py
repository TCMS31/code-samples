"""Seed the channels, categories and mock users the demo needs.

The original README said the repository shipped a pre-populated ``db.sqlite3``,
but that file is (correctly) git-ignored and was never committed, so a fresh
clone had an empty database and the Logs page was permanently blank. This
command creates the same data the README described, and is safe to re-run.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import Channel, MessageCategories, User

CHANNELS = ["SMS", "E-Mail", "Push Notification"]
CATEGORIES = ["Sports", "Finance", "Movies"]

# name -> channels the user receives
USERS = {
    "Test user 1": ["E-Mail", "Push Notification", "SMS"],
    "Test user 2": ["E-Mail"],
    "Test user 3": ["SMS"],
}


class Command(BaseCommand):
    help = "Create demo channels, message categories and subscribed mock users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--messages",
            type=int,
            default=0,
            help="Also create this many demo messages, fanning out notifications.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        channels = {
            name: Channel.objects.get_or_create(name=name)[0] for name in CHANNELS
        }
        categories = {
            name: MessageCategories.objects.get_or_create(name=name)[0]
            for name in CATEGORIES
        }

        for index, (name, channel_names) in enumerate(USERS.items(), start=1):
            user, _ = User.objects.get_or_create(
                name=name,
                defaults={
                    "email": f"user{index}@example.com",
                    "phone": f"+1555000000{index}",
                },
            )
            user.channels.set([channels[c] for c in channel_names])
            # Every demo user subscribes to every category.
            user.subscribe.set(categories.values())

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(channels)} channels, {len(categories)} categories, "
                f"{len(USERS)} users."
            )
        )

        count = options["messages"]
        if count:
            from main.models import Message

            category_list = list(categories.values())
            for i in range(count):
                Message.objects.create(
                    category=category_list[i % len(category_list)],
                    message=f"Demo message {i + 1}",
                )
            self.stdout.write(
                self.style.SUCCESS(f"Created {count} messages and their log entries.")
            )
