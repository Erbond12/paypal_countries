from calendar import month
from datetime import datetime
from idlelib.pyparse import trans
from logging import exception

import pymupdf
import fitz
import csv
import pyinputplus as pyip
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import os
import requests
from requests.auth import HTTPBasicAuth
import country_converter as coco
import time

cc = coco.CountryConverter()
load_dotenv()

PAYPAL_CLIENT_ID = os.getenv("paypal_client_id")
PAYPAL_CLIENT_SECRET = os.getenv("paypal_client_secret")

pdf_to_read = "pdfs/juni.PDF"
transactionsCSVFile = "transactions.csv"

def show_image(item, title=""):
    """Display a pixmap.

    Just to display Pixmap image of "item" - ignore the man behind the curtain.

    Args:
        item: any PyMuPDF object having a "get_pixmap" method. i.e. a page
        title: a string to be used as image title

    Generates an RGB Pixmap from item using a constant DPI and using matplotlib
    to show it inline of the notebook.
    """
    DPI = 150  # use this resolution
    import numpy as np
    import matplotlib.pyplot as plt

    # %matplotlib inline
    pix = item.get_pixmap(dpi=DPI)
    img = np.ndarray([pix.h, pix.w, 3], dtype=np.uint8, buffer=pix.samples_mv)
    plt.figure(dpi=DPI)  # set the figure's DPI
    plt.title(title)  # set title of image
    _ = plt.imshow(img, extent=(0, pix.w * 72 / DPI, pix.h * 72 / DPI, 0))
    plt.show()

def highlight_headers_and_tables_found(tabs, page):
    for i, tab in enumerate(tabs):  # iterate over all tables
        for cell in tab.header.cells:
            page.draw_rect(cell, color=fitz.pdfcolor["red"], width=0.3)
        page.draw_rect(tab.bbox, color=fitz.pdfcolor["green"])
        print(f"Table {i} column names: {tab.header.names}, external: {tab.header.external}")

def find_y(row, page):
    #page.draw_rect(tab.rows[2].cells[1], color=fitz.pdfcolor["red"], width=0.3)
    #print(tab.rows[2].cells)
    #print(tab.rows[2].bbox)
    y1, y2 = 1, 3
    final_y = (row.cells[1][y2]-row.cells[1][y1])/2 + row.cells[1][y1]
    offset = 5
    final_y += offset
    print(f"final y value: {final_y}, row_cells: {row.cells[1]}")
    return final_y #

def show_modified_page(page):
    show_image(page, f"Table & Header BBoxes")

def is_row_negative(text):
    """
    Converts EU float values from string to float (
    """
    american_comma_string = text.replace(".", "").replace(",", ".")
    row_value = float(american_comma_string)
    return row_value < 0

def write_text(page, row, text="", end_of_table_width=0.0, end_of_page_width=0, not_important=False):
    #print(f"--- Text is this wide: {pymupdf.get_text_length(text)}")
    #print( f"--- Text was written with: {page.insert_text(pymupdf.Point(x, y), text)}")

    for i in range(7):
        success = page.insert_textbox(rect, text, fontsize=11-i)
        if success >= 0:
            print(f"i: {i}, text: {text}")
            return 1
    return 0

def get_date(tab):
    date_span = tab.header.names[2]
    start_date = date_span[:10]
    end_date = date_span[13:]
    list_of_dates = []

    USA_start_first_month = datetime.strptime(start_date, '%d.%m.%Y') + relativedelta(months=-1) + relativedelta(days=3)
    USA_end_first_month = datetime.strptime(start_date, '%d.%m.%Y') + relativedelta(days=1)

    USA_start_unedited = datetime.strptime(start_date, '%d.%m.%Y')
    USA_end_unedited = datetime.strptime(end_date, '%d.%m.%Y')

    USA_start_second_month = datetime.strptime(end_date, '%d.%m.%Y') + relativedelta(days=-1)
    USA_end_second_month = datetime.strptime(end_date, '%d.%m.%Y') + relativedelta(months=1) + relativedelta(days=-3)

    timezone = "T00:00:00.000Z"

    USA_start_first_month_str = USA_start_first_month.strftime('%Y-%m-%d') + timezone
    USA_end_first_month_str = USA_end_first_month.strftime('%Y-%m-%d') + timezone

    USA_start_unedited_str = USA_start_unedited.strftime('%Y-%m-%d') + timezone
    USA_end_unedited_str = USA_end_unedited.strftime('%Y-%m-%d') + timezone

    USA_start_second_month_str = USA_start_second_month.strftime('%Y-%m-%d') + timezone
    USA_end_second_month_str = USA_end_second_month.strftime('%Y-%m-%d') + timezone

    list_of_dates.append([USA_start_first_month_str, USA_end_first_month_str])
    list_of_dates.append([USA_start_unedited_str, USA_end_unedited_str])
    list_of_dates.append([USA_start_second_month_str, USA_end_second_month_str])

    print(USA_start_first_month)
    print(USA_end_first_month)

    print(USA_start_unedited)
    print(USA_end_unedited)

    print(USA_start_second_month)
    print(USA_end_second_month)

    print(list_of_dates)
    return list_of_dates

