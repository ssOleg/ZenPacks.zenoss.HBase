##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
"""
Custom ZenPack initialization code. All code defined in this module will be
executed at startup time in all Zope clients.
"""
import math
import logging
log = logging.getLogger('zen.HBase')

import Globals

from Products.Zuul import getFacade
from Products.ZenEvents.EventManagerBase import EventManagerBase
from Products.ZenModel.Device import Device
from Products.ZenModel.ZenPack import ZenPack as ZenPackBase
from Products.ZenRelations.RelSchema import ToManyCont, ToOne
from Products.ZenRelations.zPropertyCategory import setzPropertyCategory
from Products.ZenUtils.Utils import unused
from Products.Zuul.interfaces import ICatalogTool

unused(Globals)

# Categorize zProperties.
setzPropertyCategory('zHBase', 'HBase')
setzPropertyCategory('zHBaseUsername', 'HBase')
setzPropertyCategory('zHBasePasword', 'HBase')
setzPropertyCategory('zHBasePort', 'HBase')

# Modules containing model classes. Used by zenchkschema to validate
# bidirectional integrity of defined relationships.
productNames = (
    'HBaseRegionServer',
    'HBaseTable',
    'HBaseRegion'
    )

# Useful to avoid making literal string references to module and class names
# throughout the rest of the ZenPack.
ZP_NAME = 'ZenPacks.zenoss.HBase'
MODULE_NAME = {}
CLASS_NAME = {}
for product_name in productNames:
    MODULE_NAME[product_name] = '.'.join([ZP_NAME, product_name])
    CLASS_NAME[product_name] = '.'.join([ZP_NAME, product_name, product_name])

# Useful for components' ids.
NAME_SPLITTER = '(.)'

# Define new device relations.
NEW_DEVICE_RELATIONS = (
    ('hbase_servers', 'HBaseRegionServer'),
    ('hbase_tables', 'HBaseTable'),
    )

NEW_COMPONENT_TYPES = (
    'ZenPacks.zenoss.HBase.HBaseRegionServer.HBaseRegionServer',
    'ZenPacks.zenoss.HBase.HBaseTable.HBaseTable',
    'ZenPacks.zenoss.HBase.HBaseRegion.HBaseRegion',
    )

# Add new relationships to Device if they don't already exist.
for relname, modname in NEW_DEVICE_RELATIONS:
    if relname not in (x[0] for x in Device._relations):
        Device._relations += (
            (relname,
             ToManyCont(ToOne, '.'.join((ZP_NAME, modname)), 'hbase_host')),
        )


# Add ErrorNotification to Device
def setErrorNotification(self, msg):
    if msg == 'clear':
        self.dmd.ZenEventManager.sendEvent(dict(
            device=self.id,
            summary=msg,
            eventClass='/Status',
            eventKey='ConnectionError',
            severity=0,
            ))
    else:
        self.dmd.ZenEventManager.sendEvent(dict(
            device=self.id,
            summary=msg,
            eventClass='/Status',
            eventKey='ConnectionError',
            severity=5,
            ))

    return


def getErrorNotification(self):
    return


def regionservers(self):
    return self.hbase_servers.objectIds()


def getClearEvents(self):
    """
    Attempt to clear all non-existing component events.

    The modeler plugin calls setDiscoverGuests which will cause
    ApplyDataMap to call this getter method first to validate that
    the setter even needs to be run. For this reason, this method
    must actually perform the discovery logic.
    """
    self.clear_events()
    return True


def setClearEvents(self, value):
    """
    This method should typically never be called because the
    getDiscoverGuests method will always return the same value that
    the modeler plugin sets.
    """
    self.clear_events()


def clear_events(self):
    """
    Discover and clear all events, related to components which had
    benn deleted.
    """
    zep = getFacade('zep')
    zep_filter = zep.createEventFilter(
        element_identifier=(self.id),
        event_class=('/Status'),
        severity=(5, 4),
        status=(0, 1)
    )
    results = zep.getEventSummariesGenerator(filter=zep_filter)

    component_list = [x.getObject().id for x in self.componentSearch()]
    for res in results:
        key = res['occurrence'][0]['actor'].get('element_sub_identifier')
        if key and key not in component_list:
            del_filter = zep.createEventFilter(uuid=res['uuid'])
            zep.closeEventSummaries(eventFilter=del_filter)


Device.setErrorNotification = setErrorNotification
Device.getErrorNotification = getErrorNotification
Device.regionserver_ids = property(regionservers)
Device.getClearEvents = getClearEvents
Device.setClearEvents = setClearEvents
Device.clear_events = clear_events


class ZenPack(ZenPackBase):
    """
    ZenPack loader that handles custom installation and removal tasks.
    """

    packZProperties = [
        ('zHBase', 'false', 'bool'),
        ('zHBaseUsername', '', 'string'),
        ('zHBasePasword', '', 'password'),
        ('zHBasePort', '8080', 'string'),
    ]

    def install(self, app):
        super(ZenPack, self).install(app)

        log.info('Adding HBase relationships to existing devices')
        self._buildDeviceRelations()

    def remove(self, app, leaveObjects=False):
        if not leaveObjects:
            log.info('Removing HBase components')
            cat = ICatalogTool(app.zport.dmd)
            for brain in cat.search(types=NEW_COMPONENT_TYPES):
                component = brain.getObject()
                component.getPrimaryParent()._delObject(component.id)

            # Remove our Device relations additions.
            Device._relations = tuple(
                [x for x in Device._relations
                    if x[0] not in NEW_DEVICE_RELATIONS])

            log.info('Removing HBase device relationships')
            self._buildDeviceRelations()

        super(ZenPack, self).remove(app, leaveObjects=leaveObjects)

    def _buildDeviceRelations(self):
        for d in self.dmd.Devices.getSubDevicesGen():
            d.buildRelations()
