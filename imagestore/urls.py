"""imagestore URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

from rest_framework.routers import DefaultRouter

from imagehostingapp.views import (
    PingImageHostingApp, ListUploadImages, DownloadImage,
    DownloadImageThumbnail, DownloadTempImage
)


router = DefaultRouter()
router.register('image', ListUploadImages, basename='list_upload_image')


api_urls = [
    path('ping', PingImageHostingApp.as_view(), name='api_ping_server'),
    path('image/<uuid:image_id>/size/<int:thumbnail_size_px>/',
         DownloadImageThumbnail.as_view(), name='download_image_thumbnail'),
    path('image/<uuid:image_id>/', DownloadImage.as_view(), name='download_image'),
    path('image/<str:image_temp_id>/', DownloadTempImage.as_view(), name='download_temp_image'),
    path('', include(router.urls)),
]


urlpatterns = [
    path('', RedirectView.as_view(permanent=False, url='/api'), name="index"),
    path('admin/', admin.site.urls),
    path('api/', include(api_urls)),
    path('api-auth/', include('rest_framework.urls')),
]

urlpatterns += staticfiles_urlpatterns()
