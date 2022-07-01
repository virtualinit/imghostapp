from django.shortcuts import render

# Create your views here.
import io
import os
import math
import mimetypes
import logging
from datetime import timedelta
from enum import Enum
from PIL import Image

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.encoding import smart_str
from django.utils import timezone
from django.views.decorators.cache import cache_page
from wsgiref.util import FileWrapper

from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets

from imagestore import APP_NAME, APP_VERSION
from imagehostingapp.serializers import ImageUploadSerializer, ListImagesSerializer
from imagehostingapp.models import UploadedImages, AccountTiers, Subscription


class ServiceStatues(Enum):
    STARTING_UP = 1
    RUNNING = 2
    RE_BOOTING = 3
    SHUT_DOWN = 4
    SUSPENDED = 5


class PingImageHostingApp(APIView):
    """
    API to check if service is up and running.
    curl -X GET http://127.0.0.1:8080/api/ping
    """
    def get(self, request) -> Response:
        """
        Ping ImageHosting App.
        """
        logging.log(
            level=logging.DEBUG,
            msg=f"Client with IP {request.client_ip} accessing the PING API."
        )
        response_message = {}
        response_message.update(dict(service=f"{APP_NAME} {APP_VERSION}"))
        response_message.update(dict(status=ServiceStatues.RUNNING.name))
        return Response(response_message, status=status.HTTP_200_OK)


