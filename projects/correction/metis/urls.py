"""Root URL configuration."""

from django.contrib import admin
from django.urls import path

from projects.correction.metis.api import api

urlpatterns = [path("admin/", admin.site.urls), path("", api.urls)]
