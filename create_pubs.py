#!/usr/bin/env python3
from bs4 import BeautifulSoup, SoupStrainer
from urllib.request import urlopen
import requests
import warnings
import numpy as np
from time import sleep
from torrequest import TorRequest
from functools import wraps
import pickle
import stem
import os
import sys
import hashlib

# from jemdoc import main as jemdoc_processor
global DEBUG, PERFORM_API_QUERY
DEBUG = 0
PERFORM_API_QUERY = True
# ========================================================================
# Basic setup and configuration
# ========================================================================
scholar_base_url = 'https://scholar.google.com'
defaultUserToken = 'aBYncN4AAAAJ'
cache_dir = './cache_results/'
use_torrequest = False
tor_pw = None

req_headers = {'Cookie': """SIDCC=AN0-TYuj0q-4XRiXQ3gJMz0m3tlfWP7QSEH3wVYQlp_ilFIMpNsb9QuMYvgCPd-jZ1Wxi0GNmhc-; NID=180=yyWFo_ahytXboAQC5yQZtNAuiEO4gqC24ZuBpZohz3pAommWZJfkTvBN88PMtw7W-NCrgNkrTWiYz60sex47SYBzLc9quod8SE3qJNT0brAZO-rS6Obo-xKNozk9ru5gbnpHk6JAz2hBSvE2dZ5pvsNNH07LTOzNlvKVwAUqB_DunGUsFGiVU4llMIdTot7E_w54QhCB1SK2B61mnNOTpsd1vKKl55_08QVLATkzmiTWMAS3iMSbFfEIh15au_d6oph3ty5jzwb9N9IsAY74SuROjXSEAAO4uucw_4DzAbOVrYkZuXV5danfJ-3NlXRHXTLxaQV0h8l4397Po16rNS2fFOgLGb98e8is24rHDHYdVgX8e_hRFblgl_vhUlcFjX9qaFYhDUSo5TBayZzXZ5Kx10Z_nXsg_Q-dU8OYGL5iF4x2; ANID=AHWqTUlo-5w2MofmeFT-rWs1HL7b3GPMp25mAiCc0y4fjfdp1RfBaUXbueRQslOc; APISID=ie-xK6XHggw2c8MI/AM6-7GdnzbbCMiumm; HSID=AIubFez_pc8L7TxNM; SAPISID=6ipzySGnJYFpDf6t/AK-d6VdxEfTRbjHbq; SID=DwdoFrkf3ur8nomaNkXVgSyDgVgk3oCCjH7X5twmfTOq8s8k6yqehrv3fErhhMqx0Z0r3w.; SSID=Ay-xrtBerlXX0LgH-; GSP=LM=1541629109:S=qOkGE7yk0SrAQOMa; 1P_JAR=2019-3-28-18""",
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'br, gzip, deflate',
    'Host': 'scholar.google.com',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.3 Safari/605.1.15',
    'Accept-Language': 'en-us', 'DNT': '1'}
default_pub_url = (f'{scholar_base_url}/citations?user='
    f'{defaultUserToken}&view_op=list_works&sortby=pubdate')
missing_year_override = {
    'Tracking and Phase Identification of Targets in Nonlinear Motion': 2008}


def get_aux_data(userToken=defaultUserToken):
    purl = (f'{scholar_base_url}/citations?user='
        f'{userToken}&view_op=list_works&sortby=pubdate')
# header and footer for jemdoc file
    hdr = """# jemdoc: menu{MENU}{publication.html},showsource = Nick Roseveare,addcss{jemdoc.css}
\\n
= Publications
"""
    ftr = f"""
\\n
\\n

See also [{purl} Google scholar]
"""
    return purl, hdr, ftr


class SEARCH(object):
    entry = "gsc_a_tr"
    author_venue = 'gs_gray'
    titlelink = 'gsc_a_at'
    cites = "gsc_a_ac gs_ibl"
    year = "gsc_a_h gsc_a_hc gs_ibl"
    pdflink = "gsc_vcd_title_ggi"
    pubdetails = "gsc_vcd_value"
    inside_abstract = 'gsh_small'
    # gs_btnPDF gs_in_ib gs_btn_lsb

    def make_cond(entry_type):
        def cond(x):
            if x:
                return x.startswith(entry_type)
            else:
                return False
        return cond


