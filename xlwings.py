"""
xlwings is the easiest way to deploy your Python powered Excel tools on Windows.
Homepage and documentation: http://xlwings.org/

Copyright (c) 2014, Zoomer Analytics.
License: MIT (see LICENSE.txt for details)

"""

import sys
from win32com.client import GetObject
import win32com.client.dynamic
from win32com.client import constants
import adodbapi
from pywintypes import TimeType
import numpy as np
from pandas import MultiIndex
import pandas as pd
import numbers
from datetime import date, datetime


__version__ = '0.1.0-dev'

_is_python3 = sys.version_info.major > 2

App = win32com.client.dynamic.Dispatch('Excel.Application')


def xlwings_connect(fullname=None):
    """
    Establishes a connection between an Excel file and Python. Returns the Workbook as COM object.


    Parameters
    ----------
    fullname : string, default None
        For debugging/interactive use from within Python, provide the fully qualified name, e.g: 'C:\path\to\file.xlsx'
        No arguments must be provided if called from Excel through the xlwings VBA module.
    """
    # TODO: pass 'from_excel' arg when called from VBA to catch error when called without fullname from within Python
    if fullname:
        fullname = fullname.lower()
    else:
        fullname = sys.argv[1].lower()

    global Workbook
    Workbook = GetObject(fullname)  # GetObject() returns the correct Excel instance if there are > 1
    return Workbook


def clean_com_data(data):
    """
    Transforms data from tuples of tuples into list of list and
    on Python 2, transforms PyTime Objects from COM into datetime objects.

    Parameters
    ----------
    data : raw data as returned from Excel (tuple of tuple)

    """
    # Turn into list of list for easier handling (e.g. for Pandas DataFrame)
    data = [list(row) for row in data]

    # Check which columns contain COM dates
    # TODO: replace with datetime transformations from pyvot -> python3?
    # TODO: simplify like this: [[tc.DateObjectFromCOMDate(c) for c in row] for row in data]
    # TODO: use isinstance instead of type
    if _is_python3:
        return data
    else:
        tc = adodbapi.pythonDateTimeConverter()
        for i in range(len(data[0])):
            if any([type(row[i]) is TimeType for row in data]):
                # Transform PyTime into datetime
                for j, cell in enumerate([row[i] for row in data]):
                    if type(cell) is TimeType:
                        data[j][i] = tc.DateObjectFromCOMDate(cell)
    return data


