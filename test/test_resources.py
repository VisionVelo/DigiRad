# coding=utf-8
"""Resources test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'info@vision-velo.de'
__date__ = '2025-05-13'
__copyright__ = 'Copyright 2025, Vision Velo UG (haftungsbeschränkt)'

import os
import unittest

from qgis.PyQt.QtGui import QIcon

PLUGIN_DIR = os.path.dirname(os.path.dirname(__file__))


class DigiRadDialogTest(unittest.TestCase):
    """Test rerources work."""

    def setUp(self):
        """Runs before each test."""
        pass

    def tearDown(self):
        """Runs after each test."""
        pass

    def test_icon_png(self):
        """Test the plugin icon loads from its file path."""
        path = os.path.join(PLUGIN_DIR, 'icon.png')
        icon = QIcon(path)
        self.assertFalse(icon.isNull())

    def test_rich_text_images(self):
        """Test the images referenced by the .ui rich text exist on disk."""
        for name in ('bmv_resize_trans.png', 'nicht_investiv.png'):
            self.assertTrue(
                os.path.exists(os.path.join(PLUGIN_DIR, 'res', name)), name)

