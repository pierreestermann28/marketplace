# mediahub/services/images.py
from mediahub.models import ImageAsset


def create_image_asset(
    *, user, image, source: str = ImageAsset.Source.UPLOAD
) -> ImageAsset:
    return ImageAsset.objects.create(user=user, image=image, source=source)
