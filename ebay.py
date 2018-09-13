#!/usr/bin/env python
# ebay.py
import json
from lxml import objectify, etree
import requests
from statistics import mean
import numpy as np
import datetime
from xlsxwriter import Workbook
import configparser
import dateutil.parser

#CONFIG
config = configparser.ConfigParser()
config.read('config.ini')
eBayAuthToken = config['EBAY']['eBayAuthToken'].encode("utf-8")
eBayAppID  = config['EBAY']['eBayAppID'].encode("utf-8")
trending_price_days = int(config['EBAY']['trending_price_days'].encode("utf-8"))

#if rowcount in search results is equal or more than this number, then do not search anymore.
results_min = int(config['EBAY']['results_min'].encode("utf-8"))

#limit get_active page count
active_page_count = int(config['EBAY']['active_page_count'].encode("utf-8"))


#date for eBay trending price.
today = datetime.datetime.now()
today = dateutil.parser.parse(str(today)).toordinal()
ebay_day = today + trending_price_days

#ebay condition IDs
new_id = 1000
new_other_id = 1500
used_id = 3000
for_parts_id = 7000


EM = objectify.ElementMaker(annotate=False)

xs = np.array([1, 2, 3, 4, 5, 6], dtype=np.float64)

def dict2xml(root, data):
    for key, value in data.items():
        if isinstance(value, dict):
            sub_root = getattr(EM, key)()
            element = dict2xml(sub_root, value)
            root.append(element)
        elif isinstance(value, list):
            sub_root = getattr(EM, key)
            for val in value:
                if isinstance(val, dict):
                    element = dict2xml(sub_root(), val)
                else:
                    element = sub_root(val)
                root.append(element)
        else:
            element = getattr(EM, key)(value)
            root.append(element)
    return root


def xml2dict(root):
    data = {}
    namespace = root.nsmap.get(None, "")
    clean_tag = lambda tag: tag.replace("{%s}" % namespace, "")

    for element in root.getchildren():
        if not hasattr(element, "pyval"):
            sub_data = xml2dict(element)
            name, val = clean_tag(element.tag), sub_data
        else:
            name, val = clean_tag(element.tag), element.pyval
        if name in data:
            if isinstance(data[name], list):
                data[name].append(val)
            else:
                data[name] = [data[name], val]
        else:
            data[name] = val
    return data

def best_fit(X, Y):
    xbar = sum(X)/len(X)
    ybar = sum(Y)/len(Y)
    n = len(X)
    numer = sum([xi*yi for xi,yi in zip(X, Y)]) - n * xbar * ybar
    denum = sum([xi**2 for xi in X]) - n * xbar**2
    b = numer / denum
    a = ybar - b * xbar
    return a, b

