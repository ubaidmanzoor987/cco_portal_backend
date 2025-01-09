from drf_yasg import openapi
from django.contrib import admin
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from django.urls import path, re_path, include
# from rest_framework_swagger.views import get_swagger_view
from django.conf.urls.static import static
from conf import settings
from conf.schemaProtocal import BothHttpAndHttpsSchemaGenerator
from conf.settings import BASE_URL, MEDIA_ROOT, MEDIA_URL, STATIC_ROOT, STATIC_URL

schema_view = get_schema_view(
    openapi.Info(
        title="Sria Membership Site",
        default_version="v1",
        description="Test description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    generator_class=BothHttpAndHttpsSchemaGenerator,
    permission_classes=(permissions.AllowAny,),
    url=BASE_URL,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("accounts.urls")),
    path("api/", include("file_hub.urls")),
    path("api/", include("organization.urls")),
    path("api/", include("navbar.urls")),
    path("api/", include("task.urls")),
    path("api/", include("acr_tool.urls")),
    path("api/", include("fiduciary.urls")),
    path(
        "api/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"
    ),
]

if settings.DEBUG:
    urlpatterns += static(STATIC_URL, document_root=STATIC_ROOT) + static(
        MEDIA_URL, document_root=MEDIA_ROOT
    )
