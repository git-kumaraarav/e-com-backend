from django.core.management.base import BaseCommand

from store.instagram import fetch_instagram_posts


class Command(BaseCommand):
    help = "Fetch and cache the latest Instagram posts."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--limit", type=int, default=12)

    def handle(self, *args, **options) -> None:
        saved = fetch_instagram_posts(limit=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Synced {saved} Instagram posts."))
