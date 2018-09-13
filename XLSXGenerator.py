#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
startTime = datetime.now()

import os
import json
import json
import urllib2
import time
import hashlib
import hmac
import base64
import lxml.etree as ET
import ebay
import amazon
from xlsxwriter import Workbook
import configparser

#config
config = configparser.ConfigParser()
config.read('config.ini')
outputfilename = config['GENERATOR']['outputfilename'].encode("utf-8")

#XLSX writer workbook and worksheet instances
wb = Workbook(outputfilename)
#wb = Workbook(filename)
ws = wb.add_worksheet()

#columns for headers
ws_col_ASIN = 0
ws_col_UPC = 1
ws_col_Brand = 2
ws_col_MPN = 3
ws_col_Title = 4
ws_col_Quantity = 5
ws_col_MSRP = 6
ws_col_E_MSRP = 7
ws_col_Length = 8
ws_col_Width = 9
ws_col_Heigth = 10
ws_col_Weigth = 11
ws_col_amazon_sales_rank = 12
ws_col_amazon_price = 13
ws_col_act = 14
ws_col_act_avg = 15
ws_col_sold = 16
ws_col_sold_avg = 17
ws_col_trending_price = 18
ws_col_trending_price_new = 19
ws_col_trending_price_new_other = 20
ws_col_trending_price_used = 21
ws_col_trending_price_for_parts = 22


#write headers to xlsx
ws.write(0, ws_col_ASIN,     'ASIN'  )
ws.write(0, ws_col_UPC,      'UPC'   )
ws.write(0, ws_col_Brand,    'Brand' )
ws.write(0, ws_col_MPN,      'MPN'   )
ws.write(0, ws_col_Title,    'Title' )
ws.write(0, ws_col_Quantity, 'Quantity')
ws.write(0, ws_col_MSRP,     'MSRP'  )
ws.write(0, ws_col_E_MSRP,   'Extended MSRP')
ws.write(0, ws_col_Length,   'Length')
ws.write(0, ws_col_Width,    'Width' )
ws.write(0, ws_col_Heigth,   'Heigth')
ws.write(0, ws_col_Weigth,   'Weigth')
ws.write(0, ws_col_amazon_sales_rank, 'AMZ Sales Rank')
ws.write(0, ws_col_amazon_price,      'Amazon Price')
ws.write(0, ws_col_act,      'EBY Active Count')
ws.write(0, ws_col_act_avg,  'EBY Avg Active Price')
ws.write(0, ws_col_sold,     'EBY Sold Count')
ws.write(0, ws_col_sold_avg, 'EBY Avg Sold Price')
ws.write(0, ws_col_trending_price,           'EBY Trend')
ws.write(0, ws_col_trending_price_new,       'EBY Trend - New')
ws.write(0, ws_col_trending_price_new_other, 'EBY Trend - New Other')
ws.write(0, ws_col_trending_price_used,      'EBY Trend - Used')
ws.write(0, ws_col_trending_price_for_parts, 'EBY Trend - For Parts')

class XLSXGenerator:
    def __init__(self, filename = None):
        row = 1
        amazon_data = amazon.Amazon()
        for item in amazon_data:
            print 'Amazon Data-- Begin'
            print item
            print 'Amazon Data-- End'
            ws.write(row, ws_col_ASIN, item[0])
            ws.write(row, ws_col_UPC, item[1])
            ws.write(row, ws_col_Brand, item[2])
            ws.write(row, ws_col_MPN, item[3])
            ws.write(row, ws_col_Title, item[4])
            ws.write(row, ws_col_Quantity, None)
            ws.write(row, ws_col_MSRP, None)
            ws.write(row, ws_col_E_MSRP, None)
            ws.write(row, ws_col_Length, item[5])
            ws.write(row, ws_col_Width, item[6])
            ws.write(row, ws_col_Heigth, item[7])
            ws.write(row, ws_col_Weigth, item[8])
            ws.write(row, ws_col_amazon_sales_rank, item[9])
            ws.write(row, ws_col_amazon_price, item[10])
            ebay_data = ebay.ebayAPI().search([item[1], item[3], item[4]])
            ws.write(row, ws_col_act, ebay_data[0])
            ws.write(row, ws_col_act_avg, ebay_data[1])
            ws.write(row, ws_col_sold, ebay_data[2])
            ws.write(row, ws_col_sold_avg, ebay_data[3])
            ws.write(row, ws_col_trending_price, ebay_data[4])
            ws.write(row, ws_col_trending_price_new, ebay_data[5])
            ws.write(row, ws_col_trending_price_new_other, ebay_data[6])
            ws.write(row, ws_col_trending_price_used, ebay_data[7])
            ws.write(row, ws_col_trending_price_for_parts, ebay_data[8])
            row += 1
        wb.close()

XLSXGenerator()
