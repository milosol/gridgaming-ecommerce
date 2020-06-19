from rest_framework import serializers

from retweet_picker.models import TwitterGiveaway, GiveawayResults


class TwitterGiveawaySerializer(serializers.ModelSerializer):
  #giveaway_id = serializers.StringRelatedField(many=True)
  original_url = serializers.StringRelatedField()

  class Meta:
    model = TwitterGiveaway
    fields = ['tweet_url',
              'winner_count',
              'members_to_follow',
              'contest_name',
              'giveaway_id',
              'original_url']

    read_only_fields = ['user']

  # def validate_url(self, url):
  #     qs =


class GiveawayResults(serializers.ModelSerializer):
  class Meta:
    model = GiveawayResults
    fields = '__all__'