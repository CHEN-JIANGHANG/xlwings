---
layout: page
title: "Quickstart"
---

## Quickstart

### Installation

The easiest way to install xlwings wings is via the command prompt and pip:

```python
pip install xlwings
```

Alternatively, it can be installed via conda on an Anaconda distribution:

```python
conda install xlwings
```

Note that xlwings is already included in [Anaconda 2.0][] (Python 2.7 version).

### Interact with Excel from Python

Writing/reading values to/from Excel and adding a chart is as easy as:

```python
>>> from xlwings import Workbook, Range, Chart
>>> wb = Workbook()  # Creates a connection with a new workbook
>>> Range('A1').value = ['Foo 1', 'Foo 2', 'Foo 3', 'Foo 4']
>>> Range('A2').value = [10, 20, 30, 40]
>>> Range('A1').table.value  # Read the whole table back
[[u'Foo 1', u'Foo 2', u'Foo 3', u'Foo 4'], [10.0, 20.0, 30.0, 40.0]]
>>> chart = Chart().add()
>>> chart.set_source_data(Range('A1').table)
```

The Range object as used above will refer to the active sheet. Include the Sheet name like this:

```python
Range('Sheet1', 'A1').value
```

Qualify the Workbook additionally like this:

```python
wb.range('Sheet1', 'A1').value
```

The good news is that these commands also work seamlessly with *NumPy arrays* and *Pandas DataFrames*.

### Call Python from Excel

If, for example, you want to fill your spreadsheet with standard normally distributed random numbers, your VBA code is
just one line:

```vbnet
Sub RandomNumbers()
    RunPython ("import mymodule; mymodule.rand_numbers()")
End Sub
```

This essentially hands over control to `mymodule.py`:

```python
import numpy as np
from xlwings import Workbook, Range

wb = Workbook()  # Creates a reference to the calling Excel file

def rand_numbers():
    """ produces standard normally distributed random numbers with shape (n,n)"""
    n = Range('Sheet1', 'B1').value
    rand_num = np.random.randn(n, n)
    Range('Sheet1', 'C3').value = rand_num
```

To make this run, just import the VBA module `xlwings.bas` in the VBA editor (open the VBA editor with `Alt-F11`, then
go to `File > Import File...` and import the `xlwings.bas` file). It can be found in the directory of your `xlwings`
installation.

### Easy deployment

Deployment is really the part that makes xlwings so awesome (head over to the [examples][] to check it out yourself):

* Just zip-up your Spreadsheet with your Python code and the `xlwings.py` file (again, it can be found in the
  directory of your xlwings installation) and send it around. The receiver only needs to have an installation of
  Python with [pywin32][] (and obviously all the other packages you're using).
* There is no need to install any Excel add-in.
* If this still sounds too complicated, just freeze your Python code into an executable and use `RunFrozenPython`
  instead of `RunPython`. This gives you a standalone version of your Spreadsheet tool without any dependencies.
  Please see the [Docs][] for further details.

[pywin32]: http://sourceforge.net/projects/pywin32
[Docs]: http://docs.xlwings.org
[Examples]: /examples
[Anaconda 2.0]: https://store.continuum.io/cshop/anaconda/