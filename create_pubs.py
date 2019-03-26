#!/usr/bin/env python3

from bs4 import SoupStrainer, BeautifulSoup
from urllib.request import urlopen
import numpy as np
from time import sleep

# from jemdoc import main as jemdoc_processor
scholar_base_url = 'https://scholar.google.com'
userToken = 'aBYncN4AAAAJ'
pubs_url = (f'{scholar_base_url}/citations?user='
    f'{userToken}&view_op=list_works&sortby=pubdate')

# header and footer for jemdoc file
header = """# jemdoc: menu{MENU}{publication.html},showsource = Nick Roseveare,addcss{jemdoc.css}
\\n
= Publications
"""

footer = f"""
\\n
\\n
See also [{pubs_url} Google scholar]
"""

# class MyOpener(FancyURLopener):
#     version = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36'
# openurl = MyOpener().open
# openurl(url).read()
# query = ''
# generic_query = f'http://scholar.google.se/scholar?hl=en&q=${query}'


class SEARCH(object):
    entry = "gsc_a_tr"
    author_venue = 'gs_gray'
    titlelink = 'gsc_a_at'
    cites = "gsc_a_ac gs_ibl"
    year = "gsc_a_h gsc_a_hc gs_ibl"
    pdflink = "gsc_vcd_title_ggi"
    pubdetails = "gsc_vcd_value"
    # gs_btnPDF gs_in_ib gs_btn_lsb

    def make_cond(entry_type):
        def cond(x):
            if x:
                return x.startswith(entry_type)
            else:
                return False
        return cond


def get_first_if_avail(data):
    if len(data):
        return data[0]
    else:
        return ''


def get_souped_data(url=pubs_url,
        search_func=SEARCH.make_cond(SEARCH.entry)):
    page = BeautifulSoup(urlopen(url),
        # parse_only=SoupStrainer(
        #     'tr', {'class': search_func}),
        features="html.parser"
    )
    # args = {'markup': urlopen(url),
    #     'features': "html.parser"}
    # if search_func is not None:
    #     args['parse_only'] = SoupStrainer(
    #         'tr', {'class': search_func}),
    # page = BeautifulSoup(**args)
    return page


def get_pub_data(url=pubs_url, debug=0):
    """ use the google scholar pubs url to scrap collection of publications """
    data = get_souped_data(url)
    entry_no = 0
    pub_data = {}
    pub_list = data.find_all('tr', {'class': SEARCH.make_cond(SEARCH.entry)})
    no_pubs = len(pub_list)
    try:
        import tqdm
        iterator = tqdm.tqdm(pub_list, total=no_pubs)
    except ImportError:
        iterator = pub_list
    for pub in iterator:
        if debug:
            print('\n')
            if debug > 1:
                print(pub.contents)
        titlelink = pub.find(
            'a', {'class': SEARCH.make_cond(SEARCH.titlelink)})
        cites = pub.find('a',
            {"class": SEARCH.make_cond(SEARCH.cites)})
        author_venue = pub.find_all(
            'div', {'class': SEARCH.make_cond(SEARCH.author_venue)}
                )
        pub_data[entry_no] = dict(
            author=get_first_if_avail(author_venue[0].contents),
            title=get_first_if_avail(titlelink.contents),
            linkdata=scholar_base_url + titlelink.attrs['data-href'],
            citations=get_first_if_avail(cites.contents),
            citelinks=cites.attrs['href'],
            year=get_first_if_avail(pub.find('span',
                {"class": SEARCH.make_cond(SEARCH.year)}).contents),
            venue=get_first_if_avail(author_venue[1].contents)
        )
        # try to get pdf link:
        sleep(np.random.uniform(1., 3.))
        pub_info_page = get_souped_data(pub_data[entry_no]['linkdata'],
            search_func=None)
        pubdetails = pub_info_page.find_all(
            'div', SEARCH.make_cond(SEARCH.pubdetails))
        if len(pubdetails) >= 2:
            pub_data[entry_no]['pubdate'] = get_first_if_avail(
                pubdetails[1].contents)
            if len(pubdetails) >= 3:
                venue_update = get_first_if_avail(pubdetails[2].contents)
                print(pub_data[entry_no]['venue'])
                print(venue_update)
                try:
                    if (not(pub_data[entry_no]['venue']) or
                        venue_update.strip(' …').startswith(
                            pub_data[entry_no]['venue'])):
                        pub_data[entry_no]['venue'] = ''.join(
                            [el.encode('utf-8', ignore=True) for el in venue_update])
                except UnicodeEncodeError:
                    pass
        pub_pdf_info = pub_info_page.find(
            'div', SEARCH.make_cond(SEARCH.pdflink))
        if pub_pdf_info and len(pub_pdf_info.contents):
            pub_data[entry_no]['pdf_link'] = \
                pub_pdf_info.contents[0].attrs['href']

        if debug:
            print('')
            print(pub_data[entry_no])

        entry_no += 1
    return pub_data


def create_pub_jemdoc():
    pub_data = get_pub_data()
    with open('publication.jemdoc', 'w') as outfile:
        outfile.write(header)
        year = None
        for no, pub in pub_data.items():
            if year is None or year != pub['year']:
                year = pub['year']
                outfile.write('\\n\n== ' + year)
            # write in format
            # - authors
            # title
            # venue, year
            outfile.write(f'\\n\n- {pub["author"]}')
            cites = pub["citations"]
            titlecites = [f'\\n\n [{pub["linkdata"]} {pub["title"]}]']
            if 'pdf_link' in pub:
                titlecites.append(f'[{pub["pdf_link"]} PDF]')
            if len(cites):
                titlecites.append(
                    f'Cited by: [{pub["citelinks"]} {pub["citations"]}]')
            outfile.write(', '.join(titlecites))
            venue_year = []
            if pub["venue"]:
                venue_year.append(pub['venue'])
            if pub['year']:
                venue_year.append(pub["year"])
            venue_year = ', '.join(venue_year)
            if len(venue_year):
                outfile.write('\\n\n' + venue_year)
        outfile.write(footer)
    # run the jemdoc md-to-html-processor
    # jemdoc_processor(['jemdoc.py', 'publication'])


if __name__ == '__main__':
    create_pub_jemdoc()