class ebayAPI:

    def __init__(self):
        self.cur = []

    def search(self, searchParams):

        transactions = {"UPC": searchParams[0], "Items": []}
        active = []

        for searchKeyword in searchParams:
            if len(transactions["Items"]) >= results_min:
                break

            try:
                f = self.get_items(searchKeyword)
            except UnicodeEncodeError:
                continue

            if f:
                for item in f:
                    ts = self.get_item_transactions(item)
                    if not ts:
                        continue
                    try:
                        for transaction in ts:
                            price, date, condition = transaction
                            if not price or not date:
                                continue
                            data = {
                                "ItemID": item[0],
                                "Title": item[1],
                                "Price": price,
                                "Date": date,
                                "Condition": condition}
                            transactions["Items"].append(data)
                    except ValueError:
                        continue
                active_list = self.get_active(searchKeyword)
                active.extend(active_list)
        print transactions["Items"]
        print len(transactions["Items"])

        transactions["active"] = len(active)

        try:
            transactions["active average"] = sum(active) / len(active)
        except ZeroDivisionError:
            transactions["active average"] = 'N/A'

        transactions["sold"] = len(transactions["Items"])

        try:
            transactions["sold average"] = sum(item["Price"] for item in transactions["Items"]) / len(transactions["Items"])
        except ZeroDivisionError:
            transactions["sold average"] = 'N/A'

        price_list = []
        date_list = []
        new_price_list = []
        new_date_list = []
        new_other_price_list = []
        new_other_date_list = []
        used_price_list = []
        used_date_list = []
        for_parts_price_list = []
        for_parts_date_list = []

        for item in transactions["Items"]:
            price_list.append(item["Price"])
            date = dateutil.parser.parse(item["Date"])
            date_list.append(date.toordinal())
            if int(item["Condition"]) == new_id:
                new_price_list.append(item["Price"])
                date = dateutil.parser.parse(item["Date"])
                new_date_list.append(date.toordinal())
            elif int(item["Condition"]) == new_other_id:
                new_other_price_list.append(item["Price"])
                date = dateutil.parser.parse(item["Date"])
                new_other_date_list.append(date.toordinal())
            elif int(item["Condition"]) == used_id:
                used_price_list.append(item["Price"])
                date = dateutil.parser.parse(item["Date"])
                used_date_list.append(date.toordinal())
            elif int(item["Condition"]) == for_parts_id:
                for_parts_price_list.append(item["Price"])
                date = dateutil.parser.parse(item["Date"])
                for_parts_date_list.append(date.toordinal())

        try:
            transactions["trending price"] = self.trend_price(date_list, price_list)
        except ZeroDivisionError:
            transactions["trending price"] = 'N/A'

        try:
            transactions["trending price new"] = self.trend_price(new_date_list, new_price_list)
        except ZeroDivisionError:
            transactions["trending price new"] = 'N/A'

        try:
            transactions["trending price new other"] = self.trend_price(new_other_date_list, new_other_price_list)
        except ZeroDivisionError:
            transactions["trending price new other"] = 'N/A'

        try:
            transactions["trending price used"] = self.trend_price(used_date_list, used_price_list)
        except ZeroDivisionError:
            transactions["trending price used"] = 'N/A'

        try:
            transactions["trending price for parts"] = self.trend_price(for_parts_date_list, for_parts_price_list)
        except ZeroDivisionError:
            transactions["trending price for parts"] = 'N/A'
        
        return [transactions["active"], transactions["active average"], transactions["sold"], transactions["sold average"], transactions["trending price"], transactions["trending price new"], transactions["trending price new other"], transactions["trending price used"], transactions["trending price for parts"]]

    def get_active(self, upc):
        precios = []
        jsondict = {'paginationOutput': {
            'totalPages': 1,
            'pageNumber': 0
        }}
        page = 1
        while (jsondict["paginationOutput"]["pageNumber"] != jsondict["paginationOutput"]["totalPages"]):
            print page, active_page_count, jsondict["paginationOutput"]["totalPages"]
            url = "http://svcs.ebay.com/services/search/FindingService/v1?OPERATION-NAME=findItemsByKeywords&SERVICE-VERSION=1.0.0&SECURITY-APPNAME={appid}&RESPONSE-DATA-FORMAT=XML&REST-PAYLOAD&keywords={upc}&paginationInput.entriesPerPage=100&paginationInput.pageNumber=%d" % page
            f = requests.get(url.format(appid=eBayAppID, upc=upc))

            xmlresult = objectify.fromstring(f.content)
            jsondict = xml2dict(xmlresult)
            #print jsondict
            try:
                for item in jsondict["searchResult"]["item"]:
                    if item["sellingStatus"]["sellingState"] == "Active":
                        precios.append(
                            item["sellingStatus"]["convertedCurrentPrice"])
            except:
                print jsondict
                pass
            page += 1
            if page > active_page_count:
                break

        return precios

    def get_item_transactions(self, item):
        headers = {
            "X-EBAY-API-APP-ID": eBayAppID,
            "X-EBAY-API-CALL-NAME": "GetItemTransactions",
            "X-EBAY-API-COMPATIBILITY-LEVEL": "986",
            "X-EBAY-API-SITEID": "0",
            "Content-Type": "text/xml"
        }

        itemID, title, startDate, endDate = item
        data = {
            "RequesterCredentials": {
                "eBayAuthToken": eBayAuthToken
            },
            "ItemID": int(itemID),
        }

        call_req = getattr(EM, "GetItemTransactionsRequest")(
            xmlns="urn:ebay:apis:eBLBaseComponents")

        xml = dict2xml(call_req, data)
        data = etree.tostring(xml, encoding="UTF-8", xml_declaration=True,
                              pretty_print=True)

        result = requests.request(
            "post",
            "https://api.ebay.com/ws/api.dll",
            headers=headers,
            data=data)

        xmlresult = objectify.fromstring(result.content)
        resultsdict = xml2dict(xmlresult)
        print resultsdict
        transactions = []

        try:
            condition = resultsdict['Item']['ConditionID']
        except:
            condition = 0

        try:
            transaction = resultsdict["TransactionArray"]["Transaction"]
            
            if isinstance(transaction, list):
                for t in transaction:
                    if t.get('UnpaidItem'):
                        transactions.append([None, None, None])
                    else:
                        transactions.append(([t["AmountPaid"],
                                              t["CreatedDate"],
                                              condition],
                                              ))

            elif transaction.get('UnpaidItem'):
                transactions.append([None, None, None])
            else:
                transactions.append(([transaction["AmountPaid"],
                                      transaction["CreatedDate"],
                                      condition]))
        except KeyError:
            try:
                transactions.append((resultsdict['Item']['SellingStatus']['ConvertedCurrentPrice'],
                                    self.calculate_avg(startDate, endDate),
                                    condition
                                    ))
            except KeyError:
                pass
        except Exception as e:
            print resultsdict
            pass
        #print transactions
        return transactions

    def get_items(self, upc):
        url = "http://svcs.ebay.com/services/search/FindingService/v1?OPERATION-NAME=findCompletedItems&SERVICE-VERSION=1.7.0&SECURITY-APPNAME={appid}&RESPONSE-DATA-FORMAT=XML&REST-PAYLOAD&keywords={upc}"
        f = requests.get(url.format(appid=eBayAppID, upc=upc))

        xmlresult = objectify.fromstring(f.content)
        jsondict = xml2dict(xmlresult)
        results = []
        try:
            if isinstance(jsondict["searchResult"]["item"], list):
                for item in jsondict["searchResult"]["item"]:
                    if item["sellingStatus"]["sellingState"] == "EndedWithSales" and not item[
                            "sellingStatus"].get("bidCount"):
                        results.append([item["itemId"], item["title"], item["listingInfo"][
                                    "startTime"], item["listingInfo"]["endTime"]])
            else:
                item = jsondict["searchResult"]["item"]
                if item["sellingStatus"]["sellingState"] == "EndedWithSales" and not item[
                        "sellingStatus"].get("bidCount"):
                    results.append([item["itemId"], item["title"], item["listingInfo"][
                                "startTime"], item["listingInfo"]["endTime"]])
        except:
            pass
        return results

    def calculate_avg(self, date1, date2):
        # https://stackoverflow.com/questions/17713521/python-calculate-the-average-of-datetime-with-milliseconds
        date1 = datetime.datetime.strptime(date1, '%Y-%m-%dT%H:%M:%S.%fZ')
        date2 = datetime.datetime.strptime(date2, '%Y-%m-%dT%H:%M:%S.%fZ')
        delta = (date2 - date1) / 2
        mid = date1 + delta
        return mid.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

    def trend_price(self, X, Y):
        a, b = best_fit(X, Y)
        xi = ebay_day
        yfit = a + b*xi
        return yfit
