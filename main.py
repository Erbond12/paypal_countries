import pymupdf
import fitz
import csv


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
    american_comma_string = text.replace(",", ".")
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

# make first line in save the headers i.e. page-nr., transactioncode, ... (non IT person readable)
# (save in csv: Transaction-code, page-nr, x (in case of the table width changing), y1, y_delta (in case the country is too long), y1+y_delta/2 (mid of the row))
# save in csv: Transaction-code, page-nr, x (in case of the table width changing), y0, y1, y2, y3 (y0 = no new line, y1 = 1 new line split in country name, ...)
def extract_transaction_codes():
    with open('transactions.csv', 'w', newline='') as csvfile:
        transactionwriter = csv.writer(csvfile, delimiter=',', quotechar='|',
                                       quoting=csv.QUOTE_MINIMAL)

        doc = fitz.open("MSR-202007 Kopie.PDF") # open a document

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
            rect = (x1, y1, x2, y2)

            # transactionCode, pageNr., table_width (x1) , y1, x2, y2, x1-y2 as rect, y, not_important
            transactionwriter.writerow([text_list[i][4], 3, x1, y1, x2, y2, rect, y, not_important])
        show_modified_page(page)


# make first line in save the headers i.e. page-nr., transactioncode, ... (non IT person readable)
# (save in csv: Transaction-code, page-nr, x (in case of the table width changing), y1, y_delta (in case the country is too long), y1+y_delta/2 (mid of the row))
# save in csv: Transaction-code, page-nr, x (in case of the table width changing), y0, y1, y2, y3 (y0 = no new line, y1 = 1 new line split in country name, ...)
def temp():
    with open('transactions.csv', 'w', newline='') as csvfile:
        transactionwriter = csv.writer(csvfile, delimiter=',', quotechar='|',
                                       quoting=csv.QUOTE_MINIMAL)

        doc = fitz.open("MSR-202007 Kopie.PDF") # open a document

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

if __name__ == '__main__':
    extract_transaction_codes()