# make first line in save the headers i.e. page-nr., transactioncode, ... (non IT person readable)
# (save in csv: Transaction-code, page-nr, x (in case of the table width changing), y1, y_delta (in case the country is too long), y1+y_delta/2 (mid of the row))
# save in csv: Transaction-code, page-nr, x (in case of the table width changing), y0, y1, y2, y3 (y0 = no new line, y1 = 1 new line split in country name, ...)
def extract_transaction_codes():
    doc = fitz.open(pdf_to_read) # open a document
    rows_to_save_as_csv = [["RowNr.", "TransactionCode", "PageNr", "Table_width (x1)" , "y1", "x2", "y2", "y", "not_important", "Country_code", "Country"]]

    # get date for paypal api call
    page = doc[0]
    tabs = page.find_tables()
    date = get_date(tabs[0])

    #for j, page in enumerate(doc):
    page = doc[3] # selecet page 4
    tabs = page.find_tables()  # find the all tables
    tab = tabs[1] # for PayPal the first table is not of interest for us
    text_list = tab.extract()  # get text for all the rows as a list
    column_count = len(tab.header.names) # get the shape of the table that should be headers x rows
    end_of_table_width = tab.bbox[2] + 1.0
    end_of_page_width = page.bound()[2]

    for i, row in enumerate(text_list):
        # to be removed:
        text_to_write = "Hello World"
        if i == 1:
            text_to_write = "United Kingdom"
        elif i == 4:
            text_to_write = "Netherlands"
        elif i == 7:
            text_to_write = "rio de janeiro"
        # :till here

        # Skipp header row
        if i == 0:
            continue

        # If the empty cells in a row do not get recognized or a cell does not get recognized, then throw an exception
        current_row_size = len(text_list[i])
        if current_row_size != column_count:
            raise Exception(
                f"Row is missing/ has too many elements. It should have been {column_count} big, but is {current_row_size}")

        not_important = 0
        print(text_list[i])
        if is_row_negative(text_list[i][5]):
            not_important = 1

        # y for "---" (no country)
        y = find_y(tab.rows[i], page)

        # Textbox points
        most_right_cell = tab.rows[i].cells[-1]
        x1 = end_of_table_width
        y1 = most_right_cell[1]
        x2 = end_of_page_width
        y2 = most_right_cell[3]

        # rowNr., transactionCode, pageNr., table_width (x1) , y1, x2, y2, y, not_important
        rows_to_save_as_csv.append([i, text_list[i][4], 3, x1, y1, x2, y2, y, not_important])

    #TODO: check of file exists and create new one or just add time + date to name, but may cause some other issues when
    #      manualy using the other functions
    with open(transactionsCSVFile, 'w', newline='') as csvfile:
        transactionwriter = csv.writer(csvfile, delimiter=',', quotechar='|',
                                       quoting=csv.QUOTE_MINIMAL)
        # rowNr., transactionCode, pageNr., table_width (x1) , y1, x2, y2, y, not_important
        transactionwriter.writerows(rows_to_save_as_csv)
    show_modified_page(page)


# make first line in save the headers i.e. page-nr., transactioncode, ... (non IT person readable)
# (save in csv: Transaction-code, page-nr, x (in case of the table width changing), y1, y_delta (in case the country is too long), y1+y_delta/2 (mid of the row))
# save in csv: Transaction-code, page-nr, x (in case of the table width changing), y0, y1, y2, y3 (y0 = no new line, y1 = 1 new line split in country name, ...)
def temp():
    with open(transactionsCSVFile, 'w', newline='') as csvfile:
        transactionwriter = csv.writer(csvfile, delimiter=',', quotechar='|',
                                       quoting=csv.QUOTE_MINIMAL)

        doc = fitz.open(pdf_to_read) # open a document

        #for j, page in enumerate(doc):
        page = doc[3] # selecet page 4
        tabs = page.find_tables()  # find the all tables
        tab = tabs[1] # for PayPal the first table is not of interest for us
        text_list = tab.extract()  # get text for all the rows as a list
        column_count = len(tab.header.names) # get the shape of the table that should be headers x rows
        end_of_table_width = tab.bbox[2]
        end_of_page_width = page.bound()[2]

        for i, row in enumerate(text_list):
            text_to_write = "Hello World"
            if i == 1:
                text_to_write = "United Kingdom"
            elif i == 4:
                text_to_write = "Netherlands"
            elif i == 7:
                text_to_write = "rio de janeiro"

            not_important = False

            if i == 0:
                continue

            # If the empty cells in a row do not get recognized or a cell does not get recognized, then throw an exception
            current_row_size = len(text_list[i])
            if current_row_size != column_count:
                raise Exception(
                    f"Row is missing/ has too many elements. It should have been {column_count} big, but is {current_row_size}")

            if is_row_negative(text_list[i][5]):
                not_important = True

            print(f"i: {i}, row: {row}")
            write_text(page, tab.rows[i], text_to_write, end_of_table_width, end_of_page_width, not_important) # modify the pdf to write text at specific location

            #transactionwriter.writerow([text_list[i][4], "TEMP 3 page", end_of_table_width, y])
        show_modified_page(page)