class ListUploadImages(viewsets.ModelViewSet):
    """
    API to list and upload images
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = ListImagesSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return UploadedImages.objects.filter(image_author=self.request.user)

    def list(self, request, *args, **kwargs):
        """
        API to list all uploaded images.
        curl -L -X GET -S -u "username:password" \
             http://127.0.0.1:8080/api/image/
        """
        logging.log(
            level=logging.DEBUG,
            msg=f"Client with IP {request.client_ip} accessing the List Image API."
        )
        queryset = UploadedImages.objects.filter(image_author=self.request.user)
        serializer = ListImagesSerializer(queryset, many=True)
        return Response(serializer.data)

    def _populate_image_urls_as_per_user_subscription(self, upload_response):
        # hide internal image_path in user response
        del upload_response['image_path']
        # and pop image_uuid and image_uri
        _ = upload_response.pop('image_id')
        download_uri = upload_response.pop('image_uri')
        image_temp_uri = upload_response.pop('image_temp_uri')

        user_subscription_query_set = Subscription.objects.filter(user=self.request.user)

        # Uncomment following if we want to restrict images upload feature
        # for users NOT subscribed to any of the plans.
        # if not user_subscription_query_set:
        #     return {"error": "User is not subscribed to any plan."}, status.HTTP_400_BAD_REQUEST

        user_subscription = user_subscription_query_set.first()

        if user_subscription:
            # Add thumbnail URLs
            if user_subscription.tier.thumbnail_sizes:
                thumbnails = user_subscription.tier.thumbnail_sizes.all()
                for thumbnail in thumbnails:
                    thumbnail_url_user_response_key = \
                        "image_url_thumbnail_{}".format(thumbnail.thumbnail_size_px)
                    thumbnail_url = "{}size/{}/".format(
                        self.request.build_absolute_uri(download_uri),
                        thumbnail.thumbnail_size_px
                    )
                    upload_response[thumbnail_url_user_response_key] = thumbnail_url
            # Add original image URL
            if user_subscription.tier.is_original_image_url_present:
                upload_response['image_url'] = self.request.build_absolute_uri(download_uri)
            if user_subscription.tier.is_expiring_links_available and image_temp_uri:
                upload_response['image_temp_url'] = self.request.build_absolute_uri(image_temp_uri)
        return upload_response, status.HTTP_201_CREATED

    def create(self, request, *args, **kwargs):
        """
        API to Upload Images
        curl -L -X POST -S -u "username:password" \
            -F image_desc="some random image" \
            -F image_path='@"/path/to/image/someImage.png"' \
            -F image_uri_expiry_sec=400 \
            http://127.0.0.1:8080/api/image/

        image_uri_expiry_sec: int:optional
        """
        logging.log(
            level=logging.DEBUG,
            msg=f"Client with IP {request.client_ip} accessing the Upload Image API."
        )
        serializer = ImageUploadSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            response_json = serializer.data.copy()
            response_json, status_code = \
                self._populate_image_urls_as_per_user_subscription(response_json)
            logging.log(
                level=logging.INFO,
                msg=f"Upload Image succeed for client with IP {request.client_ip}."
            )
            return Response(response_json, status_code)
        logging.log(
            level=logging.ERROR,
            msg=f"Upload Image failed for client with IP {request.client_ip}. errors: {serializer.errors}"
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DownloadImage(APIView):
    """
    Download the original image
    curl -X GET -u "username:password" \
        --remote-name --remote-header-name \
        http://localhost:8080/api/image/<image-uuid>/
    """
    permission_classes = (IsAuthenticated,)

    def retrieve_original_image(self, image_query_obj):
        file_name = image_query_obj.image_path.name
        file_path = settings.MEDIA_ROOT + '/' + file_name
        with open(file_path, 'rb') as file:
            file_wrapper = FileWrapper(file)
            file_mimetype = mimetypes.guess_type(file_path)[0]
            response = HttpResponse(file_wrapper, content_type=file_mimetype,
                                    status=status.HTTP_200_OK)
            original_image_name = image_query_obj.image_name
            response['X-Sendfile'] = original_image_name
            response['Content-Length'] = os.stat(file_path).st_size
            response['Content-Disposition'] = \
                'attachment; filename={}'.format(smart_str(original_image_name))
            return response

    def check_user_subscription(self):
        # Verify subscription status of auth user for retrieving original images
        user_subscription_query_set = Subscription.objects.filter(user=self.request.user)
        if not user_subscription_query_set:
            return Response({"error": "User is not subscribed to any plan."},
                            status=status.HTTP_400_BAD_REQUEST)

        user_subscription = user_subscription_query_set.first()
        if not user_subscription.tier.is_original_image_url_present:
            return Response(
                {"error": f"Downloading original image is not available in the "
                          f"{user_subscription.tier.account_tier_name} tier. Please Upgrade."
                 }, status=status.HTTP_400_BAD_REQUEST)

    @method_decorator(cache_page(60 * 60 * 6))
    def get(self, request, **kwargs) -> HttpResponse:
        """
        Download the original image
        """
        logging.log(
            level=logging.DEBUG,
            msg=f"Client with IP {request.client_ip} accessing the Download Original Image API."
        )
        db_query_params = {}
        db_query_params.update(dict(image_id=kwargs['image_id']))
        db_query_params.update(dict(image_author=request.user))

        # Verify if the image UUID belongs to auth user
        image_query_set = UploadedImages.objects.filter(**db_query_params)
        if not image_query_set:
            return Response({"error": "Image does not belong to the user."},
                            status=status.HTTP_403_FORBIDDEN)

        self.check_user_subscription()

        image_query_object = image_query_set.get()
        return self.retrieve_original_image(image_query_object)


class DownloadImageThumbnail(APIView):
    """
    Download the image thumbnail
    curl -L -X GET -u "username:password" \
        --remote-name --remote-header-name \
        http://localhost:8080/api/image/<image-uuid>/size/<thumbnail-size>/
    """
    permission_classes = (IsAuthenticated,)

    def _create_and_save_thumbnail(self, image_query_obj, height, thumbnail_name):
        file_name = image_query_obj.image_path.name
        # calculate thumbnail size
        current_width = image_query_obj.image_path.width
        current_height = image_query_obj.image_path.height
        aspect_ratio = math.floor(current_width / current_height)
        width = height * aspect_ratio
        thumbnail_size = width, height
        # create and store thumbnail
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)
        thumbnail_directory = os.path.join(settings.MEDIA_ROOT, "thumbnails")
        new_file_path = os.path.join(thumbnail_directory, thumbnail_name)
        os.makedirs(thumbnail_directory, exist_ok=True)
        with Image.open(file_path) as img_file:
            img_file.thumbnail(thumbnail_size, Image.ANTIALIAS)
            img_file.save(new_file_path)
            return new_file_path

    def _retrieve_image_thumbnail(self, image_query_obj, new_height):
        new_thumbnail_name = "{}px_{}".format(
                new_height, image_query_obj.image_name
        )
        thumbnail_path = self._create_and_save_thumbnail(
            image_query_obj, new_height, new_thumbnail_name
        )
        with open(thumbnail_path, 'rb') as image_thumbnail:
            file_wrapper = FileWrapper(image_thumbnail)
            file_mimetype = mimetypes.guess_type(thumbnail_path)
            response = HttpResponse(file_wrapper, content_type=file_mimetype,
                                    status=status.HTTP_200_OK)
            response['X-Sendfile'] = new_thumbnail_name
            response['Content-Length'] = os.stat(thumbnail_path).st_size
            response['Content-Disposition'] = \
                'attachment; filename={}'.format(smart_str(new_thumbnail_name))
            return response

    @method_decorator(cache_page(60 * 60 * 6))
    def get(self, request, **kwargs) -> HttpResponse:
        """
        Download the image thumbnail
        """
        logging.log(
            level=logging.DEBUG,
            msg=f"Client with IP {request.client_ip} accessing the Download Image Thumbnail API."
        )
        db_query_params = {}
        db_query_params.update(dict(image_id=kwargs['image_id']))
        db_query_params.update(dict(image_author=request.user))

        # Verify if the image UUID belongs to auth user
        image_query_set = UploadedImages.objects.filter(**db_query_params)
        if not image_query_set:
            return Response({"error": "Image does not belong to the user."},
                            status=status.HTTP_403_FORBIDDEN)

        # Verify subscription status of auth user for retrieving original images
        user_subscription_query_set = Subscription.objects.filter(user=request.user)
        if not user_subscription_query_set:
            return Response({"error": "User is not subscribed to any plan."},
                            status=status.HTTP_400_BAD_REQUEST)

        user_subscription = user_subscription_query_set.first()
        image_thumbnails = user_subscription.tier.thumbnail_sizes.all()
        input_thumbnail_size = kwargs['thumbnail_size_px']
        filter_thumbnail_sizes = filter(
                lambda thumbnail: thumbnail.thumbnail_size_px == input_thumbnail_size,
                image_thumbnails
        )
        if not next(filter_thumbnail_sizes, None):
            return Response(
                {"error": f"Downloading image thumbnail of size {input_thumbnail_size} is not available in the "
                          f"{user_subscription.tier.account_tier_name} tier."
                 }, status=status.HTTP_400_BAD_REQUEST)

        image_query_object = image_query_set.get()
        return self._retrieve_image_thumbnail(image_query_object, input_thumbnail_size)


class DownloadTempImage(DownloadImage):
    """
    Download the image thumbnail
    curl -L -X GET -u "username:password" \
        --remote-name --remote-header-name \
        http://localhost:8080/api/image/<image-temp-id>/
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, **kwargs) -> HttpResponse:
        """
        Download the image through temp URL
        """
        logging.log(
            level=logging.DEBUG,
            msg=f"Client with IP {request.client_ip} accessing the Download Image Temp URL."
        )
        db_query_params = {}
        image_temp_uri = reverse('download_temp_image',
                                 kwargs={"image_temp_id": kwargs['image_temp_id']})
        db_query_params.update(dict(image_temp_uri=image_temp_uri))
        db_query_params.update(dict(image_author=request.user))

        # Verify if the image UUID belongs to auth user
        image_query_set = UploadedImages.objects.filter(**db_query_params)
        if not image_query_set:
            return Response({"error": "Image does not exist."},
                            status=status.HTTP_400_BAD_REQUEST)

        image_query_object = image_query_set.first()
        is_url_still_valid = (image_query_object.image_created_at +
                              timedelta(seconds=image_query_object.image_uri_expiry_sec)) > timezone.now()
        if is_url_still_valid:
            self.check_user_subscription()
            return self.retrieve_original_image(image_query_object)
        else:
            return Response({"error": "The temporary URL has been expired."},
                            status=status.HTTP_404_NOT_FOUND)
