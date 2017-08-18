# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core import signing
from django.core.exceptions import ImproperlyConfigured
from django.utils.six.moves.urllib.parse import urljoin

from sorl.thumbnail.base import ThumbnailBackend
from sorl.thumbnail.conf import settings, defaults as default_settings
from sorl.thumbnail.images import ImageFile, DummyImageFile
from sorl.thumbnail import default


logger = logging.getLogger(__name__)


class LazyBackend(ThumbnailBackend):
    def get_thumbnail(self, file_, geometry_string, **options):
        logger.debug('Getting thumbnail for file [%s] at [%s]', file_, geometry_string)

        if file_:
            if not hasattr(file_, 'url') or not file_.url.startswith('http'):
                raise Exception('Cannot use lazy generation')
            file_ = file_.url
            source = ImageFile(file_)
        else:
            if settings.THUMBNAIL_DUMMY:
                return DummyImageFile(geometry_string)
            else:
                logger.error('missing file_ argument in get_thumbnail()')
                return

        # preserve image filetype
        if settings.THUMBNAIL_PRESERVE_FORMAT:
            options.setdefault('format', self._get_format(source))

        for key, value in self.default_options.items():
            options.setdefault(key, value)

        # For the future I think it is better to add options only if they
        # differ from the default settings as below. This will ensure the same
        # filenames being generated for new options at default.
        for key, attr in self.extra_options:
            value = getattr(settings, attr)
            if value != getattr(default_settings, attr):
                options.setdefault(key, value)

        name = self._get_thumbnail_filename(source, geometry_string, options)
        thumbnail = ImageFile(name, default.storage)
        cached = default.kvstore.get(thumbnail)

        if cached:
            return cached

        # We have to check exists() because the Storage backend does not
        # overwrite in some implementations.
        if settings.THUMBNAIL_FORCE_OVERWRITE or not thumbnail.exists():
            try:
                source_image = default.engine.get_image(source)
            except IOError as e:
                logger.exception(e)
                if settings.THUMBNAIL_DUMMY:
                    return DummyImageFile(geometry_string)
                else:
                    # if S3Storage says file doesn't exist remotely, don't try to
                    # create it and exit early.
                    # Will return working empty image type; 404'd image
                    logger.warning(
                        'Remote file [%s] at [%s] does not exist',
                        file_, geometry_string,
                    )
                    return thumbnail

            # We might as well set the size since we have the image in memory
            image_info = default.engine.get_image_info(source_image)
            options['image_info'] = image_info
            size = default.engine.get_image_size(source_image)
            source.set_size(size)

            try:
                self._create_thumbnail(source_image, geometry_string, options,
                                       thumbnail)
                # do not create alternative resolutions!
            finally:
                default.engine.cleanup(source_image)

        # If the thumbnail exists we don't create it, the other option is
        # to delete and write but this could lead to race conditions so I
        # will just leave that out for now.
        default.kvstore.get_or_set(source)
        # do not save thumbnail in kvstore!
        url_data = {'file_': file_,
                    'geometry_string': geometry_string,
                    'options': options}
        signed_data = signing.dumps(url_data,
                                    key=settings.THUMBNAIL_SECRET_KEY)
        if not settings.THUMBNAIL_SERVER_URL.startswith('http') or \
            not settings.THUMBNAIL_SERVER_URL.endswith('/'):
            raise ImproperlyConfigured(
                'THUMBNAIL_SERVER_URL must start with "http" and end with "/"')
        url = urljoin(settings.THUMBNAIL_SERVER_URL, 'hash/') + signed_data
        thumbnail.url = url
        return thumbnail

    def delete(self, file_, delete_file=True):
        if not hasattr(file_, 'url') or not file_.url.startswith('http'):
            raise Exception('Canmot use lazy generation')
        file_ = file_.url
        super(LazyBackend, self).delete(file_, delete_file)
