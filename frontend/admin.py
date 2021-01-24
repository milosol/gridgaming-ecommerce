from django.contrib import admin
from .models import BuyCredit, OneValue
# Register your models here.


class BuyCreditAdmin(admin.ModelAdmin):
    list_display = ['user',
                    'user_id',
                    'credit_amount',
                    'usd_amount',
                    'payment_status',
                    'payment',
                    'created_at',
                    ]
    search_fields = ('user_id',)
    list_display_links = [
        'payment', 'user'
    ]
    
    def user_id(self, obj):
        if obj.user:
            return obj.user.id
        else:
            ''
            
class OneValueAdmin(admin.ModelAdmin):
    list_display = ['cc_per_usd']


admin.site.register(BuyCredit, BuyCreditAdmin)
admin.site.register(OneValue, OneValueAdmin)