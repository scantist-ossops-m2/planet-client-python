# Copyright 2023 Planet Labs PBC.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.
"""Example of creating and downloading multiple orders.

This is an example of submitting two orders, waiting for them to complete, and
downloading them. The orders each clip a set of images to a specific area of
interest (AOI), so they cannot be combined into one order.

[Planet Explorer](https://www.planet.com/explorer/) was used to define
the AOIs and get the image ids.
"""
from pathlib import Path
import planet
from planet import data_filter
import json
from datetime import datetime
import pytest


@pytest.fixture
def search_filter(get_test_file_json):
    filename = 'data_search_filter_2022-01.json'
    return get_test_file_json(filename)


@pytest.fixture
def item_descriptions(get_test_file_json):
    item_ids = [
        '20220125_075509_67_1061',
        '20220125_075511_17_1061',
        '20220125_075650_17_1061'
    ]
    items = [get_test_file_json(f'data_item_{id}.json') for id in item_ids]
    return items


@pytest.mark.anyio
async def test_snippet_search(search_filter):
    '''Code snippet for search.'''
    # --8<-- [start:search]
    async with planet.Session() as sess:
        client = sess.client('data')
        items_list = [
            item async for item in client.search(['PSScene'],
                                                 search_filter=search_filter,
                                                 name="My Search",
                                                 sort="acquired asc",
                                                 limit=10)
        ]
    # --8<-- [end:search]
    assert len(items_list) == 10


@pytest.mark.anyio
async def test_snippet_create_search(search_filter):
    '''Code snippet for create_search.'''
    # --8<-- [start:create_search]
    async with planet.Session() as sess:
        client = sess.client('data')
        response = await client.create_search(item_types=['PSScene'],
                                              search_filter=search_filter,
                                              name="My Search")
    # --8<-- [end:create_search]
    assert 'PSScene' in response['item_types']


@pytest.mark.anyio
async def test_snippet_update_search(search_filter):
    '''Code snippet for update_search.'''
    # --8<-- [start:update_search]
    async with planet.Session() as sess:
        client = sess.client('data')
        response = await client.update_search(
            search_id='66722b2c8d184d4f9fb8b8fcf9d1a08c',
            item_types=['PSScene'],
            search_filter=search_filter,
            name="My Search")
    # --8<-- [end:update_search]
    assert 'PSScene' not in response['item_types']
    assert '66722b2c8d184d4f9fb8b8fcf9d1a08c' in response['id']


# list_searches
async def test_snippet_list_searches(sort, search_type, limit):
    '''Code snippet for list_searches.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        async for item in client.list_searches(sort=sort,
                                               search_type=search_type,
                                               limit=limit):
            return item


# delete_search
async def test_snippet_delete_search(search_id):
    '''Code snippet for delete_search.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        await client.delete_search(search_id)


# get_search
async def test_snippet_get_search(search_id):
    '''Code snippet for get_search.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        items = await client.get_search(search_id)
        return items


# run_search
async def test_snippet_run_search(search_id):
    '''Code snippet for run_search.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        async for item in client.run_search(search_id):
            return item


# get_stats
async def test_snippet_get_stats(item_types, search_filter, interval):
    '''Code snippet for get_stats.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        items = await client.get_stats(item_types=item_types,
                                       search_filter=search_filter,
                                       interval=interval)
        return items


# list_item_assets
async def test_snippet_list_item_assets(item_type_id, item_id):
    '''Code snippet for list_item_assets.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        assets = await client.list_item_assets(item_type_id, item_id)
    return assets


# get_asset
async def test_snippet_get_asset(item_type, item_id, asset_type):
    '''Code snippet for get_asset.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        asset = await client.get_asset(item_type, item_id, asset_type)
    return asset


# activate_asset
async def test_snippet_activate_asset(item_type, item_id, asset_type):
    '''Code snippet for activate_asset.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        asset = await client.get_asset(item_type, item_id, asset_type)
        await client.activate_asset(asset)


# wait_asset
async def test_snippet_wait_asset(item_type, item_id, asset_type):
    '''Code snippet for wait_asset.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        asset = await client.get_asset(item_type, item_id, asset_type)
        _ = await client.wait_asset(asset, callback=print)


# download_asset w/o checksum
async def test_snippet_download_asset_without_checksum(item_type,
                                                       item_id,
                                                       asset_type,
                                                       filename,
                                                       directory,
                                                       overwrite):
    '''Code snippet for download_asset without a checksum.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        asset = await client.get_asset(item_type, item_id, asset_type)
        path = await client.download_asset(asset=asset,
                                           filename=filename,
                                           directory=Path(directory),
                                           overwrite=overwrite)
        return path


# download_asset w/ checksum
async def test_snippet_download_asset_with_checksum(item_type,
                                                    item_id,
                                                    asset_type,
                                                    filename,
                                                    directory,
                                                    overwrite):
    '''Code snippet for download_asset with a checksum.'''
    async with planet.Session() as sess:
        client = sess.client('data')
        asset = await client.get_asset(item_type, item_id, asset_type)
        path = await client.download_asset(asset=asset,
                                           filename=filename,
                                           directory=Path(directory),
                                           overwrite=overwrite)
        client.validate_checksum(asset, path)
        return path


# Create search filters
def create_search_filter():
    '''Create a search filter.'''

    # Geometry you wish to clip to
    with open("aoi.geojson") as f:
        geom = json.loads(f.read())

    # Build your filters with all types of requirements
    date_range_filter = data_filter.date_range_filter("acquired",
                                                      gte=datetime(month=1,
                                                                   day=1,
                                                                   year=2017),
                                                      lte=datetime(month=1,
                                                                   day=1,
                                                                   year=2018))
    clear_percent_filter = data_filter.range_filter('clear_percent', 90)
    cloud_cover_filter = data_filter.range_filter('cloud_cover', None, 0.1)
    geom_filter = data_filter.geometry_filter(geom)
    asset_filter = data_filter.asset_filter(
        ["basic_analytic_4b", "basic_udm2", "ortho_visual"])
    permission_filter = data_filter.permission_filter()
    std_quality_filter = data_filter.std_quality_filter()

    # Search filter containing all filters listed above
    search_filter = data_filter.and_filter([
        date_range_filter,
        clear_percent_filter,
        cloud_cover_filter,
        geom_filter,
        asset_filter,
        permission_filter,
        std_quality_filter
    ])

    return search_filter
