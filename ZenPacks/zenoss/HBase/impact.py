######################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is
# installed.
#
######################################################################


from zope.component import adapts
from zope.interface import implements

from Products.ZenRelations.ToManyRelationship import ToManyRelationshipBase
from Products.ZenRelations.ToOneRelationship import ToOneRelationship
from Products.ZenUtils.guid.interfaces import IGlobalIdentifier

from ZenPacks.zenoss.Impact.impactd import Trigger
from ZenPacks.zenoss.Impact.impactd.relations import ImpactEdge
from ZenPacks.zenoss.Impact.impactd.interfaces import IRelationshipDataProvider
from ZenPacks.zenoss.Impact.impactd.interfaces import INodeTriggers

AVAILABILITY = 'AVAILABILITY'
PERCENT = 'policyPercentageTrigger'
THRESHOLD = 'policyThresholdTrigger'
RP = 'ZenPacks.zenoss.HBase'


def guid(obj):
    return IGlobalIdentifier(obj).getGUID()


def edge(source, target):
    return ImpactEdge(source, target, RP)


def getRedundancyTriggers(guid, format, **kwargs):
    """Return a general redundancy set of triggers."""

    return (
        Trigger(guid, format % 'DOWN', PERCENT, AVAILABILITY, dict(
            kwargs, state='DOWN', dependentState='DOWN', threshold='100',
        )),
        Trigger(guid, format % 'DEGRADED', THRESHOLD, AVAILABILITY, dict(
            kwargs, state='DEGRADED', dependentState='DEGRADED', threshold='1',
        )),
        Trigger(guid, format % 'ATRISK_1', THRESHOLD, AVAILABILITY, dict(
            kwargs, state='ATRISK', dependentState='DOWN', threshold='1',
        )),
        Trigger(guid, format % 'ATRISK_2', THRESHOLD, AVAILABILITY, dict(
            kwargs, state='ATRISK', dependentState='ATRISK', threshold='1',
        )),
    )


def getPoolTriggers(guid, format, **kwargs):
    """Return a general pool set of triggers."""

    return (
        Trigger(guid, format % 'DOWN', PERCENT, AVAILABILITY, dict(
            kwargs, state='DOWN', dependentState='DOWN', threshold='100',
        )),
        Trigger(guid, format % 'DEGRADED', THRESHOLD, AVAILABILITY, dict(
            kwargs, state='DEGRADED', dependentState='DEGRADED', threshold='1',
        )),
        Trigger(guid, format % 'ATRISK_1', THRESHOLD, AVAILABILITY, dict(
            kwargs, state='DEGRADED', dependentState='DOWN', threshold='1',
        )),
    )


class BaseRelationsProvider(object):
    implements(IRelationshipDataProvider)

    relationship_provider = RP
    impact_relationships = None
    impacted_by_relationships = None

    def __init__(self, adapted):
        self._object = adapted

    def belongsInImpactGraph(self):
        return True

    def guid(self):
        if not hasattr(self, '_guid'):
            self._guid = guid(self._object)

        return self._guid

    def impact(self, relname):
        relationship = getattr(self._object, relname, None)
        if relationship:
            if isinstance(relationship, ToOneRelationship):
                obj = relationship()
                if obj:
                    yield edge(self.guid(), guid(obj))

            elif isinstance(relationship, ToManyRelationshipBase):
                for obj in relationship():
                    yield edge(self.guid(), guid(obj))

    def impacted_by(self, relname):
        relationship = getattr(self._object, relname, None)
        if relationship:
            if isinstance(relationship, ToOneRelationship):
                obj = relationship()
                if obj:
                    yield edge(guid(obj), self.guid())

            elif isinstance(relationship, ToManyRelationshipBase):
                for obj in relationship():
                    yield edge(guid(obj), self.guid())

    def getEdges(self):
        device = self._object.device()
        if self.impact_relationships is not None:
            for impact_relationship in self.impact_relationships:
                for impact in self.impact(impact_relationship):
                    yield impact

        if self.impacted_by_relationships is not None:
            for impacted_by_relationship in self.impacted_by_relationships:
                # Check if zookeeper component is on device and
                # use it instead 'hbase host'
                if impacted_by_relationship == 'hbase_host' and\
                        hasattr(device, 'zookeepers') and\
                        getattr(device, 'zookeepers')():
                    impacted_by_relationship = 'zookeepers'
                for impacted_by in self.impacted_by(impacted_by_relationship):
                    yield impacted_by


class BaseTriggers(object):
    implements(INodeTriggers)

    def __init__(self, adapted):
        self._object = adapted


# ----------------------------------------------------------------------------
# Impact relationships

class HBaseRegionServerRelationsProvider(BaseRelationsProvider):
    impacted_by_relationships = ['hbase_host']
    impact_relationships = ['regions']


class HBaseHRegionRelationsProvider(BaseRelationsProvider):
    impacted_by_relationships = ['server']

    def getEdges(self):
        for impact in super(HBaseHRegionRelationsProvider, self).getEdges():
            yield impact
        component = self._object
        # Add impact 'table' relation for region
        for hbt in component.hbase_tables():
            if hbt.id == component.table:
                yield edge(self.guid(), guid(hbt))


class HBaseTableRelationsProvider(BaseRelationsProvider):

    def getEdges(self):
        for impact in super(HBaseTableRelationsProvider, self).getEdges():
            yield impact

        component = self._object
        # Get all regions from all region servers
        regions = [
            r for s in component.device().hbase_servers() for r in s.regions()
        ]
        # Add impacted by 'region' relation for tables
        for hbr in regions:
            if hbr.table == component.id:
                yield edge(guid(hbr), self.guid())