# use python menu to have custom ui?
# have a mode for:
    # -> automatic code extraction, paypal api, writing on pdf
    # -> and manual code extraction, paypal api, writing on pdf
# When the pdf is getting written on we need to write on the pdf to make the preview (with row number),
#   but we have to make the changes on the csv file and at the end apply all changes
#   again without a preview
# It should show one page at a time so that you could check for errors. You then can
#   type c to continue or the row number, that you want to edit. Then type the new country.
#   close the preview to get to the next page?
def get_access_token():
    token_url = "https://api-m.paypal.com/v1/oauth2/token"
    basic_auth = HTTPBasicAuth(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET)
    body = "grant_type=client_credentials"

    response = requests.post(token_url, data=body, auth=basic_auth)
    print(response.json())
    return response.json()["access_token"]

def get_transactions(access_token):
    #transaction_detail_url = "https://api-m.sandbox.paypal.com/v1/reporting/transactions?start_date=2025-06-30T00:00:00.000Z&end_date=2025-06-30T23:59:59.999Z"
    transaction_detail_url = "https://api-m.paypal.com/v1/reporting/transactions?fields=transaction_info,payer_info,shipping_info,auction_info,cart_info,incentive_info,store_info&start_date=2025-07-01T00:00:00.000Z&end_date=2025-07-17T23:59:59.999Z"
    headers = {"Authorization": "Bearer " + access_token}

    transactions_response = requests.get(transaction_detail_url, headers=headers)
    print(transactions_response.json())
    return transactions_response.json()

def load_transactions_csv():
    csv_rows = []
    with open(transactionsCSVFile, mode="r") as file:
        csv_reader = csv.reader(file)
        next(csv_reader, None) # Skip header row
        for row in csv_reader:
            csv_rows.append(row)
    return csv_rows

def request_paypal_countries():
    access_token = get_access_token()
    transactions_response = get_transactions(access_token)
    transactions = transactions_response["transaction_details"]

    # Take response and reformat it to have a transaction code as key in the dict.
    #   -> easy access and no search needed
    easy_transactions_dictionary = {}
    for i, transaction in enumerate(transactions):
        key = transaction["transaction_info"]["transaction_id"]
        value = transaction["transaction_info"]
        easy_transactions_dictionary[key] = value

    # Check
    csv_rows = load_transactions_csv()
    for row in csv_rows:
        transaction_code = row[1]
        not_important = row[-1]

        if transaction_code in easy_transactions_dictionary and not_important == 0:
            payer_country = easy_transactions_dictionary["payer_info"]["country_code"]
            shipping_country = easy_transactions_dictionary["shipping_info"]["address"]["country_code"]

            if payer_country != shipping_country: #TODO: what to do in this case -> let human check this
                raise exception(f"Payer info has a different value than shipping info: payer_info: {payer_country} != shipping_info: {shipping_country}")

            start = time.time()
            # use the following to= parameters for the converter
            # 'name_official' -> if short is too short
            # 'name_short' -> if official is too long
            print(cc.convert(["DE", "armenia"], to='name_short'))
            print(cc.valid_class)
            end = time.time()
            print(end-start)

            row.append(payer_country) # TODO: check if this changes the row in the csv_rows (is it the original or a copy that changes)

    # TODO: make a function for this code (second usage in extract transaction codes)
    with open(transactionsCSVFile, 'w', newline='') as csvfile:
        transactionwriter = csv.writer(csvfile, delimiter=',', quotechar='|',
                                       quoting=csv.QUOTE_MINIMAL)
        # rowNr., transactionCode, pageNr., table_width (x1) , y1, x2, y2, y, not_important
        transactionwriter.writerows(csv_rows)

    print(easy_transactions_dictionary)
    print(len(easy_transactions_dictionary))
    print(len(transactions))
    print("9JG1998130909105X" in easy_transactions_dictionary)
    print(easy_transactions_dictionary["9JG1998130909105X"])

def write_countries_on_pdf():
    print("write")

def main():
    while True:
        value = pyip.inputInt("-------------------------------------\n"
                              "What do you want to do?\n"
                              " 1. Extract transaction codes\n"
                              " 2. Get country names from PayPal\n"
                              " 3. Write country names on PDF\n"
                              " 4. All of the above\n"
                              " 5. Exit\n", min=1, max=5)

        match value:
            case 1:
                extract_transaction_codes()
            case 2:
                request_paypal_countries()
            case 3:
                write_countries_on_pdf()
            case 4:
                extract_transaction_codes()
                request_paypal_countries()
                write_countries_on_pdf()
                quit()
            case 5:
                quit()


if __name__ == '__main__':
    main()