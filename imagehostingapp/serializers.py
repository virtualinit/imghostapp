
from rest_framework import serializers
from imagehostingapp.models import UploadedImages


VALID_UPLOAD_FORMATS = (
    'image/png',
    'image/jpg',
)


class ImageUploadSerializer(serializers.ModelSerializer):
    """
    File Upload Serializer
    """
    image_author = serializers.StringRelatedField(
        read_only=True, default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = UploadedImages
        fields = ('image_id', 'image_desc', 'image_path', 'image_uri',
                  'image_author', 'image_uri_expiry_sec', 'image_temp_uri')

    def create(self, validated_data):
        uploaded_image = UploadedImages(
            image_desc=validated_data.get('image_desc', ''),
            image_path=validated_data['image_path'],
            image_author=self.context['request'].user,
            image_uri_expiry_sec=validated_data.get('image_uri_expiry_sec', -1),
        )
        uploaded_image.save()
        return uploaded_image

    def validate_image_path(self, value):
        """
        Check for valid image formats
        """
        if value.content_type not in VALID_UPLOAD_FORMATS:
            raise serializers.ValidationError(
                f"{value.content_type} not supported. Please upload PNG or JPG images."
            )
        return value

    def validate_image_uri_expiry_sec(self, value):
        """
        Check for valid URI expiry seconds
        """
        if value and (value < 300 or value > 30000):
            raise serializers.ValidationError(
                f"{value} should be between 300 to 30000 seconds."
            )
        return value


class ListImagesSerializer(serializers.ModelSerializer):
    """
    List Images Serializer
    """
    class Meta:
        model = UploadedImages
        fields = ('image_name', 'image_desc', 'image_created_at')
