"""Tests for the notification fan-out sample."""

import gc

from django.test import TestCase
from django.urls import reverse

from main.models import Channel, Log, Message, MessageCategories, User
from main.notifications import (
    EmailNotificationDispatcher,
    NotificationDispatcher,
    SMSNotificationDispatcher,
)


class FixtureMixin:
    """Build the channel/category/user graph the dispatchers walk."""

    def build_world(self):
        self.sms = Channel.objects.create(name="SMS")
        self.email = Channel.objects.create(name="E-Mail")
        self.push = Channel.objects.create(name="Push Notification")

        self.sports = MessageCategories.objects.create(name="Sports")
        self.finance = MessageCategories.objects.create(name="Finance")

        # Receives everything, subscribed to both categories.
        self.everyone = User.objects.create(
            name="All channels", email="a@example.com", phone="1"
        )
        self.everyone.channels.set([self.sms, self.email, self.push])
        self.everyone.subscribe.set([self.sports, self.finance])

        # E-mail only, Sports only.
        self.email_only = User.objects.create(
            name="Email only", email="b@example.com", phone="2"
        )
        self.email_only.channels.set([self.email])
        self.email_only.subscribe.set([self.sports])

        # SMS only, Finance only.
        self.sms_finance = User.objects.create(
            name="SMS finance", email="c@example.com", phone="3"
        )
        self.sms_finance.channels.set([self.sms])
        self.sms_finance.subscribe.set([self.finance])


class DispatcherRegistryTests(TestCase):
    def test_every_builtin_dispatcher_is_discovered(self):
        names = {d.channel_name for d in NotificationDispatcher.dispatchers()}
        # A subset check: ``__subclasses__`` is a process-global registry cleared
        # only by garbage collection, so a dispatcher defined by another test may
        # still be listed here.
        self.assertTrue({"SMS", "E-Mail", "Push Notification"}.issubset(names))

    def test_a_new_subclass_is_picked_up_automatically(self):
        """The documented extension point: subclass and set channel_name."""

        class WebhookDispatcher(NotificationDispatcher):
            channel_name = "Webhook"

        try:
            self.assertIn(WebhookDispatcher, NotificationDispatcher.dispatchers())
            self.assertIn(
                "Webhook",
                {d.channel_name for d in NotificationDispatcher.dispatchers()},
            )
        finally:
            del WebhookDispatcher
            gc.collect()

    def test_nested_subclasses_are_found(self):
        class SecondarySms(SMSNotificationDispatcher):
            channel_name = "SMS Backup"

        try:
            self.assertIn(SecondarySms, NotificationDispatcher.dispatchers())
        finally:
            del SecondarySms
            gc.collect()

    def test_unconfigured_channel_returns_false_and_logs_nothing(self):
        category = MessageCategories.objects.create(name="Sports")
        message = Message(category=category, message="hi")
        message.save()  # plain save: no fan-out
        self.assertFalse(EmailNotificationDispatcher().send_notification(message))
        self.assertEqual(Log.objects.count(), 0)


class FanOutTests(FixtureMixin, TestCase):
    def setUp(self):
        self.build_world()

    def test_creating_a_message_logs_one_row_per_channel_and_subscriber(self):
        Message.objects.create(category=self.sports, message="Match tonight")

        # Sports subscribers: everyone (3 channels) + email_only (1 channel).
        self.assertEqual(Log.objects.count(), 4)
        self.assertEqual(Log.objects.filter(user=self.everyone).count(), 3)
        self.assertEqual(Log.objects.filter(user=self.email_only).count(), 1)
        self.assertEqual(Log.objects.filter(user=self.sms_finance).count(), 0)

    def test_category_subscription_is_respected(self):
        Message.objects.create(category=self.finance, message="Rates up")

        # Finance subscribers: everyone (3 channels) + sms_finance (1 channel).
        self.assertEqual(Log.objects.count(), 4)
        self.assertEqual(Log.objects.filter(user=self.sms_finance).count(), 1)
        self.assertEqual(Log.objects.filter(user=self.email_only).count(), 0)

    def test_channel_subscription_is_respected(self):
        Message.objects.create(category=self.sports, message="Match tonight")
        channels = set(
            Log.objects.filter(user=self.email_only).values_list(
                "channel__name", flat=True
            )
        )
        self.assertEqual(channels, {"E-Mail"})

    def test_a_message_without_a_category_sends_nothing(self):
        Message.objects.create(category=None, message="orphan")
        self.assertEqual(Log.objects.count(), 0)

    def test_saving_without_the_manager_does_not_fan_out(self):
        Message(category=self.sports, message="direct save").save()
        self.assertEqual(Log.objects.count(), 0)


