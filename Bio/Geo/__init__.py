import re

from Records import Record, Series

def parse(source):
    """Returns a record or series object from the source."""

    # Implementation notes:
    # User-facing behavior is always to return one record.
    # However, we may be parsing a series .soft file, which
    # may contain many records, and we would like the ability to
    # iteratively parse these to build the final Series object.
    for geo in _iterparse(source):
        return geo 


def _iterparse(source):
    """Yields the records found in the source."""
    assert not isinstance(source, str)

    # Filter out database information
    source = [x for x in source if not re.match(r'[!\^]Database', x, re.I)]
    record = None
    for line in source:
        line = line.strip('\n\r')
        if not line: continue
        c = line[0]

        if c == '^':
            if record: yield record
            type, id = _read_key_value(line)
            if type == 'SERIES':
                record = Series(id)
                series_meta = [x for x in source if re.match(r'!Series', x)]
                rest = [x for x in source if not re.match(r'[!\^]Series', x, re.I)]
                # Parse the metadata in one loop
                for line in series_meta:
                    key, value = _read_key_value(line)
                    record.meta[key] = value
                # Parse the rest of the records iteratively
                for subrecord in _iterparse(rest):
                    if subrecord.type == 'PLATFORM':
                        record.platforms.append(subrecord)
                    elif subrecord.type == 'SAMPLE':
                        record.samples.append(subrecord)
            else:
                record = Record(type, id)
        elif c == '!':
            if re.match(r'!(Sample|Platform)_table_(begin|end)', line, re.I):
                continue
            key, value = _read_key_value(line)
            record.meta[key] = value
        elif c == '#':
            key, value = _read_key_value(line)
            record.columns[key] = value
        else:
            row = line.split('\t')
            record.table.append(row)


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