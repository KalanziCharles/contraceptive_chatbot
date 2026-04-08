import csv
import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contraceptive_chatbot.settings")

django.setup()

from chatbot.models import ContraceptiveMethod


def import_contraceptive_data():

    with open("contraceptives.csv", newline='', encoding='utf-8-sig') as file:

        reader = csv.DictReader(file, delimiter=',')

        print(reader.fieldnames)  # DEBUG

        for row in reader:

            ContraceptiveMethod.objects.get_or_create(
                name=row['name'],
                description=row['description'],
                effectiveness=row['effectiveness'],
                advantages=row['advantages'],
                disadvantages=row['disadvantages'],
                side_effects=row['side_effects'],
                suitability=row['suitability']
            )

    print("Dataset imported successfully!")



if __name__ == "__main__":
    import_contraceptive_data()
    