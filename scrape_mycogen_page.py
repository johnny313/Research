#!/opt/local/bin/python


################
#This script retreives the thermal heat unit ratings of hybrid maize seeds from the tech spec sheets linked on the seed company website.
#PDF is processed with PDFminer, urls are accessed with urllib2, HTML is processed with BeautifulSoup.
#the retreived values are printed to the terminal, and should be piped into a .txt file: ./scrape_mycogen_page.py > Mycogen_gdu.txt
################

import urllib2
from bs4 import BeautifulSoup
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams
from pdfminer.converter import  TextConverter
import re
from StringIO import StringIO

links = []

base = 'http://www.mycogen.com'


#function to read pdf accessed via url
def parse_pdf(url):
    # Open the url provided as an argument to the function and read the content
    open = urllib2.urlopen(urllib2.Request(base + url)).read()
    memory_file = StringIO(open)
    parser = PDFParser(memory_file)
    document = PDFDocument(parser)
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    laparams = LAParams()
    codec = 'utf-8'
    device = TextConverter(rsrcmgr, retstr, codec = codec, laparams = laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for page in PDFPage.create_pages(document):
        interpreter.process_page(page)
        data =  retstr.getvalue()
    return data

#return number contained in string x as a string
def get_num(x):
    return ''.join(e for e in x if e.isdigit())

#multiple pages with tech sheets, all are in the same format
querys = ['http://www.mycogen.com/Grain_Corn/Product%20Tech%20Sheets/Forms/AllItems.aspx',\
          'http://www.mycogen.com/Grain_Corn/Product%20Tech%20Sheets/Forms/AllItems.aspx?Paged=TRUE&p_SortBehavior=0&p_FileLeafRef=2D355%2epdf&p_ID=142&PageFirstRow=31&&View={D5AEE489-1DF0-4ACF-A28D-82BDE8E24C3B}',\
          'http://www.mycogen.com/Grain_Corn/Product%20Tech%20Sheets/Forms/AllItems.aspx?Paged=TRUE&p_SortBehavior=0&p_FileLeafRef=2J237%2epdf&p_ID=192&PageFirstRow=61&&View={D5AEE489-1DF0-4ACF-A28D-82BDE8E24C3B}',\
          'http://www.mycogen.com/Grain_Corn/Product%20Tech%20Sheets/Forms/AllItems.aspx?Paged=TRUE&p_SortBehavior=0&p_FileLeafRef=2P769%2epdf&p_ID=174&PageFirstRow=91&&View={D5AEE489-1DF0-4ACF-A28D-82BDE8E24C3B}',\
          'http://www.mycogen.com/Grain_Corn/Product%20Tech%20Sheets/Forms/AllItems.aspx?Paged=TRUE&p_SortBehavior=0&p_FileLeafRef=2V676%2epdf&p_ID=166&PageFirstRow=121&&View={D5AEE489-1DF0-4ACF-A28D-82BDE8E24C3B}']

#loop through the links, retrieve the url for each seed PDF
for query in querys:
    resp = urllib2.urlopen(query)
    soup = BeautifulSoup(resp.read())
    breeds =soup.find_all('a', {'onfocus':'OnLink(this)'}) # the search parameter is used to find the html tag for the linked PDF
    for breed in breeds:
        links.append(urllib2.quote(breed['href'])) #get the actual url, quote is used to replace the ' ' with '%20' in the url

resp.close()

#Access and process the PDFs, printing the gdu values for maturity and mid-silking
for link in links:
    dat = parse_pdf(link)
    reg1 = re.compile("\n[0-9]+\sRM") #get relative maturity 
    rm = re.findall(reg1, dat) 
    reg2 = re.compile("GDUs[a-z\s].+[0-9]+") #retreives the gdu values, finding the containing regular expression 
    inst  = re.findall(reg2, dat)
    print "%s, %s, %s" % (get_num(rm[0]), get_num(inst[0]), get_num(inst[1]))
