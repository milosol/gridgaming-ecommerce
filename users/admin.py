from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, UserRoles



class AssignUserRole(admin.ModelAdmin):
    model = User
    search_fields = ['id', 'username','email']
    list_display = ['id', 'username', 'first_name','last_name', 'email', 'get_account_type', 'cleared_hot']
    list_filter = ('is_staff', 'is_superuser', 'cleared_hot', 'account_type__role_name')

    def get_account_type(self, obj):
        return obj.account_type

    get_account_type.short_description = 'Role Name'
    get_account_type.admin_order_field = 'account_type__role_name'

class UserRoleAdmin(admin.ModelAdmin):
    class Meta:
        verbose_name_plural = "User Roles"

    list_display = ['role_name', 'fee_quantifier', 'time_quantifier']


admin.site.register(UserRoles, UserRoleAdmin)
admin.site.register(User, AssignUserRole)