def sleep_between(wait=1):
    if wait == 0:
        return 0
    else:
        return float(np.random.uniform(2., 3.))


# ========================================================================
# Tor obfuscated API access functions
# ========================================================================
def tor_newip_get(url, pw=tor_pw, debug=0):
    debug = max(debug, DEBUG)
    response = None
    try:
        try:
            if use_torrequest:
                with TorRequest(password=pw) as tr:
                    tr.reset_identity()
                    if debug:
                        check = tr.get('http://www.icanhazip.com/')  # , headers=req_headers)
                        print('outside ip looks like', check.text)
                    response = tr.get(url)
            else:
                renew_connection()
                with get_tor_session() as session:
                    if debug:
                        check = session.get('http://www.icanhazip.com/')  # , headers=req_headers)
                        print('outside ip looks like', check.text)
                    response = session.get(url)
        except (stem.SocketError, stem.connection.AuthenticationFailure):
            warnings.warn('TOR SERVICE: unable to connect to tor service')
        except stem.connection.IncorrectPassword:
            warnings.warn('TOR SERVICE: tor control password incorrect')
    except OSError as ose:
        if 'tor' in str(ose):
            warnings.warn(str(ose))
        else:
            raise(ose)
    if debug:
        print(response, type(response))
        if debug > 2:
            print('')
            print(response.__dict__)
    if response:
        if response.status_code == 200:
            return response._content
        else:
            response = None
            warnings.warn(response.reason)

    return response


def get_tor_session():
    session = requests.session()
    # Tor uses the 9050 port as the default socks port
    session.proxies = {'http': 'socks5://127.0.0.1:9050',
                       'https': 'socks5://127.0.0.1:9050'}
    return session


def renew_connection():
    with stem.control.Controller.from_port(port=9051) as controller:
        controller.authenticate(password=tor_pw)
        controller.signal(stem.Signal.NEWNYM)
        sleep(2)


def get_first_if_avail(data):
    if len(data):
        return data[0]
    else:
        return ''


# ========================================================================
# Cache wrapper functions
# ========================================================================
def clear_cache():
    """ clear out the local page cache """
    if not(os.path.isdir(cache_dir)):
        return True
    try:
        for f in os.listdir(cache_dir):
            os.remove(cache_dir + f)
        return True
    except:
        return False


