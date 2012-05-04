import re

def truncate(string, trunc=20):
    length = len(string)
    if length <= trunc: return string
    if trunc < 8: return '[...]'
    half = (trunc//2)-3

    p1 = ''.join([x for x in string[:half]])
    p2 = ''.join([x for x in string[length-half:]])
    return '[...]'.join((p1, p2))

def pad(string, pad_to=20, justify='left'):
    length = len(string)
    if length >= pad_to: return string
    spacing = pad_to-length
    if justify == 'right':
        spaces = ''.join([' ' for x in xrange(spacing)])
        return spaces+string
    if justify == 'center':
        spaces_half = ''.join([' ' for x in xrange(spacing/2)])
        if spacing%2 == 0: 
            return string.join((spaces_half, spaces_half))
        else:
            return string.join((spaces_half, spaces_half+' '))
    if justify == 'left':
        spaces = ''.join([' ' for x in xrange(spacing)])
        return string+spaces

class SoftFile(object):
    """Base class for SOFT-format file representations (GDS, GSE, GSM, and GPL).

    SOFT file format structure:
    - Line starts indicate line types:
        '^': entity indicator line (PLATFORM, SAMPLE, SERIES, DATASET)
        '!': entity attribute line
        '#': data table header description line
        n/a: data table row

    - Line format:
        [line-type char] [label] = [value]
    """
    def __init__(self, type, id):
        self.id = id
        self.type = type
        self.meta = {}

    def __repr__(self):
        return self.id

    def print_metadata(self):
        """Prints the metadata associated with this data."""
        print("*** %s: %s ***" % (self.type, self.id))
        for entry in self.meta:
            print("%s:\t%s" % (entry, self.meta[entry]))


class Record(SoftFile):
    """Represents the three basic GEO record types: datasets (GDS), samples (GSM), and platforms (GPL).
    GEO Series are special records that contain samples and platforms and are defined in the Series object.

    Attributes:
        id:      entity id (GEO accession)
        type:    entity type
        meta:    metadata information for the record {key:value}
        table:   list of rows, split by tabs. First row is the header. 
                 [header, row1, row2, ...]
        columns: column names, descriptions, and (if dataset), factor subtypes. 
                 {colname: {description:'', factor1:'', factor2:'', ...}}
    """
        
    def __init__(self, type, id):
        super(Record, self).__init__(type, id)
        self.table = []
        self.columns = {}


    def print_table(self, length=20, max_width=80, col_width=20):
        """Prints a nicely-formatted overview of the data table.

        Arguments: (set any to < 0 to disable)
        length      number of rows to print (omits middle) [default=20]
        max_width:  maximum width of the table (omits end columns if needed) [default=80]
        col_width:  width of each column (trims middle if needed) [default=20]
        """
        num_rows = len(self.table)
        printed_ellipses = False
        for c, row in enumerate(self.table):
            # if we're within the first or last part of the table (or displaying all rows)
            if (length < 0) or (c < length//2) or (c > num_rows-length//2):
                line = ''   
                i = 0
                fill = lambda x: pad(truncate(x, trunc=col_width), pad_to=col_width)
                # set the column width if width is not -1
                entry = fill(row[i]) if col_width > 0 else row[i]
                # build the row, minding the max_width (if not -1)
                while (i < len(row)) and ((max_width < 0) or (i < len(row) and len(line)+len(entry) < max_width)):
                    entry = fill(row[i]) if col_width > 0 else row[i]
                    line = "%s\t%s" % (line, entry)
                    i += 1
                if i < len(row)-1:
                    line += "\t [...]"
                print line
            elif not printed_ellipses:
                print("\t[...]")
                printed_ellipses = True

class Series(SoftFile):
    """Represents a GEO Series (GSE) record.

    Attributes:
        id:      entity id (GEO accession)
        type:    entity type 
        meta:    metadata information for the record {key:value}
        platforms:  list of platform records associated with series
                    [GPL0, GPL1, ...]
        samples: list of sample records associated with the series
                 [GSM0, GSM1, ...]
    """

    def __init__(self, id):
        super(Series, self).__init__("SERIES", id)
        self.platforms = []
        self.samples = []




    