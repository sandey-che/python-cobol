#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re

class CobolPatterns:
    opt_pattern_format = "({})?"

    row_pattern_base = r'^(?P<level>\d{2})\s+(?P<name>\S+)'
    row_pattern_occurs = r'\s+OCCURS (?P<occurs>\d+) TIMES'
    row_pattern_indexed_by = r"\s+INDEXED BY\s(?P<indexed_by>\S+)"
    row_pattern_redefines = r"\s+REDEFINES\s(?P<redefines>\S+)"
    row_pattern_pic = r'\s+PIC\s+(?P<pic>\S+)'
    row_pattern_comp= r'\s+([A-Z][A-Z0-9\-]*)'
    row_pattern_end = r'\.$'

    row_pattern = re.compile(row_pattern_base + 
                             opt_pattern_format.format(row_pattern_redefines) + 
                             opt_pattern_format.format(row_pattern_occurs) + 
                             opt_pattern_format.format(row_pattern_indexed_by) + 
                             opt_pattern_format.format(row_pattern_pic) + 
                             opt_pattern_format.format(row_pattern_comp) +
                             row_pattern_end)

    pic_pattern_repeats = re.compile(r'(.)\((\d+)\)')
    pic_pattern_float = re.compile(r'S?[9Z]*[.V][9Z]+')
    pic_pattern_integer = re.compile(r'S?[9Z]+')


# Parse the pic string
def parse_pic_string(pic_str):
    # Expand repeating chars
    while True:
        match = CobolPatterns.pic_pattern_repeats.search(pic_str)

        if not match:
            break
        
        expanded_str = match.group(1) * int(match.group(2))
        
        pic_str = CobolPatterns.pic_pattern_repeats.sub(expanded_str, pic_str, 1)

    # Match to types
    if CobolPatterns.pic_pattern_float.match(pic_str):
        data_type = 'Float'
    elif CobolPatterns.pic_pattern_integer.match(pic_str):
        data_type = 'Integer'
    else:
        data_type = 'Char'

    # Handle signed
    if pic_str[0] == "S":
        data_type = "Signed " + data_type
        pic_str = pic_str[1:]

    # Handle precision
    decimal_pos = 0

    if 'V' in pic_str:
        decimal_pos = len(pic_str[pic_str.index('V') + 1 :])
        pic_str = pic_str.replace('V', '')

    return {'type':data_type, 'length':len(pic_str), 'precision':decimal_pos}

# Cleans the COBOL by converting the cobol informaton to single lines
def clean_cobol(lines):
    holder = []

    output = []

    for row in lines:            
        row = row[6:72].rstrip()

        if row == "" or row[0] in ('*','/'):
            continue

        holder.append(row if len(holder) == 0 else row.strip())

        if row[-1] == ".":
            output.append(" ".join(holder))

            holder = []
            

    if len(holder) > 0:
        print("[WARNING] probably invalid COBOL - found unfinished line: ", " ".join(holder))

    return output

"""
Parses the COBOL
 - converts the COBOL line into a dictionarty containing the information
 - parses the pic information into type, length, precision 
 - handles redefines
"""
def parse_cobol(lines):
    output = []

    intify = ["level","occurs"]

    # All in 1 line now, let's parse
    for row in lines:
        match = CobolPatterns.row_pattern.match(row.strip())

        if not match:
            print("Found unmatched row", row.strip())
            continue

        match = match.groupdict()

        for i in intify:
            match[i] = int(match[i] ) if match[i] is not None else None

        if match['pic'] is not None:
            match['pic_info'] = parse_pic_string(match['pic'])

        if match['redefines'] is not None:
            # Find item that is being redefined.
            try:
                redefinedItemIndex, redefinedItem = [(index, item) for index, item in enumerate(output) if item['name'] == match['redefines']][0]

                related_group = get_subgroup( redefinedItem['level'] , output[ redefinedItemIndex+1 : ] )

                output = output[:redefinedItemIndex] + output[ redefinedItemIndex + len(related_group) + 1 : ]

                match['redefines'] = None
            except IndexError:
                print("Could not find the field to be redefined ({}) for row: {}".format(match['redefines'], row.strip()))

        output.append(match)

    return output

# Helper function
# Gets all the lines that have a higher level then the parent_level until
# a line with equal or lower level then parent_level is encountered
def get_subgroup(parent_level, lines):
    output = []

    for row in lines:
        if row["level"] > parent_level:
            output.append(row)
        else:
            return output

    return output

def denormalize_cobol(lines):
    return handle_occurs(lines, 1)

