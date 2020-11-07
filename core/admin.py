from django.contrib import admin
from django.db.models import Prefetch

from .models import (
    Item,
    OrderItem,
    Order,
    Payment,
    Coupon,
    Refund,
    Address,
    UserProfile,
    Slotitem,
    Checktime,
    History,
    Counting,
    Cartget,
)


def make_refund_accepted(modeladmin, request, queryset):
    queryset.update(refund_requested=False, refund_granted=True)


make_refund_accepted.short_description = 'Update orders to refund granted'


class PaymentAdmin(admin.ModelAdmin):
    raw_id_fields = ("user",)
    list_display = ['user',
                    'stripe_charge_id',
                    'braintree_charge_id',
                    'amount',
                    'timestamp',
                    ]


class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ("user", 'items')

    list_display = ['id',
                    'user',
                    'get_cleared_hot',
                    'ordered',
                    'ordered_date',
                    'status',
                    'get_purchased_items',
                    'billing_address',
                    'payment',
                    'coupon'
                    ]
    list_display_links = [
        'user',
        'billing_address',
        'payment',
        'coupon'
    ]
    list_filter = ['ordered',
                   'being_delivered',
                   'status',
                   'ordered_date',
                   'refund_requested',
                   'kind',
                   'refund_granted']
    search_fields = [
        'id',
        'user__username',
        'ref_code'
    ]
    actions = [make_refund_accepted]

    # def get_queryset(self, request):
    #     user_search = super(OrderAdmin, self).get_queryset(request)
    #     user_search = user_search.prefetch_related('user')
    #     return user_search

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if kwargs:
            print(f'foreign: {kwargs}')
        # if db_field.name in ['billing_address','shipping_address']:
        #     kwargs['queryset'] = Address.objects.filter(user=request.user)
        # if db_field.name == 'payment':
        #     kwargs['queryset'] = Payment.objects.filter(user=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == 'items':
            if kwargs:
                print(kwargs)
            #kwargs['queryset'] = OrderItem.objects.filter(user=request.user)
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_cleared_hot(self, obj):
        return obj.user.cleared_hot

    def get_queryset(self, request):
        prefetched_orders = super(OrderAdmin, self).get_queryset(request)
        prefetched_orders.prefetch_related(
            Prefetch('items', queryset=OrderItem.objects.select_related('item',
                                                                        'slot',
                                                                        'user')))\
            .select_related('user', 'shipping_address','billing_address','payment','coupon')

        # prefetched_orders = prefetched_orders.select_related('user', 'shipping_address',
        #                                                      'billing_address','payment','coupon')
        return prefetched_orders

    get_cleared_hot.boolean = True
    get_cleared_hot.short_description = 'Cleared Hot'
    get_cleared_hot.admin_order_field = 'user__cleared_hot'


class OrderItemAdmin(admin.ModelAdmin):
    raw_id_fields = ("user", "item")
    list_display = ['user',
                    'get_title',
                    'quantity',
                    'kind',
                    'ordered',
                    'username',
                    'launch_code',
                    'order_id',
                    'ordered_date'
                    ]

    list_filter = ['ordered', 'kind']
    search_fields = ('username',)

    def get_email(self, obj):
        return obj.user.email

    def order_id(self, obj):
        if obj.orders.all():
            return obj.orders.all()[0].id
        else:
            return 0

    def ordered_date(self, obj):
        if obj.orders.all():
            return obj.orders.all()[0].ordered_date
        else:
            return 0

    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #     if db_field.name == 'payment':
    #         kwargs['queryset'] = Payment.objects.filter(user=request.user)
    #
    #     return super().formfield_for_foreignkey(db_field, request, **kwargs)


    def get_queryset(self, request):
        prefetched_orders = super(OrderItemAdmin, self).get_queryset(request)
        prefetched_orders = prefetched_orders.select_related('item','slot')
        return prefetched_orders


class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'street_address',
        'apartment_address',
        'country',
        'zip',
        'address_type',
        'default'
    ]
    list_filter = ['default', 'address_type', 'country']
    search_fields = ['user', 'street_address', 'apartment_address', 'zip']


class HistoryAdmin(admin.ModelAdmin):
    list_display = [
        'start_date',
        'user',
        'user_id',
        'action',
        'reason',
        'order_str',
        'item_str',
    ]
    list_display_links = [
        'user',
    ]
    list_filter = ['user']
    search_fields = ['order_str']

    def user_id(self, obj):
        if obj.user:
            return obj.user.id
        else:
            return 0


class CountingAdmin(admin.ModelAdmin):
    list_display = [
        'user_id',
        'deadline',
        'pause',
        'order_id',
    ]
    list_filter = ['user_id']
    search_fields = ['user_id']


class ChecktimeAdmin(admin.ModelAdmin):
    list_display = [
        'time',
        'launched',
        'action_time',
        'launch_time',
        'cartcounter_run',
        'thread_id',
        'launch_code',
    ]


class SlotitemAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'available',
        'available_count',
        'placeholder',
        'total',
        'points',
        'value',
        'description',
    ]


class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'payment_method',
        'stripe_charge_id',
        'amount',
        'timestamp'
    ]

class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
    ]
    search_fields = ['user']



admin.site.register(Item)
admin.site.register(OrderItem, OrderItemAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(History, HistoryAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Coupon)
admin.site.register(Refund)
admin.site.register(Address, AddressAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Slotitem, SlotitemAdmin)
admin.site.register(Checktime, ChecktimeAdmin)
admin.site.register(Counting, CountingAdmin)
admin.site.register(Cartget)
