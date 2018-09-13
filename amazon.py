#!/usr/bin/env python
# -*- coding: utf-8 -*-
from datetime import datetime
import urllib2
import time
import hashlib
import hmac
import base64
import lxml.etree as ET
import configparser

#config
config = configparser.ConfigParser()
config.read('config.ini')
amazon_access_key = config['AMAZON']['amazon_access_key'].encode("utf-8")
amazon_secret_key = config['AMAZON']['amazon_secret_key'].encode("utf-8")
amazon_associate_tag = config['AMAZON']['amazon_associate_tag'].encode("utf-8")
inputfilename = config['AMAZON']['inputfilename'].encode("utf-8")

class Amazon:

    def __init__(self):
        #initialize variables
        startTime = datetime.now()
        f = open(inputfilename, "r")
        f.readline()
        self.lines = f.readlines()
        f.close()

    def __iter__(self):
        current = 0
        lines = self.lines
        for line in lines:
            current += 1
            line = line.replace("\n", "").strip()
            salesrank = self.GetSalesRank(line)
            #print salesrank
            price = self.GetPrice(line)
            ItemAttributes = self.GetItemAttributes(line)
            cur = [line, ItemAttributes[0], ItemAttributes[1], ItemAttributes[2], ItemAttributes[3],ItemAttributes[4],ItemAttributes[5],ItemAttributes[6], ItemAttributes[7], salesrank, price]
            yield cur

    def GetItemAttributes(self, asin):
        while True:
            try:
                responsegroup = 'ItemAttributes'
                xml = self.__item_lookup(asin, responsegroup)
                break
            except KeyboardInterrupt:
                raise
            except BaseException:
                continue
        try:
            #print xml
            data = ET.fromstring(xml)
            values = [
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "ItemAttributes"]/*[name() = "UPC"]',
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "ItemAttributes"]/*[name() = "Brand"]',
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "ItemAttributes"]/*[name() = "MPN"]',
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "ItemAttributes"]/*[name() = "Title"]'
                    ]
            float_values = [
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "ItemAttributes"]/*[name() = "PackageDimensions"]/*[name() = "Length"]',
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "ItemAttributes"]/*[name() = "PackageDimensions"]/*[name() = "Width"]',
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "ItemAttributes"]/*[name() = "PackageDimensions"]/*[name() = "Height"]',
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "ItemAttributes"]/*[name() = "PackageDimensions"]/*[name() = "Weight"]'
                    ]
            index = 0
            result = []
            for value in values:
                try:
                    data_to_append = data.xpath(value)[0].text
                    result.append(data_to_append)
                    index += 1
                except IndexError:
                    result.append('')
                    index += 1
                    continue
            index = 0
            for value in float_values:
                try:
                    data_to_append = float(data.xpath(float_values[index])[0].text) / 100.0
                    result.append(data_to_append)
                    index += 1
                except IndexError:
                    result.append('')
                    index += 1
                    continue

            return result
        except BaseException as e:
            print e
            result = ['', '', '', '', '', '', '', '']
            return result

    def GetPrice(self, asin):
        while True:
            try:
                responsegroup = 'Offers'
                xml = self.__item_lookup(asin, responsegroup)
                break
            except KeyboardInterrupt:
                raise
            except BaseException:
                continue
        try:
            data = ET.fromstring(xml)
            #print xml
            total = data.xpath(
                '//*[name() = "Offers"]/*[name() = "TotalOffers"]')[0].text
            if int(total) > 0:
                amount = data.xpath(
                    '//*[name() = "OfferListing"]/*[name() = "Price"]/*[name() = "FormattedPrice"]')[0].text
                currency = data.xpath(
                    '//*[name() = "OfferListing"]/*[name() = "Price"]/*[name() = "CurrencyCode"]')[0].text
                return '%s %s' % (amount, currency)
            else:
                return 'N/A (unavailable)'
        except BaseException:
            return 'N/A'

    def GetSalesRank(self, asin):
        while True:
            try:
                responsegroup = 'SalesRank'
                xml = self.__item_lookup(asin, responsegroup)
                break
            except KeyboardInterrupt:
                raise
            except BaseException:
                continue
        try:
            #print xml
            data = ET.fromstring(xml)
            salesrank = data.xpath(
                    '//*[name() = "ItemLookupResponse"]/*[name() = "Items"]/*[name() = "Item"]/*[name() = "SalesRank"]')[0].text
            return salesrank

        except BaseException:
            return 'N/A'

    def __item_lookup(self, asin, responsegroup, **options):
        params = options
        params['Operation'] = 'ItemLookup'
        params['ItemId'] = asin
        params['ResponseGroup'] = responsegroup
        return self.__sendRequest(params)

    def __buildUrl(self, params):
        params['Service'] = 'AWSECommerceService'
        params['AWSAccessKeyId'] = amazon_access_key
        params['AssociateTag'] = amazon_associate_tag

        params['Version'] = '2011-08-01'
        params['Timestamp'] = time.strftime(
            '%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        sorted_params = sorted(params.items())
        req_list = []
        for p in sorted_params:
            pair = "%s=%s" % (p[0], urllib2.quote(p[1].encode('utf-8')))
            req_list.append(pair)
        urlencoded_reqs = '&'.join(req_list)
        string_to_sign = "GET\necs.amazonaws.com\n/onca/xml\n%s" % urlencoded_reqs
        hmac_digest = hmac.new(
            amazon_secret_key,
            string_to_sign,
            hashlib.sha256).digest()
        base64_encoded = base64.b64encode(hmac_digest)
        signature = urllib2.quote(base64_encoded)
        url = "http://ecs.amazonaws.com/onca/xml?%s&Signature=%s" % (
            urlencoded_reqs, signature)
        return url

    def __sendHttpRequest(self, url):
        opener = urllib2.build_opener()
        opener.addheaders = [
            ('User-Agent',
             'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36')]
        return opener.open(url).read()

    def __sendRequest(self, params):
        url = self.__buildUrl(params)
        result = self.__sendHttpRequest(url)
        return result