def local_remote_wrapper(func, cache_ext='bin', overwrite_cache=False):
    """ get cache data for the url if available, and call function
        to get page data if not available in the cache

        Usage:
            local_cache(func, cache_ext='.bin', overwrite_cache=False)

        add 'local_cache' to the kwargs if not already specified
        automatically loads and saves the data generated as appropriate
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        global DEBUG
        if 'debug' in kwargs:
            DEBUG = kwargs['debug']
        assert ('url' in kwargs) or len(args), "url must be specified"
        url = (kwargs['url'] if 'url' in kwargs else args[0])
        hashseq = hashlib.md5(url.encode()).hexdigest()
        cache_url = cache_dir + '.'.join([func.__name__, hashseq, cache_ext])
        if 'local_cache' not in kwargs:
            if DEBUG > 3:
                print(f'searching for cache file for {url}')
                print(f'   hash is {hashseq} ')
                print(f'   with file location (assumed to be) {cache_url}')
            if os.path.isfile(cache_url):
                try:
                    with open(cache_url, 'rb') as binfile:
                        # kwargs['local_cache'] = pickle.loads(binfile.read())
                        kwargs['local_cache'] = binfile.read()
                    if DEBUG:
                        print(f'   FOUND local cache: {cache_url} for url: {url}')
                except EOFError:
                    # in the case of a bad or empty file, don't get hung up
                    pass
        if 'local_cache' not in kwargs:
            wait = sleep_between()
            if DEBUG > 1:
                print('...sleeping for {wait:.3f} seconds')
            # sleep a bit to prevent scraping from getting banned for these urls
            sleep(wait)
        # call the function to retrieve and beautify html data
        beautified, raw = func(*args, **kwargs)
        if 'local_cache' not in kwargs and not(os.path.isdir(cache_dir)):
            os.mkdir(cache_dir)
        if raw is not None and (
                overwrite_cache or not(os.path.isfile(cache_url))):
            with open(cache_url, 'wb') as bfile:
                # bfile.write(pickle.dumps(data))
                bfile.write(raw)
            if DEBUG:
                print(f'   CREATED local cache: {cache_url} for url: {url}')
        return beautified, raw
    return wrapper


# ========================================================================
# Primary functions
# ========================================================================

@local_remote_wrapper
def get_souped_data(url,
        parse_only=None,  # ('tr', {'class': search_func})
        torpw=tor_pw,
        local_cache=None,
        search_func=SEARCH.make_cond(SEARCH.entry)):
    get_data = None
    if local_cache is not None:
        get_data = local_cache
    elif PERFORM_API_QUERY:
        if tor_pw:
            get_data = tor_newip_get(url)
        if get_data is None:
            if tor_pw:
                print('tor-get unsuccessful, attempting standard get')
            response = urlopen(url)
            if response.code == 200:
                get_data = response.read()
    if get_data is None and not(PERFORM_API_QUERY):
        warnings.warn('cached data not found, refusing to query API')
    page = None
    if get_data:
        if parse_only:
            page = BeautifulSoup(get_data,
                features="html.parser",
                parse_only=SoupStrainer(*parse_only)
            )
        else:
            page = BeautifulSoup(get_data,
                # parse_only=SoupStrainer(
                #     'tr', {'class': search_func}),
                features="html.parser"
            )
    return page, get_data


@local_remote_wrapper
def get_pub_data(url, overwrite_pub_data=False, local_cache=None, debug=0):
    """ use the google scholar pubs url to scrap collection of publications """
    if local_cache is not None:
        # promote the raw data to the formatted data for this function
        pub_data = pickle.loads(local_cache)
        return pub_data, local_cache
    data, raw = get_souped_data(url)
    entry_no = 0
    pub_data = {}
    if data is None:
        print('no data parsed, returning early')
        return None, None
    pub_list = data.find_all('tr', {'class': SEARCH.make_cond(SEARCH.entry)})
    no_pubs = len(pub_list)
    try:
        import tqdm
        iterator = tqdm.tqdm(pub_list, total=no_pubs)
    except ImportError:
        iterator = pub_list
    for pub in iterator:
        if debug > 1:
            print('\n')
            if debug > 2:
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
        # int the year appropriately
        if (len(pub_data[entry_no]['year']) == 0 and
                pub_data[entry_no]['title'] in missing_year_override):
            pub_data[entry_no]['year'] = missing_year_override[
                pub_data[entry_no]['title']]
        else:
            try:
                pub_data[entry_no]['year'] = int(pub_data[entry_no]['year'])
            except:
                print('did not find year in pub data or missing look-up table')
        # try to get pdf link:
        # try:
        pub_info_page, raw = get_souped_data(pub_data[entry_no]['linkdata'],
            search_func=None)
        if pub_info_page is not None:
            # except
            pubdetails = pub_info_page.find_all(
                'div', SEARCH.make_cond(SEARCH.pubdetails))
            idx2search = 1
            if len(pubdetails) >= 2:
                if (pubdetails[idx2search].find('div',
                        SEARCH.make_cond(SEARCH.inside_abstract)) is None):
                    pub_data[entry_no]['pubdate'] = get_first_if_avail(
                        pubdetails[idx2search].contents)
                    idx2search += 1
                if len(pubdetails) >= 3:
                    venue_update = get_first_if_avail(pubdetails[idx2search].contents)
                    # print(pub_data[entry_no]['venue'])
                    # print(venue_update)
                    try:
                        if (pubdetails[idx2search].find('div',
                                SEARCH.make_cond(SEARCH.inside_abstract)) is None) and (
                            not(pub_data[entry_no]['venue']) or
                            (' '.join(venue_update.split(' ')[:-1])
                                ).startswith(pub_data[entry_no]['venue'])):
                            pub_data[entry_no]['venue'] = str(venue_update)
                            # print(type(venue_update))
                            # ''.join(
                            # [el.encode('utf-8', ignore=True) for el in venue_update.decode()])
                    except UnicodeEncodeError:
                        pass
            pub_pdf_info = pub_info_page.find(
                'div', SEARCH.make_cond(SEARCH.pdflink))
            if pub_pdf_info and len(pub_pdf_info.contents):
                pub_data[entry_no]['pdf_link'] = \
                    pub_pdf_info.contents[0].attrs['href']
        elif debug:
            print(f'skipping details update for {pub_data[entry_no]["title"]}')

        if debug > 1:
            print('')
            print(pub_data[entry_no])

        entry_no += 1

    try:
        raw = pickle.dumps(pub_data)
    except RecursionError as re:
        if debug:
            print(repr(re), repr(re.__traceback__))
        raw = None
    return pub_data, raw


def create_pub_jemdoc(fileout, userToken=defaultUserToken,
        debug=0, overwrite_pub_data=True):
    pubs_url, header, footer = get_aux_data(userToken)
    pub_data, raw = get_pub_data(url=pubs_url, debug=debug)

    if pub_data is not None:
        with open(fileout, 'w') as outfile:
            outfile.write(header)
            year = None

            # ensure sorted by pub data
            pub_data = {i: item
                for i, item in enumerate(sorted(list(pub_data.values()),
                    key=lambda x: (int(x['year'])
                        if 'year' in x else 2006),
                    reverse=True))}

            for no, pub in pub_data.items():
                if year is None or year != pub['year']:
                    year = pub['year']
                    outfile.write('\\n\n== ' + str(year))
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
                        f'Cited: [{pub["citelinks"]} {pub["citations"]}]')
                outfile.write(', '.join(titlecites))
                venue_year = []
                if pub["venue"]:
                    venue_year.append(pub['venue'])
                if pub['year']:
                    venue_year.append(str(pub["year"]))
                venue_year = ', '.join(venue_year)
                if len(venue_year):
                    outfile.write('\\n\n' + venue_year)
            outfile.write(footer)
        print(f'wrote publication data to: {fileout}')
    else:
        print('no publication data retrieved')
    # run the jemdoc md-to-html-processor
    # jemdoc_processor(['jemdoc.py', 'publication'])


if __name__ == '__main__':
    helptextshort = 'USAGE: ./create_pub_jemdoc.py [-c, -f <file>, -t <token>, -h]'
    helptext = """