class LogModelTests(FixtureMixin, TestCase):
    def setUp(self):
        self.build_world()

    def test_string_rendering_includes_channel_category_and_body(self):
        Message.objects.create(category=self.sports, message="Match tonight")
        rendered = Log.objects.filter(channel=self.email).first().get_log()
        self.assertIn("E-Mail", rendered)
        self.assertIn("Sports", rendered)
        self.assertIn("Match tonight", rendered)

    def test_string_rendering_survives_a_deleted_category(self):
        """Regression: message_type raised AttributeError on a null category."""
        Message.objects.create(category=self.sports, message="Match tonight")
        self.sports.delete()
        log = Log.objects.first()
        log.refresh_from_db()
        self.assertIsNone(log.message_type)
        self.assertIn("None", log.get_log())

    def test_string_rendering_survives_a_deleted_channel(self):
        Message.objects.create(category=self.sports, message="Match tonight")
        self.email.delete()
        log = Log.objects.filter(channel__isnull=True).first()
        self.assertIsNotNone(log)
        self.assertIsNone(log.channel_type)


class LogEndpointTests(FixtureMixin, TestCase):
    def setUp(self):
        self.build_world()
        Message.objects.create(category=self.sports, message="Match tonight")

    def test_log_list_returns_paginated_results(self):
        response = self.client.get(reverse("log-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 4)
        self.assertEqual(len(response.json()["results"]), 4)

    def test_log_string_list_returns_rendered_lines(self):
        response = self.client.get(reverse("log-list-string"))
        self.assertEqual(response.status_code, 200)
        first = response.json()["results"][0]
        self.assertIn("log", first)
        self.assertIn("Match tonight", first["log"])

    def test_log_listing_does_not_scale_queries_with_row_count(self):
        """select_related keeps both log endpoints off an N+1 path."""
        with self.assertNumQueries(2) as ctx:
            self.client.get(reverse("log-list-string"))
        baseline = len(ctx.captured_queries)

        # Ten more messages -> 40 more log rows, each touching four relations.
        for i in range(10):
            Message.objects.create(category=self.sports, message=f"extra {i}")
        self.assertEqual(Log.objects.count(), 44)

        with self.assertNumQueries(baseline):
            response = self.client.get(reverse("log-list-string"))
        self.assertEqual(response.json()["count"], 44)

    def test_logs_are_returned_newest_first(self):
        Message.objects.create(category=self.sports, message="Later message")
        results = self.client.get(reverse("log-list")).json()["results"]
        self.assertGreaterEqual(results[0]["created_on"], results[-1]["created_on"])


class CreateMessageEndpointTests(FixtureMixin, TestCase):
    def setUp(self):
        self.build_world()

    def test_posting_a_message_creates_it_and_fans_out(self):
        response = self.client.post(
            reverse("add-message"),
            data={"message": "Breaking news", "category": self.sports.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Message.objects.filter(message="Breaking news").exists())
        self.assertEqual(Log.objects.count(), 4)

    def test_posting_without_a_message_is_rejected(self):
        response = self.client.post(
            reverse("add-message"),
            data={"category": self.sports.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.json())

    def test_posting_an_unknown_category_is_rejected(self):
        response = self.client.post(
            reverse("add-message"),
            data={"message": "hi", "category": 99999},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class SeedCommandTests(TestCase):
    def test_seed_demo_is_idempotent(self):
        from django.core.management import call_command

        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)

        self.assertEqual(Channel.objects.count(), 3)
        self.assertEqual(MessageCategories.objects.count(), 3)
        self.assertEqual(User.objects.count(), 3)

    def test_seed_demo_can_create_messages(self):
        from django.core.management import call_command

        call_command("seed_demo", messages=3, verbosity=0)
        self.assertEqual(Message.objects.count(), 3)
        self.assertGreater(Log.objects.count(), 0)