# Helper function
# Will go ahead and denormalize the COBOL
# Beacuse the OCCURS are removed the INDEXED BY will also be removed
def handle_occurs(lines, occurs, level_diff=0, name_postfix=""):
    output = []

    for i in range(1, occurs+1):
        
        skipTill = 0
        new_name_postfix = name_postfix if occurs == 1 else name_postfix + '-' + str(i)

        for index, row in enumerate(lines):
            if index < skipTill:
                continue

            new_row = row.copy()

            new_row['level'] += level_diff

            # Not needed when flattened
            new_row['indexed_by'] = None

            if row['occurs'] is None:
                # First time occurs is just 1, we don't want to add _1 after *every* field
                new_row['name'] = row['name'] + new_name_postfix
                # + "-" + str(i) if occurs > 1 else row['name'] + name_postfix

                output.append(new_row)
            
            else:
                if row["pic"] is not None:
                    # If it has occurs and pic just repeat the same line multiple times
                    new_row['occurs'] = None

                    for j in range(1, row["occurs"]+1):
                        row_to_add = new_row.copy()

                        # First time occurs is just 1, we don't want to add _1 after *every* field
                        row_to_add["name"] = row['name'] + new_name_postfix + '-' + str(j)
                        # + "-" + str(i) + "-" + str(j) if occurs > 1 else row['name'] + name_postfix + "-" + str(j) 

                        output.append(row_to_add)

                else:
                    # Get all the lines that have to occur
                    occur_lines = get_subgroup(row['level'], lines[index+1:])

                    # Calculate the new level difference that has to be applied
                    new_level_diff = level_diff + row['level'] - occur_lines[0]['level']

                    output += handle_occurs(occur_lines, row['occurs'], new_level_diff, new_name_postfix)

                    skipTill = index + len(occur_lines) + 1

    return output

"""
Clean the names.

Options to:
 - strip prefixes on names
 - enforce unique names
 - make database safe names by converting - to _
"""
def clean_names(lines, ensure_unique_names=False, strip_prefix=False, make_database_safe=False):
    names = {}

    for row in lines:
        if strip_prefix:
            row['name'] = row['name'][ row['name'].find('-')+1 : ]

            if row['indexed_by'] is not None:
                row['indexed_by'] = row['indexed_by'][ row['indexed_by'].find('-')+1 : ]

        if ensure_unique_names:
            i = 1
            while (row['name'] if i == 1 else row['name'] + "-" + str(i)) in names:
                i += 1

            names[row['name'] if i == 1 else row['name'] + "-" + str(i)] = 1

            if i > 1:
                row['name'] = row['name'] + "-" + str(i)

        if make_database_safe:
            row['name'] = row['name'].replace("-","_")


    return lines

def process_cobol(lines):
    return clean_names(denormalize_cobol(parse_cobol(clean_cobol(lines))), True, True, True)    

# Prints a Copybook compatible file
def print_cobol(lines):
    output = []

    default_padding = ' ' * 7

    levels = [0]

    for row in lines:
        row_output = []

        if row['level'] > levels[-1]:
            levels.append(row['level'])
        else:
            while row['level'] < levels[-1]:
                levels.pop()

        row_output.append( (len(levels)-1) * '  ' )
        row_output.append( "{0:02d}  ".format(row['level']) )
        row_output.append( row['name'])

        if row['indexed_by'] is not None:
            row_output.append(" INDEXED BY "+row['indexed_by'])

        if row['occurs'] is not None:
            row_output.append( " OCCURS {0:04d} TIMES".format(row['occurs']) )

        if row['pic'] is not None:
            row_output.append( " PIC " + row['pic'] )

        row_output.append(".")

        tot_length = 0
        max_data_length = 66
        outp = default_padding

        for data in row_output:

            if len(outp) + len(data) + 1 > max_data_length:
                # Makes rows 80 chars
                outp += (80-len(outp)) * ' '

                output.append(outp)

                # Start the following line with an extra padding
                outp = default_padding + (len(levels)-1) * '  ' + '    '

            outp += data

        outp += (80-len(outp)) * ' '
        output.append(outp)

    print("\n".join(output))

if __name__ == '__main__':
    import argparse
    import os.path

    parser = argparse.ArgumentParser(description="Parse COBOL Copybooks")
    parser.add_argument("filename", help="The filename of the copybook.")
    parser.add_argument("--skip-all-processing", help="Only processes the redefines.", default=False, action="store_true")
    parser.add_argument("--skip-unique-names", help="Skips making all names unique.", default=False, action="store_true")
    parser.add_argument("--skip-denormalize", help="Skips denormalizing the COBOL.", default=False, action="store_true")
    parser.add_argument("--skip-strip-prefix", help="Skips stripping the prefix from the names.", default=False, action="store_true")

    args = parser.parse_args() 

    if not os.path.isfile(args.filename):
        print("Could not find", args.filename)
        exit()

    with open(args.filename,'r') as f:
        lines = parse_cobol(clean_cobol(f.readlines()))

        if not args.skip_all_processing:
            if not args.skip_denormalize:
                lines = denormalize_cobol(lines)

            if not args.skip_strip_prefix or not args.skip_unique_names:
                lines = clean_names(lines, not args.skip_unique_names, not args.skip_strip_prefix)

        print_cobol(lines)
