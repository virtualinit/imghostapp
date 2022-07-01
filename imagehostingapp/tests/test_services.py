import json
import os.path
from os import path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import SimpleTestCase
from django.conf import settings

from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from imagehostingapp.models import Subscription, ImageThumbnailSize, AccountTiers


class PingAPITestCase(SimpleTestCase):
    """
    Test Ping API
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()
        cls.ping_url = reverse('api_ping_server')

    def test_ping_image_hosting_app(self):
        # Make request
        response = self.client.get(self.ping_url)
        # Check status response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertJSONEqual(
            json.dumps({'service': 'ImageHostingApp 0.1.0', 'status': 'RUNNING'}),
            response.json()
        )


class UploadListImageTestCase(APITestCase):
    """
    Test Upload and List an Image
    """

    PASSWORD = 'pa$$w0rd'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = User.objects.create_superuser(
            'superuser1', 'email@domain.tld', cls.PASSWORD
        )
        cls.client = APIClient()
        cls.list_upload_image_url = reverse('list_upload_image-list')

    def test_upload_image_403(self):
        # Make request
        response = self.client.post(self.list_upload_image_url)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertJSONEqual(
            json.dumps({'detail': 'Authentication credentials were not provided.'}),
            response.json()
        )

    def test_upload_image_404(self):
        self.client.login(username=self.admin_user.username,
                          password=self.PASSWORD)
        # Make request
        response = self.client.post(self.list_upload_image_url)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertJSONEqual(
            json.dumps({'image_path': ['No file was submitted.']}),
            response.json()
        )

    def test_upload_image_tiff(self):
        self.client.login(username=self.admin_user.username,
                          password=self.PASSWORD)
        test_img_path = path.join(
            settings.BASE_DIR,
            'imagehostingapp/tests/testdata/test_img_1.tiff'
        )
        with open(test_img_path, 'rb') as file:
            f_content = file.read()
        image = SimpleUploadedFile(
            "test_img_1.tiff", f_content, content_type="image/tiff"
        )
        payload = {
            'image_desc': 'some random image 1',
            'image_path': image,
        }
        # Make request
        response = self.client.post(self.list_upload_image_url, data=payload)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertJSONEqual(
            json.dumps({'image_path': ['image/tiff not supported. Please upload PNG or JPG images.']}),
            response.json()
        )

    def test_upload_image_png(self):
        self.client.login(username=self.admin_user.username,
                          password=self.PASSWORD)
        test_img_path = path.join(
            settings.BASE_DIR,
            'imagehostingapp/tests/testdata/test_img_2.png'
        )
        with open(test_img_path, 'rb') as file:
            f_content = file.read()
        image = SimpleUploadedFile(
            "test_img_2.png", f_content, content_type="image/png"
        )
        payload = {
            'image_desc': 'some random image 2',
            'image_path': image,
        }
        # Make request
        response = self.client.post(self.list_upload_image_url, data=payload)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertJSONEqual(
            json.dumps({'image_desc': 'some random image 2',
                        'image_author': 'superuser1',
                        'image_uri_expiry_sec': -1}),
            response.json()
        )

        # Make GET request - list Images
        get_response = self.client.get(self.list_upload_image_url)
        # Check response status
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertIn('image_name', get_response.json()[0])
        self.assertIn('image_desc', get_response.json()[0])
        self.assertEqual(get_response.json()[0]['image_name'], 'test_img_2.png',
                         "Uploaded image name should be preserved")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # remove test files uploaded
        upload_folder = path.join(settings.MEDIA_ROOT, "user_images")
        for test_file in os.listdir(upload_folder):
            if test_file.startswith("test_img_"):
                os.remove(path.join(upload_folder, test_file))


class DownloadImageTestCase(APITestCase):
    """
    Test Download an Image
    """

    PASSWORD = 'pa$$w0rd'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = User.objects.create_superuser(
            'superuser2', 'email@domain.tld', cls.PASSWORD
        )
        cls.thumbnail_size = \
            ImageThumbnailSize.objects.create(thumbnail_size_px=200)
        cls.account_tier = AccountTiers.objects.create(
            account_tier_name="Premium",
            is_original_image_url_present=True,
            is_expiring_links_available=False
        )
        cls.client = APIClient()
        cls.list_upload_image_url = reverse('list_upload_image-list')

    def test_download_image_subscribed_user(self):
        # create subscription
        self.account_tier.thumbnail_sizes.add(*[self.thumbnail_size])
        Subscription.objects.create(user=self.admin_user, tier=self.account_tier)
        # login
        self.client.login(username=self.admin_user.username,
                          password=self.PASSWORD)
        test_img_path = path.join(
            settings.BASE_DIR,
            'imagehostingapp/tests/testdata/test_img_2.png'
        )
        with open(test_img_path, 'rb') as file:
            f_content = file.read()
        image = SimpleUploadedFile(
            "test_img_2.png", f_content, content_type="image/png"
        )
        payload = {
            'image_desc': 'some random image 4',
            'image_path': image,
        }
        # Make request
        response = self.client.post(self.list_upload_image_url, data=payload)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_json = response.json()
        self.assertIn("image_url", response_json, "Response should have image_url")

        image_uuid = response_json["image_url"].split("/")[-2]
        download_image_url = reverse('download_image', kwargs={"image_id": image_uuid})
        # Make request
        response = self.client.get(download_image_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image/png', response._content_type_for_repr)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # remove test files uploaded
        upload_folder = path.join(settings.MEDIA_ROOT, "user_images")
        for test_file in os.listdir(upload_folder):
            if test_file.startswith("test_img_"):
                os.remove(path.join(upload_folder, test_file))


class DownloadImageInvalidTestCase(APITestCase):
    """
    Test Download an Image - Invalid Scenario
    """

    PASSWORD = 'pa$$w0rd'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = User.objects.create_superuser(
            'superuser2', 'email@domain.tld', cls.PASSWORD
        )
        cls.thumbnail_size = \
            ImageThumbnailSize.objects.create(thumbnail_size_px=200)
        cls.account_tier = AccountTiers.objects.create(
            account_tier_name="Basic",
            is_original_image_url_present=False,
            is_expiring_links_available=False
        )
        cls.client = APIClient()
        cls.list_upload_image_url = reverse('list_upload_image-list')

    def test_download_image_subscribed_user(self):
        # create subscription
        self.account_tier.thumbnail_sizes.add(*[self.thumbnail_size])
        Subscription.objects.create(user=self.admin_user, tier=self.account_tier)
        # login
        self.client.login(username=self.admin_user.username,
                          password=self.PASSWORD)
        test_img_path = path.join(
            settings.BASE_DIR,
            'imagehostingapp/tests/testdata/test_img_2.png'
        )
        with open(test_img_path, 'rb') as file:
            f_content = file.read()
        image = SimpleUploadedFile(
            "test_img_2.png", f_content, content_type="image/png"
        )
        payload = {
            'image_desc': 'some random image 4',
            'image_path': image,
        }
        # Make request
        response = self.client.post(self.list_upload_image_url, data=payload)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_json = response.json()
        self.assertNotIn("image_url", response_json,
                         "Response should NOT have the image_url")
        self.assertIn("image_url_thumbnail_200", response_json,
                      "Response should have thumbnail URL.")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # remove test files uploaded
        upload_folder = path.join(settings.MEDIA_ROOT, "user_images")
        for test_file in os.listdir(upload_folder):
            if test_file.startswith("test_img_"):
                os.remove(path.join(upload_folder, test_file))


class DownloadThumbnailTestCase(APITestCase):
    """
    Test Download a Thumbnail
    """

    PASSWORD = 'pa$$w0rd'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = User.objects.create_superuser(
            'superuser2', 'email@domain.tld', cls.PASSWORD
        )
        cls.thumbnail_size = \
            ImageThumbnailSize.objects.create(thumbnail_size_px=400)
        cls.account_tier = AccountTiers.objects.create(
            account_tier_name="Premium",
            is_original_image_url_present=True,
            is_expiring_links_available=False
        )
        cls.client = APIClient()
        cls.list_upload_image_url = reverse('list_upload_image-list')

    def test_download_thumbnail_subscribed_user(self):
        # create subscription
        self.account_tier.thumbnail_sizes.add(*[self.thumbnail_size])
        Subscription.objects.create(user=self.admin_user, tier=self.account_tier)
        # login
        self.client.login(username=self.admin_user.username,
                          password=self.PASSWORD)
        test_img_path = path.join(
            settings.BASE_DIR,
            'imagehostingapp/tests/testdata/test_img_2.png'
        )
        with open(test_img_path, 'rb') as file:
            f_content = file.read()
        image = SimpleUploadedFile(
            "test_img_2.png", f_content, content_type="image/png"
        )
        payload = {
            'image_desc': 'some random image 6',
            'image_path': image,
        }
        # Make request
        response = self.client.post(self.list_upload_image_url, data=payload)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_json = response.json()
        self.assertIn("image_url_thumbnail_400", response_json,
                      "Response should have image_url")

        image_uuid = response_json["image_url_thumbnail_400"].split("/")[-4]
        download_thumbnail_url = reverse(
            'download_image_thumbnail',
            kwargs={"image_id": image_uuid,
                    "thumbnail_size_px": self.thumbnail_size.thumbnail_size_px}
        )
        # Make request
        response = self.client.get(download_thumbnail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image/png', response._content_type_for_repr)

        # Check for 400 error
        download_thumbnail_url = reverse(
            'download_image_thumbnail',
            kwargs={"image_id": image_uuid,
                    "thumbnail_size_px": 500}
        )
        # Make request
        response = self.client.get(download_thumbnail_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('image/png', response._content_type_for_repr)
        self.assertJSONEqual(
            json.dumps({'error': 'Downloading image thumbnail of size 500 '
                                 'is not available in the Premium tier.'}),
            response.json()
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # remove test files uploaded
        upload_folder = path.join(settings.MEDIA_ROOT, "user_images")
        for test_file in os.listdir(upload_folder):
            if test_file.startswith("test_img_"):
                os.remove(path.join(upload_folder, test_file))


class DownloadTempImageTestCase(APITestCase):
    """
    Test Downloading an Image using temp URL
    """

    PASSWORD = 'pa$$w0rd'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = User.objects.create_superuser(
            'superuser2', 'email@domain.tld', cls.PASSWORD
        )
        cls.thumbnail_size = \
            ImageThumbnailSize.objects.create(thumbnail_size_px=400)
        cls.account_tier = AccountTiers.objects.create(
            account_tier_name="Enterprise",
            is_original_image_url_present=True,
            is_expiring_links_available=True
        )
        cls.client = APIClient()
        cls.list_upload_image_url = reverse('list_upload_image-list')

    def test_download_temp_url_subscribed_user(self):
        # create subscription
        self.account_tier.thumbnail_sizes.add(*[self.thumbnail_size])
        Subscription.objects.create(user=self.admin_user, tier=self.account_tier)
        # login
        self.client.login(username=self.admin_user.username,
                          password=self.PASSWORD)
        test_img_path = path.join(
            settings.BASE_DIR,
            'imagehostingapp/tests/testdata/test_img_2.png'
        )
        with open(test_img_path, 'rb') as file:
            f_content = file.read()
        image = SimpleUploadedFile(
            "test_img_2.png", f_content, content_type="image/png"
        )
        payload = {
            'image_desc': 'some random image 6',
            'image_path': image,
            'image_uri_expiry_sec': 5000,
        }
        # Make request
        response = self.client.post(self.list_upload_image_url, data=payload)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_json = response.json()
        self.assertIn("image_temp_url", response_json,
                      "Response should have image_temp_url")

        image_temp_id = response_json["image_temp_url"].split("/")[-2]
        download_temp_url = reverse('download_temp_image',
                                    kwargs={"image_temp_id": image_temp_id})
        # Make request
        response = self.client.get(download_temp_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('image/png', response._content_type_for_repr)

    def test_download_temp_url_invalid_expiry_range(self):
        # create subscription
        self.account_tier.thumbnail_sizes.add(*[self.thumbnail_size])
        Subscription.objects.create(user=self.admin_user, tier=self.account_tier)
        # login
        self.client.login(username=self.admin_user.username,
                          password=self.PASSWORD)
        test_img_path = path.join(
            settings.BASE_DIR,
            'imagehostingapp/tests/testdata/test_img_2.png'
        )
        with open(test_img_path, 'rb') as file:
            f_content = file.read()
        image = SimpleUploadedFile(
            "test_img_2.png", f_content, content_type="image/png"
        )
        payload = {
            'image_desc': 'some random image 6',
            'image_path': image,
            'image_uri_expiry_sec': 299,
        }
        # Make request
        response = self.client.post(self.list_upload_image_url, data=payload)
        # Check response status
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertJSONEqual(
            json.dumps({'image_uri_expiry_sec': ['299 should be between 300 to 30000 seconds.']}),
            response.json()
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # remove test files uploaded
        upload_folder = path.join(settings.MEDIA_ROOT, "user_images")
        for test_file in os.listdir(upload_folder):
            if test_file.startswith("test_img_"):
                os.remove(path.join(upload_folder, test_file))
