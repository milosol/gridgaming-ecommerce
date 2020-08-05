from django.contrib import admin
from .models import Giveaway

# Register your models here.


class GiveawayAdmin(admin.ModelAdmin):
    list_display = ['title','description','url','image', 'giveaway_end_date']

admin.site.register(Giveaway, GiveawayAdmin)

