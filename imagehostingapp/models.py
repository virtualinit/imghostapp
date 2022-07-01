import string
import random
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

# Create your models here.


class UploadedImages(models.Model):
    image_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    image_author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    image_name = models.CharField(max_length=255, verbose_name="Image Name", default='')
    image_desc = models.CharField(max_length=255, verbose_name="Image Description", default='')
    image_path = models.ImageField(upload_to="user_images", verbose_name="Image to be Uploaded",
                                   null=False, blank=False)
    image_uri = models.URLField(max_length=255, verbose_name="Image URI", default='')
    image_temp_uri = models.URLField(max_length=255, verbose_name="Image Temp URI", default='')
    image_uri_expiry_sec = models.IntegerField(
        default=-1, verbose_name="Image temp link expire after seconds"
    )
    image_created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        # preserve file_name for duplicate uploads
        self.image_name = self.image_path.name
        # help create download URLs
        self.image_uri = reverse('download_image',  kwargs={"image_id": self.image_id})
        # create temp uri
        image_temp_id = ''.join(random.choices(string.ascii_uppercase, k=8))
        self.image_temp_uri = reverse('download_temp_image', kwargs={"image_temp_id": image_temp_id}) \
            if self.image_uri_expiry_sec != -1 else ''
        return super(UploadedImages, self).save(*args, **kwargs)

    def __str__(self):
        return "{}".format(self.image_path)

    class Meta:
        verbose_name = "Uploaded Image"


class ImageThumbnailSize(models.Model):
    thumbnail_size_px = models.IntegerField(
        verbose_name="Image Thumbnail Size"
    )

    def __str__(self):
        return "{}px".format(self.thumbnail_size_px)

    class Meta:
        verbose_name = "Thumbnail Size"


class AccountTiers(models.Model):
    account_tier_name = models.CharField(
        max_length=255, verbose_name="Account Tier Name", default=''
    )
    thumbnail_sizes = models.ManyToManyField(
        ImageThumbnailSize, verbose_name="Thumbnail Sizes"
    )
    is_original_image_url_present = models.BooleanField(
        verbose_name="Originally uploaded image URL"
    )
    is_expiring_links_available = models.BooleanField(
        verbose_name="Generate expiring links (300 - 30000 sec)"
    )

    def __str__(self):
        return "{}".format(self.account_tier_name)

    class Meta:
        verbose_name = "Account Tier"


class Subscription(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tier = models.ForeignKey(AccountTiers, on_delete=models.CASCADE)

    def __str__(self):
        return "{} | {}".format(self.user.username, self.tier.account_tier_name)

    class Meta:
        verbose_name = "User Subscription"
