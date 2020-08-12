from django.shortcuts import render

# Create your views here.
from django.urls import reverse_lazy
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView

from giveaways.models import Giveaway


class GiveawayDetailView(DetailView):
    model = Giveaway
    query_pk_and_slug = True
    template_name = "giveaways/giveaway_detail.html"


class GiveawayListView(ListView):
    model = Giveaway
    ordering = ['-giveaway_end_date']
    queryset = Giveaway.objects.filter(visible=True)
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class GiveawayCreateView(CreateView):
    model = Giveaway
    fields = ["title", "url", "image"]
    success_url = reverse_lazy("giveaways:giveaway-list")

    def form_valid(self, form):
        title = form.cleaned_data.get("title")
        url = form.cleaned_data.get("url")
        description = form.cleaned_data.get("description")
        image = form.cleaned_data.get("image")
        # create pk and slug model Giveaway
        Giveaway(title=title,
                 url=url,
                 description=description,
                 image=image).save()
        return super().form_valid(form)