Script to query google scholar and scrap author publication data,
creates a publication jemdoc file for posting to a website
    usage: ./create_pub_jemdoc.py
    Options:
    --clear/-c                   | clear the cache, will exit after clearing
    --help/-h                    | print this help
    --file/-f <outfile>          | default is publication.jemdoc
    --debug/-d <debug level>     | default is 0
    --cache/-o                   | use the cache only, no API queries
    --token/-t <GS user token>   | set the GS user token"""

    fileout = 'publication.jemdoc'
    token = defaultUserToken
    args = sys.argv
    printhelp = False
    if len(args) > 1:
        args = args[1:]  # remove the calling filename
        while len(args):
            arg, next_arg = args[0], (args[1] if len(args) > 1 else None)
            if arg in ['--clear', '-c']:
                status = clear_cache()
                sys.exit(int(not(status)))
            elif arg in ['--cache', '-o']:
                PERFORM_API_QUERY = False
                args = args[1:]
            elif arg in ['--file', '-f']:
                if next_arg is None:
                    printhelp = True
                    break
                fileout = next_arg
                args = args[2:]
            elif arg in ['--token', '-t']:
                if next_arg is None:
                    printhelp = True
                    break
                token = next_arg
                args = args[2:]
            elif arg in ['--debug', '-d']:
                if next_arg is None:
                    printhelp = True
                    break
                DEBUG = int(next_arg)
                args = args[2:]
            else:
                longhelp = (arg in ['--help'])
                printhelp = True
                break
    if printhelp:
        if longhelp:
            print(helptext)
        else:
            print(helptextshort)
        sys.exit(1)

    create_pub_jemdoc(fileout, token, debug=DEBUG)
