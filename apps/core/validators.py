from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _

MAX_IMAGE_UPLOAD_SIZE = 5 * 1024 * 1024


def validate_image_file_size(file):
    if file.size > MAX_IMAGE_UPLOAD_SIZE:
        raise ValidationError(
            _("This file is too large (%(size)s). The maximum allowed size is %(max_size)s.")
            % {"size": filesizeformat(file.size), "max_size": filesizeformat(MAX_IMAGE_UPLOAD_SIZE)}
        )
