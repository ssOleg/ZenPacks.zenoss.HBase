##############################################################################
#
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
log = logging.getLogger('zen.HBaseTest')

from mock import Mock, patch, sentinel

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenUtils.Utils import prepId
import ZenPacks.zenoss.HBase.dsplugins as dsplugins
from ZenPacks.zenoss.HBase import NAME_SPLITTER
from ZenPacks.zenoss.HBase.tests.utils import test_device, load_data


class TestHBaseMasterPlugin(BaseTestCase):

    def afterSetUp(self):
        super(TestHBaseMasterPlugin, self).afterSetUp()
        dc = self.dmd.Devices.createOrganizer('/Server')
        self.d = dc.createInstance('hbase.testDevice')
        self.plugin = dsplugins.HBaseMasterPlugin()

    def test_get_events(self):
        data = load_data('HBaseCollector.json')
        self.plugin.component = 'localhost_11111'
        ds = Mock()
        ds.component = sentinel.component
        ds.regionserver_ids = ['test']
        ds.region_ids = ['test']
        self.plugin.process(data)
        self.plugin.add_maps(data, ds)
        result = self.plugin.get_events(data, ds)
        # Check event for added server.
        self.assertIn({
            'eventClass': '/Status',
            'severity': 2,
            'summary': "Region server 'localhost:44451' is added"
        }, result)
        # Check event for removed server.
        ds.regionserver_ids = ['localhost_11111', 'test']
        self.plugin.add_maps(data, ds)
        self.assertIn({
            'eventClass': '/Status',
            'severity': 2,
            'summary': "Region server 'test' is removed"
        }, self.plugin.get_events(data, ds))

    def test_process(self):
        data = load_data('HBaseCollector.json')
        result = self.plugin.process(data)
        self.assertEquals(result.get('average_load'), (2.0, 'N'))
        self.assertEquals(result.get('live_servers'), (1, 'N'))
        self.assertEquals(result.get('percent_dead_servers'), (50.0, 'N'))
        self.assertEquals(result.get('requests_per_second'), (0, 'N'))
        self.assertEquals(result.get('dead_servers'), (1, 'N'))
        self.assertEquals(result.get('regions'), (2, 'N'))

    def test_onSuccess(self):
        data = self.plugin.new_data()
        config = ds = Mock()
        ds.component = sentinel.component
        config.datasources = [ds]
        # Test not clear events if no data in values.
        self.assertEquals(data, self.plugin.onSuccess(data, config))

        # Test clear events if there is data in values.
        data['values'][sentinel.component] = 'test'
        self.assertIn({
            'severity': 0,
            'eventClass': '/Status',
            'component': sentinel.component,
            'eventKey': 'hbase_monitoring_error',
            'summary': 'Monitoring ok'
        }, self.plugin.onSuccess(data, config).get('events'))

    def test_onError(self):
        self.plugin.component = sentinel.component
        # Test clear events if no events came in data.
        self.assertIn({
            'severity': 4,
            'eventClass': '/Status',
            'component': sentinel.component,
            'eventKey': 'hbase_monitoring_error',
            'summary': 'test'
        }, self.plugin.onError('test', sentinel.config).get('events'))


class TestHBaseRegionServerPlugin(BaseTestCase):

    def afterSetUp(self):
        super(TestHBaseRegionServerPlugin, self).afterSetUp()
        dc = self.dmd.Devices.createOrganizer('/Server')
        self.d = dc.createInstance('hbase.testDevice')
        self.plugin = dsplugins.HBaseRegionServerPlugin()

    def test_process(self):
        data = load_data('HBaseCollector.json')
        self.plugin.component = 'localhost_44451'
        result = self.plugin.process(data)
        self.assertEquals(result.get('max_heap_mb'), (997, 'N'))
        self.assertEquals(result.get('memstore_size_mb'), (0, 'N'))
        self.assertEquals(result.get('number_of_store_files'), (1, 'N'))
        self.assertEquals(result.get('read_requests'), (9, 'N'))
        self.assertEquals(result.get('current_compacted_kv'), (8, 'N'))
        self.assertEquals(result.get('total_compacting_kv'), (8, 'N'))
        self.assertEquals(result.get('used_heap_mb'), (26, 'N'))
        self.assertEquals(result.get('number_of_stores'), (1, 'N'))
        self.assertEquals(result.get('store_file_index_size_mb'), (0, 'N'))
        self.assertEquals(result.get('store_file_size_mb'), (0, 'N'))
        self.assertEquals(result.get('write_requests'), (1, 'N'))

    def test_get_events(self):
        data = load_data('HBaseCollector.json')
        self.plugin.component = 'localhost_11111'
        ds = Mock()
        ds.component = sentinel.component
        ds.regionserver_ids = []
        result = self.plugin.get_events(data, ds)
        # Check event for dead server.
        self.assertIn({
            'severity': 4,
            'eventClass': '/Status',
            'component': 'localhost_11111',
            'eventKey': 'hbase_monitoring_error',
            'summary': "Region server 'localhost:11111' is dead"
        }, result)
        # Check clear event for dead server.
        self.plugin.component = 'localhost_44451'
        self.assertIn({
            'severity': 0,
            'eventClass': '/Status',
            'component': 'localhost_44451',
            'eventKey': 'hbase_monitoring_error',
            'summary': "Region server 'localhost:44451' is dead"
        }, self.plugin.get_events(data, ds))

    def test_add_maps(self):
        data = load_data('HBaseCollector.json')
        result = self.plugin.add_maps(data, sentinel.ds)
        self.assertEquals(result, [])


