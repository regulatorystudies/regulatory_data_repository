#----------------------------------------------------------------------------------------------------------------------#
#-----------------------------------------PDF Word/Character Counter & Readability-------------------------------------#
# Reference: https://www.kaggle.com/code/yhirakawa/textstat-how-to-evaluate-readability

#%% Import libraries
import numpy as np
import pandas as pd
import os
import glob
from pathlib import Path
import fitz     #need: pip install PyMuPDF
import docx
import string
import math
from PIL import Image
import pytesseract
import sys
from pdf2image import convert_from_path
import spacy
import textstat
import sys
import comtypes.client

#----------------------------------------------------------------------------------------------------------------------#
#%% Define a function to convert scanned (machine unreadable) PDF to text
def convertScanPDF(file):
    ## Part 1 : Converting PDF to images
    # Store all the pages of the PDF in a variable
    # Need to specify paths for tesseract and poppler if error occurs
    # Ref1: https://stackoverflow.com/questions/50951955/pytesseract-tesseractnotfound-error-tesseract-is-not-installed-or-its-not-i
    # Ref2: https://stackoverflow.com/questions/53481088/poppler-in-path-for-pdf2image
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    pages = convert_from_path(file, 500, poppler_path=r'C:\Users\xiezd\Downloads\poppler-0.68.0_x86\poppler-0.68.0\bin')
    # Counter to store images of each page of PDF to image
    image_counter = 1
    # Iterate through all the pages stored above
    for page in pages:
        # Declaring filename for each page of PDF as JPG
        # For each page, filename will be:
        # PDF page 1 -> page_1.jpg
        # ....
        # PDF page n -> page_n.jpg
        filename = "page_" + str(image_counter) + ".jpg"
        # Save the image of the page in system
        page.save(filename, 'JPEG')
        # Increment the counter to update filename
        image_counter = image_counter + 1

    ##Part 2 - Recognizing text from the images using OCR
    # Variable to get count of total number of pages
    filelimit = image_counter - 1
    text=''
    # Iterate from 1 to total number of pages
    for i in range(1, filelimit + 1):
        # Set filename to recognize text from
        # Again, these files will be:
        # page_1.jpg
        # page_2.jpg
        # ....
        # page_n.jpg
        filename = "page_" + str(i) + ".jpg"
        # Recognize the text as string in image using pytesserct
        new_text = str(((pytesseract.image_to_string(Image.open(filename)))))
        # The recognized text is stored in variable text.
        # Any string processing may be applied on text
        # Here, basic formatting has been done: In many PDFs, at line ending, if a word can't be written fully,
        # a 'hyphen' is added. The rest of the word is written in the next line. Eg: This is a sample text this
        # word here GeeksF-orGeeks is half on first line, remaining on next. To remove this, we replace every '-\n' to ''.
        new_text = new_text.replace('-\n', '')
        # Finally, write the processed text to the file.
        text += new_text
        # Delete the image from system
        os.remove(filename)
    return text

#%% Define a function to convert doc file to pdf
def convert_doc_to_pdf(directory,filename):
    wdFormatPDF = 17

    in_file = os.path.join(directory, filename)
    out_file = os.path.join(directory, filename.split('.')[0]+'.pdf')

    word = comtypes.client.CreateObject('Word.Application')
    doc = word.Documents.Open(in_file)
    doc.SaveAs(out_file, FileFormat=wdFormatPDF)
    doc.Close()
    word.Quit()
    print(filename,"has been converted to PDF.")

#%% Define a function to get word/character count & readability
def get_count_readability(directory,filename):
    file = os.path.join(directory, filename)
    doc = fitz.open(file)
    # the pages
    num_pages = doc.page_count
    count = 0
    text = ""
    error = "ERROR: failed to extract text or no text existing"
    # The while loop will read each page
    while count < num_pages:
        page = doc[count]
        count += 1
        text += page.get_text('text')
    if text == "":
        if os.path.getsize(file)<10000000:  # set a size limit (bytes)
            try:
                print('reading images in',filename)
                text = convertScanPDF(file)
            except:
                print(filename,': failed to extract text or no text existing')
        else:
            print(filename,': file is too large')
            error='ERROR: file is too large'

    if text!="":
        # Get readability scores
        text = text.lower().replace('-\n', '').replace('\n', ' ').replace('\r', ' ')
        flesch = textstat.flesch_reading_ease(text)
        gunning = textstat.gunning_fog(text)
        smog = textstat.smog_index(text)
        dale = textstat.dale_chall_readability_score(text)

        # Get word/character count
        text = text.translate(str.maketrans('', '', string.punctuation))
        words = text.split()
        word_count = len(words)
        text = text.replace(' ', '')
        characters = len(text)
    else:
        characters=error
        word_count=None
        flesch=None
        gunning=None
        smog=None
        dale=None

    doc.close

    return (filename,num_pages,characters,word_count,flesch,gunning,smog,dale)

#----------------------------------------------------------------------------------------------------------------------#
#%% Convert all doc files to PDF
directory = "your_file_directory"  #set directory
for filename in os.listdir(directory):
    if filename.endswith('doc'):
        out_file = os.path.join(directory, filename.split('.')[0] + '.pdf')
        if os.path.exists(out_file)==False:
            convert_doc_to_pdf(directory,filename)
print('END')

#%% Get counts and readability for all PDF files
results=[]
for filename in os.listdir(directory):
    if filename.endswith('pdf'):
        results.append(get_count_readability(directory,filename))
print("END")

#%% Save results
df_results = pd.DataFrame(results,columns=["Document ID", "Page Count", "Number of Characters",'Number of Words',
                                              "Flesch", "Gunning Fog",'Smog', 'Dale Chall'])
print(df_results.info())
df_results.to_csv('word counts and readability.csv',index=False)

