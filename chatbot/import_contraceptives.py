import csv
from django.core.management.base import BaseCommand
from chatbot.models import HealthFacility


class Command(BaseCommand):
    help = "Import health facilities from CSV"

    def handle(self, *args, **kwargs):

        with open("health_facilities.csv", newline='', encoding='utf-8-sig') as file:

            reader = csv.DictReader(file)

            for row in reader:

                HealthFacility.objects.get_or_create(
                    name=row['name'],
                    location=row['location'],
                    latitude=float(row['latitude']),
                    longitude=float(row['longitude']),
                    facility_type=row['facility_type'],
                    offers_free_services=row['offers_free_services'] == "True",
                    services=row['services']
                )

        self.stdout.write(self.style.SUCCESS("Facilities imported successfully!"))