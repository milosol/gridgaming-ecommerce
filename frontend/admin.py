from django.contrib import admin
from .models import BuyCredit, OneValue
from users.models import User
# Register your models here.


class BuyCreditAdmin(admin.ModelAdmin):
    list_display = ['user',
                    'user_id',
                    'credit_amount',
                    'usd_amount',
                    'payment_status',
                    'added_credit',
                    'created_at',
                    ]
    search_fields = ['added_credit']
    list_display_links = [
        'user'
    ]
    
    def user_id(self, obj):
        if obj.user:
            return obj.user.id
        else:
            ''
    
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(BuyCreditAdmin, self).get_search_results(request, queryset, search_term)
        
        # users = User.objects.filter(username__contains=search_term)
        # if users.exists():
        #     ids = map(lambda x: x.id, users) 
        #     queryset |= self.model.objects.filter(user__id__in=ids)
        queryset |= self.model.objects.filter(user__username__contains=search_term)
        if search_term.isnumeric():
            queryset |= self.model.objects.filter(user__id=int(search_term))
        return queryset, use_distinct
           
class OneValueAdmin(admin.ModelAdmin):
    list_display = ['cc_per_usd', 
                    'min_buy_credit',
                    'judge_credit_price'
                    ]


admin.site.register(BuyCredit, BuyCreditAdmin)
admin.site.register(OneValue, OneValueAdmin)