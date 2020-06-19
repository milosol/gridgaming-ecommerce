# Create your views here.
from django.db.models import Q
from rest_framework import generics, mixins

from retweet_picker.models import GiveawayResults, TwitterGiveaway
from .permissions import IsOwnerOrReadOnly
from .serializers import TwitterGiveawaySerializer


class GiveawayAPIView(generics.ListAPIView, mixins.CreateModelMixin):
    # pk aka id --> numbers
    lookup_field        = 'pk'  #slug, id url(r'?P<pk>\d+')
    serializer_class    = TwitterGiveawaySerializer
    permission_classes = [IsOwnerOrReadOnly]
    #queryset            = GiveawayResults.objects.all()

    def get_queryset(self):
        qs = TwitterGiveaway.objects.all()
        query = self.request.GET.get("q")
        if query is not None:
            qs = qs.filter(Q(tweet_url__tweet_url__icontains=query))
        return qs
        #return TwitterGiveaway.objects.all()

    def perform_create(self, serializer):
      serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class GiveawayRudView(generics.RetrieveUpdateDestroyAPIView):
    # pk aka id --> numbers
    lookup_field        = 'pk'  #slug, id url(r'?P<pk>\d+')
    serializer_class    = TwitterGiveawaySerializer
    #queryset            = GiveawayResults.objects.all()


    def get_queryset(self):
        return TwitterGiveaway.objects.all()

    def perform_create(self, serializer):
      serializer.save(user=self.request.user)

class RetweetWinnerRudView(generics.RetrieveUpdateDestroyAPIView):
    # pk aka id --> numbers
    lookup_field        = 'pk'  #slug, id url(r'?P<pk>\d+')
    serializer_class    = GiveawayResults
    #queryset            = GiveawayResults.objects.all()



    def get_queryset(self):
        return GiveawayResults.objects.all()