class Range(object):
    """
    A Range object can be created with the following arguments:

    Range('A1')          Range('Sheet1', 'A1')          Range(1, 'A1')
    Range('A1:C3')       Range('Sheet1', 'A1:C3')       Range(1, 'A1:C3')
    Range((1,2))         Range('Sheet1, (1,2))          Range(1, (1,2))
    Range((1,1), (3,3))  Range('Sheet1', (1,1), (3,3))  Range(1, (1,1), (3,3))
    Range('NamedRange')  Range('Sheet1', 'NamedRange')  Range(1, 'NamedRange')

    If no worksheet name is provided as first argument, it will take the range from the active sheet. To get
    the range from a specific sheet, provide the worksheet name as first argument either as name or index.

    You usually want to go for Range(...).value to get the values as list of lists.
    Specify Range(..., asarray=True).value if you want to get back a NumPy array.
    """
    def __init__(self, *args, **kwargs):
        # Arguments
        if len(args) == 1 and isinstance(args[0], (str, unicode)):
            sheet = None
            cell_range = args[0]
        elif len(args) == 1 and isinstance(args[0], tuple):
            sheet = None
            cell_range = None
            self.row1 = args[0][0]
            self.col1 = args[0][1]
            self.row2 = self.row1
            self.col2 = self.col1
        elif (len(args) == 2
              and isinstance(args[0], (numbers.Number, str, unicode))
              and isinstance(args[1], (str, unicode))):
            sheet = args[0]
            cell_range = args[1]
        elif (len(args) == 2
              and isinstance(args[0], (numbers.Number, str, unicode))
              and isinstance(args[1], tuple)):
            sheet = args[0]
            cell_range = None
            self.row1 = args[1][0]
            self.col1 = args[1][1]
            self.row2 = self.row1
            self.col2 = self.col1
        elif len(args) == 2 and isinstance(args[0], tuple):
            sheet = None
            cell_range = None
            self.row1 = args[0][0]
            self.col1 = args[0][1]
            self.row2 = args[1][0]
            self.col2 = args[1][1]
        elif len(args) == 3:
            sheet = args[0]
            cell_range = None
            self.row1 = args[1][0]
            self.col1 = args[1][1]
            self.row2 = args[2][0]
            self.col2 = args[2][1]

        # Keyword Arguments
        self.kwargs = kwargs
        self.index = kwargs.get('index', True)  # Set DataFrame with index
        self.header = kwargs.get('header', True)  # Set DataFrame with header
        self.asarray = kwargs.get('asarray', False)  # Return Data as NumPy Array
        self.strict = kwargs.get('strict', False)  # stop table/horizontal/vertical at empty formulas, e.g. =""

        # Get sheet
        if sheet:
            self.sheet = Workbook.Worksheets(sheet)
        else:
            self.sheet = Workbook.ActiveSheet

        # Get row1, col1, row2, col2 out of Range object
        if cell_range:
            self.row1 = self.sheet.Range(cell_range).Row
            self.col1 = self.sheet.Range(cell_range).Column
            self.row2 = self.row1 + self.sheet.Range(cell_range).Rows.Count - 1
            self.col2 = self.col1 + self.sheet.Range(cell_range).Columns.Count - 1

        self.cell_range = self.sheet.Range(self.sheet.Cells(self.row1, self.col1),
                                           self.sheet.Cells(self.row2, self.col2))

    @property
    def value(self):
            if self.row1 == self.row2 and self.col1 == self.col2:
                data = clean_com_data([[self.cell_range.Value]])[0][0]  # TODO: introduce as_matrix method?
            else:
                data = clean_com_data(self.cell_range.Value)

            if self.asarray:
                # replace None (empty cells) with nan as None produces arrays with dtype=object
                if data is None:
                    data = np.nan
                elif not isinstance(data, (numbers.Number, str, unicode)):
                    data = [[np.nan if x is None else x for x in i] for i in data]
                return np.array(data)
            return data

    @value.setter
    def value(self, data):
        if isinstance(data, pd.DataFrame):
            if self.index:
                data = data.reset_index()

            if self.header:
                if isinstance(data.columns, MultiIndex):
                    columns = np.array(zip(*data.columns.tolist()))
                else:
                    columns = np.array([data.columns.tolist()])
                data = np.vstack((columns, data.values))
            else:
                data = data.values

        if isinstance(data, np.ndarray):
            try:
                # nan have to be transformed to None, otherwise Excel shows them as 65535
                data = np.where(np.isnan(data), None, data)
            except TypeError:
                # isnan doesn't work on arrays of dtype=object
                data[pd.isnull(data)] = None
            # Python 3 can't handle arrays directly
            data = data.tolist()

        if isinstance(data, (numbers.Number, str, unicode, date, datetime)):
            row2 = self.row2
            col2 = self.col2
        else:
            row2 = self.row1 + len(data) - 1
            col2 = self.col1 + len(data[0]) - 1

        self.sheet.Range(self.sheet.Cells(self.row1, self.col1), self.sheet.Cells(row2, col2)).Value = data

    @property
    def table(self):
        """
        Returns a contiguous Range starting with the indicated cell as top-left corner and going down and right as long
        as no empty cell is hit. For example, to get the values of a contiguous range or clear its contents use:

            Range('A1').table.value
            Range('A1').table.clear_contents()

        Parameters
        ----------
        strict : bool, default False
            strict stops the table at empty cells even if they contain a formula. Less efficient than if set to False.

        Returns
        -------
        Range
            xlwings Range object

        """
        row2 = Range(self.sheet.Name, (self.row1, self.col1), **self.kwargs).vertical.row2
        col2 = Range(self.sheet.Name, (self.row1, self.col1), **self.kwargs).horizontal.col2

        return Range(self.sheet.Name, (self.row1, self.col1), (row2, col2), **self.kwargs)

    @property
    def vertical(self):
        """
        Returns a contiguous Range starting with the indicated cell and going down as long as no empty cell is hit. For
        example, to get the values of a contiguous range or clear its contents use:

            Range('A1').vertical.value
            Range('A1').vertical.clear_contents()

        Parameters
        ----------
        strict : bool, default False
            strict stops the table at empty cells even if they contain a formula. Less efficient than if set to False.

        Returns
        -------
        Range
            xlwings Range object

        """
        if self.sheet.Cells(self.row1 + 1, self.col1).Value in [None, ""]:
            row2 = self.row1
        else:
            row2 = self.sheet.Cells(self.row1, self.col1).End(constants.xlDown).Row

        if self.strict:
            row2 = self.row1
            while self.sheet.Cells(row2 + 1, self.col1).Value not in [None, ""]:
                row2 += 1

        col2 = self.col2

        return Range(self.sheet.Name, (self.row1, self.col1), (row2, col2), **self.kwargs)

    @property
    def horizontal(self):
        """
        Returns a contiguous Range starting with the indicated cell and going right as long as no empty cell is hit. For
        example, to get the values of a contiguous range or clear its contents use:

            Range('A1').horizontal.value
            Range('A1').horizontal.clear_contents()

        Parameters
        ----------
        strict : bool, default False
            strict stops the table at empty cells even if they contain a formula. Less efficient than if set to False.

        Returns
        -------
        Range
            xlwings Range object

        """
        if self.sheet.Cells(self.row1, self.col1 + 1).Value in [None, ""]:
            col2 = self.col1
        else:
            col2 = self.sheet.Cells(self.row1, self.col1).End(constants.xlToRight).Column

        if self.strict:
            col2 = self.col1
            while self.sheet.Cells(self.row1, col2 + 1).Value not in [None, ""]:
                col2 += 1

        row2 = self.row2

        return Range(self.sheet.Name, (self.row1, self.col1), (row2, col2), **self.kwargs)

    @property
    def current_region(self):
        """
        The current_region property returns a Range object representing a range bounded by (but not including) any
        combination of blank rows and blank columns or the edges of the worksheet
        VBA equivalent: CurrentRegion property of Range object

        Returns
        -------
        Range
            xlwings Range object

        """
        current_region = self.sheet.Cells(self.row1, self.col1).CurrentRegion
        row2 = self.row1 + current_region.Rows.Count - 1
        col2 = self.col1 + current_region.Columns.Count - 1
        return Range(self.sheet.Name, (self.row1, self.col1), (row2, col2), **self.kwargs)

    def clear(self):
        self.cell_range.Clear()

    def clear_contents(self):
        self.cell_range.ClearContents()

if __name__ == "__main__":
    xlwings_connect(r'C:\DEV\Git\xlwings\tests\test1.xlsx')

    print Range('C1').table.value
