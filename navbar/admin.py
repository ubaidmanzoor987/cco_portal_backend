from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(NavBar)
admin.site.register(SubNavBar)
admin.site.register(OrganizationParentNavBar)
admin.site.register(OrganizationSubNavBar)