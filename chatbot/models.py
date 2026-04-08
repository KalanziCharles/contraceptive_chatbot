from django.db import models

# Create your models here.

class ContraceptiveMethod(models.Model):

    name = models.CharField(max_length=200)
    description = models.TextField()
    effectiveness = models.CharField(max_length=100)
    advantages = models.TextField()
    disadvantages = models.TextField()
    side_effects = models.TextField()
    suitability = models.TextField()

    def __str__(self):
        return self.name

class HealthFacility(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)

    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)

    FACILITY_TYPE = [
        ('hospital', 'Hospital'),
        ('health_center', 'Health Center'),
        ('private', 'Private Clinic'),
    ]
    facility_type = models.CharField(
        max_length=20,
        choices=FACILITY_TYPE,
        default='health_center'   # 👈 IMPORTANT
    )

    offers_free_services = models.BooleanField(default=False)
    services = models.TextField()


class ChatHistory(models.Model):

    user_message = models.TextField()

    bot_response = models.TextField()

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_message   