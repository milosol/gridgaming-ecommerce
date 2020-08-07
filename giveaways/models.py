from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone

class Giveaway(models.Model):
    """Uses primary key and slug in URL"""
    title = models.CharField(max_length=settings.GIVEAWAY_TITLE_MAX_LENGTH)
    description = models.TextField(max_length=500, null=True, blank=True)
    giveaway_end_date = models.DateTimeField(null=True, blank=True)
    url = models.URLField(max_length=500, unique=True, blank=True, null=True)
    gleam_embed = models.TextField(null=True, blank=True)
    gleam_graph_tags = models.TextField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True)
    visible = models.BooleanField(default=True)
    sponsored = models.BooleanField(default=False)
    slug = models.SlugField(
        default="", editable=False, max_length=settings.GIVEAWAY_TITLE_MAX_LENGTH
    )

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        kwargs = {"pk": self.id, "slug": self.slug}
        return reverse("giveaways:giveaway-detail", kwargs=kwargs)

    @property
    def giveaway_ended(self):
        return timezone.now() > self.giveaway_end_date

    def save(self, *args, **kwargs):
        value = self.title
        self.slug = slugify(value, allow_unicode=True)
        super().save(*args, **kwargs)
