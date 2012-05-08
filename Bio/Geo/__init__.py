import re
import os
import urllib
import tempfile
from copy import deepcopy

try:
    import numpy
except ImportError:
    print "Warning: Numpy required for some functions, but was not available."
from Records import Record, Dataset, Series

# -- Code to retrieve GEO records from NCBI  -- #

def _download(url, outfile):
    '''Ensures correct download of gzip files.'''
    handle = urllib.urlopen(url)
    while True:
        packet = handle.read()
        if not packet: break
        outfile.write(packet)
    handle.close()
    return os.path.abspath(outfile.name)


def _get_remote(accn, destdir, amount, verbose):
    if not amount in ('full', 'brief', 'quick', 'data'):
        raise ValueError("Valid options for `amount` are full, brief, quick, ",
            "or data.")
    if not re.match(r'(GDS|GSE|GPL|GSM)\d+', accn):
        raise ValueError("Invalid GEO accession number.")

    geotype = accn[0:3]
    if not destdir:
        destdir = tempfile.mkdtemp()

    if geotype == 'GDS':
        filename = accn+'.soft.gz'
        url = 'ftp://ftp.ncbi.nih.gov/pub/geo/DATA/SOFT/GDS/'+filename
    elif geo_type == 'GSE' and amount == 'full':
        filename = accn+'_family.soft.gz'
        url = '/'.join("ftp://ftp.ncbi.nih.gov/pub/geo/DATA/SOFT/by_series",
                        accn, filename)
    else:
        filename = accn+'.soft'
        url = ('http://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?'
                'targ=self&acc=%s&form=text&view=%s' % (accn, amount))
    outfile = open(os.path.join(destdir,filename), 'wb')
    if verbose: print "Downloading "+filename
    try:
        downloaded = _download(url, outfile)
    except IOError:
        print "error: invalid: ",url
    if verbose: print "File stored at: "+downloaded
    return downloaded   


def get_geo(accn_or_file, destdir=None, amount='full', verbose=True):
    if os.path.isfile(accn_or_file):
        geo = accn_or_file
    else:
        geo = _get_remote(accn_or_file, destdir, amount, verbose)

    if geo.endswith('.gz'):
        import gzip
        return parse(gzip.open(geo))
    else:
        return parse(open(geo))



# -- Code to parse the four GEO record types -- #

def _read_key_value(line):
    words = line[1:].split('=', 1)
    try:
        key, value = words
        value = value.strip()
    except ValueError:
        key = words[0]
        value = ''
    key = key.strip()
    return key, value

def _loop(fn):
    def loop(record, lines):
        for line in lines:
            line = line.strip('\n\r')
            fn(record, line)
        return record
    return loop

@_loop
def _add_attributes(record, line):
    if not re.match(r'![a-z]+_table_(begin|end)', line, re.I):
        key, value = _read_key_value(line)
        key = re.sub(r'^[a-z]+_', '', key) # strip first part (redundant)
        record.meta[key] = value

@_loop
def _add_col_descriptions(record, line):
    key, value = _read_key_value(line)
    record.columns[key] = {'description':value}

@_loop
def _add_table_rows(record, line):
    row = line.split('\t')
    record.table.append(row)

def _filter(source, regex, invert=False):
    if not invert:
        return [x for x in source if re.match(regex, x, re.I)]
    else:
        return [x for x in source if not re.match(regex, x, re.I)]


def _parse(source):
    """Iteratively reads the source (a handle or list of lines) for GEO records,
    returning each record as it is parsed.

    For most purposes, use the public method 'parse()' for expected behavior.
    """
    source = _filter(source, r'[!\^]Database', invert=True)
    record = None
    for line in source:
        if not line: continue
        c = line[0]
        if c == '^':
            if record: yield record
            type, id = _read_key_value(line)
            if type == 'SERIES':
                record  = Series(id)
                meta    = _filter(source, r'!Series')
                rest    = _filter(source, r'[!\^]Series', invert=True)
                _add_attributes(record, lines)
                for record in _parse(rest):
                    if subrecord.type == 'PLATFORM':
                        record.platforms.append(subrecord)
                    elif subrecord.type == 'SAMPLE':
                        record.samples.append(subrecord)
            elif type == 'DATASET':
                record  = Dataset(id)
                columns = _filter(source, r'#')
                table   = _filter(source, r'[^!\^#]')
                meta    = _filter(source, r'!dataset')
                subsets = _filter(source, r'[!\^]subset')

                _add_col_descriptions(record, columns)
                _add_table_rows(record, table)
                _add_attributes(record, meta)

                for subset in _parse(subsets):
                    factor      = subset.meta['type']
                    description = subset.meta['description']
                    samples     = subset.meta['sample_id'].split(',')
                    record.factors[factor][description] = samples
                    for sample in samples:
                        # add subset desc to each sample's column
                        record.columns[sample].update({factor:description})
            else:
                record = Record(type, id)
        elif c == '!':
            _add_attributes(record, [line])
        elif c == '#':
            _add_col_descriptions(record, [line])
        else:
            _add_table_rows(record, [line])
    if record: yield record


def parse(source, verbose=True):
    """Returns a GEO record from the given source file handle or text.

    Arguments:
        source: a SOFT file handle, list of lines of the SOFT file, or raw text
    """
    if isinstance(source, str):
        _source = source.splitlines()
        if len(_source) < 2: 
            raise ValueError("Source must be handle or raw text of SOFT file.")
    if verbose: print "Parsing source..."
    # Implementation notes:
    # User-facing behavior is always to return one record.
    # However, we may be parsing a series-type SOFT file, which
    # may contain many records, and we would like the ability to
    # iteratively parse these to build the final Series object.

    for geo in _parse(source):
        return geo 


# -- Code to analyze data tables in GEO records -- #

def log2xform(dataset):
    matrix = dataset.table_as_matrix()
    return numpy.log2(matrix)

def filter2median(dataset):
    """Returns a copy of the dataset with the data table filtered 
    to remove probes that had no values above the median value of all 
    values in the matrix.
    """
    _ds = deepcopy(dataset)


    
