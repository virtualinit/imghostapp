from django.contrib import admin
from imagehostingapp.models import UploadedImages, ImageThumbnailSize, AccountTiers, Subscription
# Register your models here.


@admin.register(UploadedImages)
class UploadedImagesAdmin(admin.ModelAdmin):
    search_fields = ('image_path', )
    exclude = ('image_name', )
    readonly_fields = ('image_uri', 'image_created_at',
                       'image_temp_uri', 'image_uri_expiry_sec')


@admin.register(ImageThumbnailSize)
class ImageThumbnailSize(admin.ModelAdmin):
    search_fields = ('thumbnail_size_px', )


@admin.register(AccountTiers)
class AccountTiers(admin.ModelAdmin):
    search_fields = ('account_tier_name', )


@admin.register(Subscription)
class Subscription(admin.ModelAdmin):
    search_fields = ('user', )
