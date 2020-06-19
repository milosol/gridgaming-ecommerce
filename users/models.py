from django.contrib.auth.models import AbstractUser
from django.db import models
# Create your models here.


class User(AbstractUser):
    account_type = models.ForeignKey("UserRoles",
                                     null=True,
                                     blank=True,
                                     on_delete=models.CASCADE)
    blacklisted = models.BooleanField(default=False)
    cleared_hot = models.BooleanField(default=False)  # Sets to true after member earns status


class UserRoles(models.Model):
    role_name = models.CharField(max_length=100, default="New User")
    role_description = models.CharField(max_length=500, null=True, blank=True)
    fee_quantifier = models.FloatField()  # Role to create quantifier based on user role
    time_quantifier = models.FloatField()

    def __str__(self):
        return self.role_name


class UserFeedback(models.Model):
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    feedback = models.TextField(verbose_name="User Feedback", max_length=1000)
    created_on = models.DateTimeField(auto_now_add=True)
