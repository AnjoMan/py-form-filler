#! /usr/bin/python3
#! python

import click
from fdfgen import forge_fdf
import csv

import random


import os
import subprocess

# pdftk command to get pdf fields
# pdftk *.pdf dump_data_fields

formIDColumn = "form-writer form id"

def main():
    # import doctest
    # doctest.testmod()



    cli()



@click.group()
def cli():
    """ Autowrite forms

        This script can be used to auto-write PDF forms based on a table of data. It works in 3 steps:

         1) use get_fields to produce a template spreadsheet (in CSV format).

         2) Populate the template spreadsheet with a row for each form you'd like written - this step can be done with a spreadsheet editor, and the results should be saved as a .csv file.

         3) Use write_forms on your completed spreadsheet to write to rows.
        """
    pass


def test_dict_insert_append():
    a = {'a': 1, 'b': [2,3]}

    dict_insert_append(a,'a',4)
    assert a['a'][1] == 4

    dict_insert_append(a,'b',5)
    assert a['b'][2] == 5

    dict_insert_append(a,'c',6)
    assert a['c'] == 6

def dict_insert_append(mdict, key, value):
    """ turn single dict values into lists when another value of the same key is offered

    >>> a = {'a': 1, 'b': [2,3]}
    >>> dict_insert_append(a,'a',4)
    >>> a['a']
    [1, 4]

    >>> dict_insert_append(a,'b',5)
    >>> a['b']
    [2, 3, 5]

    >>> dict_insert_append(a,'c', 6)
    >>> a['c']
    6

    """
    if key in mdict:
        try:
            mdict[key].append(value)
        except AttributeError:
            mdict[key] = [mdict[key], value]
    else:
        mdict[key] = value

    # return mdict

@cli.command()
@click.argument('template', type=click.Path(exists=True))
@click.option("--output", "-o", default="entries.csv", help="Name of .CSV table template file.")
@click.option("--fields_save", "-f", default="fields.txt", help="Name of fields output file for printing out the fields and corresponding parameters.")
@click.option("--sample", "-s", default=False, is_flag=True, help="Create a sample output file, useful for cross-referencing fields on PDF with fields in the output file")
def get_fields(template='template.pdf', output='entries.csv', fields_save=None, sample=False):
    """ Parse a .pdf to identify each field.

        This command parses the pdf specified by TEMPLATE and produces a template spreadsheet to use for autofilling.

    """

    print("form-writer - get fields")
    print("\ttemplate: <{}>".format(template))

    fields = subprocess.check_output('pdftk "{}" dump_data_fields'.format(template), shell=True)
    fields = fields.decode("utf-8").split("---")[1:]

    def row_to_dict(row):
        """how to split field entry into a field name and dict of field elements"""
        field_els = [el.partition(": ") for el in row.split("\r\n") if el]

        new_dict  = dict()
        for el in field_els:
            dict_insert_append(new_dict, el[0], el[2])

        return new_dict

    fields = [row_to_dict(row) for row in fields]

    with open(fields_save, 'w') as mF:
        mF.write("Field Name\tField Description\n");
        mF.writelines("{}\t{}\n".format(el['FieldName'], el) for el in fields)

    print("\n\tFound {} fields".format(len(fields)))
    print("\tA printout of field paramaters was written to <{}>".format(output))



    fields = [{'FieldName':formIDColumn}]+fields

    def sampleValue(field, idx):
        if 'FieldStateOption' in field:
            return random.choice(field['FieldStateOption'])
        else:
            return idx
    sample_row = {field['FieldName']: sampleValue(field,idx) for idx, field in enumerate(fields)}
    sample_row[formIDColumn] = "Sample"

    with open("entries.csv", 'w') as fout:
        writer = csv.DictWriter(fout,lineterminator="\n", fieldnames=[el['FieldName'] for el in fields])
        writer.writeheader()
        writer.writerow(sample_row)

    print("\tTable Template has been written to <'entries.csv'>")

    if sample:
        fileout = form_write(sample_row, template)
        print("\tSample form has been written to <{}>".format(fileout))

        # for el in sample_row:
        #     print(el, sample_row[el])


@cli.command()
@click.argument('table_file', type=click.File('r'))
@click.option("--template", default="template.pdf", help="PDF template which is to be populted")
def write_forms(table_file='entries.csv', template="template.pdf"):
    """ Write a table of form values to .pdf files """
    data_table_reader  = csv.DictReader(table_file, dialect='excel')#click has already opend the file for us

    print("Writing forms for")
    for row in data_table_reader:
        form_write(row, template)
    print("Done!")

def form_write(row, template="template.pdf"):

    DocumentName = template.split(".")[0]
    if not row[formIDColumn]:
        print("\tEmpty row encountered (no value in column <{}>)".format(formIDColumn))
        return None

    fields = [(key, value) for key, value in row.items()]

    fdf = forge_fdf("", fields, [],[],[])
    fdf_file = open("data.fdf", "wb")
    fdf_file.write(fdf)
    fdf_file.close()

    pdf_name = "{} - {}.pdf".format(DocumentName,row[formIDColumn])
    print("\t{}".format(pdf_name))
    os.system('pdftk "{}" fill_form data.fdf output "{}"'.format(template,pdf_name))

    try: #clean up by removing data.fdf
        os.remove("data.fdf")
    except FileNotFoundError:
        Pass

    return pdf_name



if __name__ == "__main__":
    main()
