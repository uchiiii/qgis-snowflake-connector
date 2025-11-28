# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Snowflake Connector for QGIS
 This package includes the Snowflake Connector for QGIS.
                              -------------------
        begin                : 2024-08-07
        copyright            : (C) 2024 by Snowflake
        email                : erick.cuberojimenez@snowflake.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is licensed under the MIT License. You may use, modify,  *
 *   and distribute it under the terms specified in the license.           *
 *                                                                         *
 *   MIT License                                                           *
 *                                                                         *
 *   Permission is hereby granted, free of charge, to any person obtaining *
 *   a copy of this software and associated documentation files (the       *
 *   "Software"), to deal in the Software without restriction, including   *
 *   without limitation the rights to use, copy, modify, merge, publish,   *
 *   distribute, sublicense, and/or sell copies of the Software, and to    *
 *   permit persons to whom the Software is furnished to do so, subject    *
 *   to the following conditions:                                          *
 *                                                                         *
 *   The above copyright notice and this permission notice shall be        *
 *   included in all copies or substantial portions of the Software.       *
 *                                                                         *
 *   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,       *
 *   EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF    *
 *   MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.*
 *   IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY  *
 *   CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,  *
 *   TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE     *
 *   SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.                *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = "Snowflake Inc."
__date__ = "2024-08-07"
__copyright__ = "(C) 2024 by Snowflake"

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = "$Format:%H$"

import os
import sys
import inspect

from qgis.core import QgsProcessingAlgorithm, QgsApplication, QgsProviderRegistry, QgsMessageLog, Qgis

from .providers.sf_metadata_provider import SFMetadataProvider

from .qgis_snowflake_connector_algorithm import QGISSnowflakeConnectorAlgorithm

from .providers.sf_data_item_provider import SFDataItemProvider

from .providers.sf_source_select_provider import SFSourceSelectProvider
from .qgis_snowflake_connector_provider import QGISSnowflakeConnectorProvider
from .resources_rc import *
from qgis.gui import QgsGui
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]

if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)


class QGISSnowflakeConnectorPlugin(object):
    def __init__(self):
        self.provider = None
        self.iface = None
        self.toolbar_action = None

    def is_snowflake_layer(self, layer):
        """Check if a layer is a Snowflake layer"""
        if not layer or not layer.dataProvider():
            return False
        provider = layer.dataProvider()
        # Check provider key - Snowflake provider returns "snowflakedb"
        return hasattr(provider, 'name') and provider.name() == "snowflakedb"

    def refresh_snowflake_layer(self, layer):
        """Refresh/reload data for a Snowflake layer"""
        if self.is_snowflake_layer(layer):
            provider = layer.dataProvider()
            provider.reloadData()
            layer.triggerRepaint()
            layer.reload()
            QgsMessageLog.logMessage(
                f"Reloaded data for layer: {layer.name()}",
                "Snowflake Plugin",
                Qgis.MessageLevel.Info,
            )

    def initProcessing(self):
        """Init Processing provider for QGIS >= 3.8."""
        self.postgis_native_provider = QgsApplication.processingRegistry().providerById(
            "native"
        )

        if self.postgis_native_provider:
            self.qgis_snowflake_connector_algorithm = QGISSnowflakeConnectorAlgorithm()
            self.postgis_native_provider.addAlgorithm(
                self.qgis_snowflake_connector_algorithm
            )

        self.tm = QgsApplication.taskManager()
        self.sf_source_select_provider = SFSourceSelectProvider("mssp")
        QgsGui.sourceSelectProviderRegistry().addProvider(
            self.sf_source_select_provider
        )

        self.sf_data_item_provider = SFDataItemProvider("dipk", "Snowflake")
        QgsApplication.dataItemProviderRegistry().addProvider(
            self.sf_data_item_provider
        )

        self.provider = QGISSnowflakeConnectorProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        registry = QgsProviderRegistry.instance()
        sf_metadata_provider = SFMetadataProvider()
        registry.registerProvider(sf_metadata_provider)

    def initGui(self):
        self.initProcessing()

        # Store iface reference if available
        try:
            from qgis.utils import iface
            self.iface = iface

            # Add toolbar button for reloading active Snowflake layer
            if self.iface:
                self.toolbar_action = QAction(
                    QIcon(":/plugins/qgis-snowflake-connector/icon.png"),
                    "Reload Snowflake Layer",
                    self.iface.mainWindow()
                )
                self.toolbar_action.setToolTip("Reload data from Snowflake for the active layer")
                self.toolbar_action.triggered.connect(self.reload_active_layer)

                # Add to Plugins menu
                self.iface.addPluginToMenu("Snowflake", self.toolbar_action)

                # Optionally add to toolbar
                self.iface.addToolBarIcon(self.toolbar_action)
        except Exception:
            pass

    def reload_active_layer(self):
        """Reload the currently active layer if it's a Snowflake layer"""
        if not self.iface:
            return

        layer = self.iface.activeLayer()
        if self.is_snowflake_layer(layer):
            self.refresh_snowflake_layer(layer)
        else:
            QgsMessageLog.logMessage(
                "Active layer is not a Snowflake layer",
                "Snowflake Plugin",
                Qgis.MessageLevel.Warning,
            )

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
        self.postgis_native_provider.algorithms().remove(
            self.qgis_snowflake_connector_algorithm
        )
        self.postgis_native_provider.refreshAlgorithms()
        QgsGui.sourceSelectProviderRegistry().removeProvider(
            self.sf_source_select_provider
        )
        QgsApplication.dataItemProviderRegistry().removeProvider(
            self.sf_data_item_provider
        )

        # Clean up toolbar action
        if self.iface and self.toolbar_action:
            self.iface.removePluginMenu("Snowflake", self.toolbar_action)
            self.iface.removeToolBarIcon(self.toolbar_action)