class TestHBaseHRegionPlugin(BaseTestCase):

    def afterSetUp(self):
        super(TestHBaseHRegionPlugin, self).afterSetUp()
        dc = self.dmd.Devices.createOrganizer('/Server')
        self.d = dc.createInstance('hbase.testDevice')
        self.plugin = dsplugins.HBaseHRegionPlugin()

    def test_process(self):
        data = load_data('HBaseCollector.json')
        self.plugin.component = '{0}{1}{2}'.format(
            'localhost_44451', NAME_SPLITTER, 'LVJPT1QtLCww')
        result = self.plugin.process(data)
        self.assertEquals(result.get('memstore_size_mb'), (0, 'N'))
        self.assertEquals(result.get('number_of_store_files'), (1, 'N'))
        self.assertEquals(result.get('read_requests'), (9, 'N'))
        self.assertEquals(result.get('current_compacted_kv'), (8, 'N'))
        self.assertEquals(result.get('total_compacting_kv'), (8, 'N'))
        self.assertEquals(result.get('number_of_stores'), (1, 'N'))
        self.assertEquals(result.get('store_file_index_size_mb'), (0, 'N'))
        self.assertEquals(result.get('store_file_size_mb'), (0, 'N'))
        self.assertEquals(result.get('write_requests'), (1, 'N'))


class TestHBaseTablePlugin(BaseTestCase):

    def afterSetUp(self):
        super(TestHBaseTablePlugin, self).afterSetUp()
        dc = self.dmd.Devices.createOrganizer('/Server')
        self.d = dc.createInstance('hbase.testDevice')
        self.plugin = dsplugins.HBaseTablePlugin()

    def test_onSuccess(self):
        data = self.plugin.new_data()
        config = ds = Mock()
        ds.component = sentinel.component
        config.datasources = [ds]
        # Test not clear events if no data in values.
        self.assertEquals(data, self.plugin.onSuccess(data, config))

        # Test clear events if there is data in maps.
        om = Mock()
        om.compname = 'hbase_tables/test'
        data['maps'] = [om]
        self.assertIn({
            'severity': 0,
            'eventClass': '/Status',
            'component': 'test',
            'eventKey': 'hbase_table_monitoring_error',
            'summary': 'Monitoring ok'
        }, self.plugin.onSuccess(data, config).get('events'))

    def test_get_events(self):
        data = load_data('HBaseTableStatus.txt')
        self.plugin.component = sentinel.component
        result = self.plugin.get_events(data, sentinel.ds)
        self.assertIn({
            'severity': 4,
            'eventClass': '/Status',
            'component': sentinel.component,
            'eventKey': 'hbase_monitoring_error',
            'summary': "The table 'sentinel.component' is disabled"
        }, result)

    def test_get_events_clear(self):
        data = load_data('HBaseTableEnabledStatus.txt')
        self.plugin.component = sentinel.component
        result = self.plugin.get_events(data, sentinel.ds)
        self.assertIn({
            'severity': 0,
            'eventClass': '/Status',
            'component': sentinel.component,
            'eventKey': 'hbase_monitoring_error',
            'summary': 'Monitoring ok'
        }, result)

    def test_add_maps(self):
        data = load_data('HBaseTableStatus.txt')
        schema = load_data('HBaseTableColumnFamily.json')
        self.plugin.component = sentinel.component
        result = self.plugin.add_maps(data, schema, sentinel.ds)
        om = result[0]
        self.assertEquals(om.compname, 'hbase_tables/sentinel.component')
        self.assertEquals(om.modname, 'HBase table state')
        self.assertEquals(om.enabled, 'false')
        self.assertEquals(om.compaction, '')
        self.assertEquals(om.number_of_col_families, 2)
        self.assertEquals(
            om.col_family_block_size, 'colfam1: 640.0KB; colfam2: 612.0B')


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestHBaseMasterPlugin))
    suite.addTest(makeSuite(TestHBaseRegionServerPlugin))
    suite.addTest(makeSuite(TestHBaseHRegionPlugin))
    suite.addTest(makeSuite(TestHBaseTablePlugin))
    return suite
