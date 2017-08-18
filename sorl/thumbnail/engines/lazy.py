# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from PIL import Image

from sorl.thumbnail.engines.base import EngineBase


class SourceImagePlaceholder(object):
    format = None
    format_description = None

    def __init__(self):
        self.im = None
        self.mode = ""
        self.size = (0, 0)
        self.palette = None
        self.info = {}
        self.category = Image.NORMAL
        self.readonly = 0
        self.pyaccess = None

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]

    def crop(self, box=None):
        left, upper, right, lower = box
        self.size = (right - left, lower - upper)
        return self

    def resize(self, size, resample=Image.NEAREST):
        self.size = size
        return self


class Engine(EngineBase):

    def create(self, image, geometry, options):
        image = self.cropbox(image, geometry, options)
        image = self.orientation(image, geometry, options)
        # image = self.colorspace(image, geometry, options)
        # image = self.remove_border(image, options)
        image = self.scale(image, geometry, options)
        image = self.crop(image, geometry, options)
        # image = self.rounded(image, geometry, options)
        # image = self.blur(image, geometry, options)
        # image = self.padding(image, geometry, options)
        return image

    def get_image(self, source):
        # TODO maybe copy more information
        source = Image.open(source)
        image = SourceImagePlaceholder()
        image.size = source.size
        return image

    def get_image_size(self, image):
        return image.size

    def get_image_info(self, image):
        return image.info or {}

    def write(self, image, options, thumbnail):
        pass

    def _cropbox(self, image, x, y, x2, y2):
        return image.crop((x, y, x2, y2))

    def _scale(self, image, width, height):
        return image.resize((width, height), resample=Image.ANTIALIAS)

    def _crop(self, image, width, height, x_offset, y_offset):
        return image.crop((x_offset, y_offset,
                           width + x_offset, height + y_offset))
