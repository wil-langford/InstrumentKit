#!/usr/bin/python
# -*- coding: utf-8 -*-
##
# util_fns.py: Random utility functions.
##
# © 2013 Steven Casagrande (scasagrande@galvant.ca).
#
# This file is a part of the InstrumentKit project.
# Licensed under the AGPL version 3.
##
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
##

## FEATURES ####################################################################

from __future__ import division

## IMPORTS #####################################################################

import sys

import quantities as pq
from flufl.enum import Enum, IntEnum

## FUNCTIONS ###################################################################

def assume_units(value, units):
    """
    If units are not provided for ``value`` (that is, if it is a raw
    `float`), then returns a `~quantities.Quantity` with magnitude
    given by ``value`` and units given by ``units``.
    
    :param value: A value that may or may not be unitful.
    :param units: Units to be assumed for ``value`` if it does not already
        have units.
        
    :return: A unitful quantity that has either the units of ``value`` or
        ``units``, depending on if ``value`` is unitful.
    :rtype: `Quantity`
    """
    if not isinstance(value, pq.Quantity):
        value = pq.Quantity(value, units)
    return value

def rproperty(fget=None, fset=None, doc=None, readonly=False):
    if readonly:
        return property(fget=fget, fset=None, doc=doc)
    else:
        return property(fget=fget, fset=fset, doc=doc)  

def bool_property(name, inst_true, inst_false, doc=None, readonly=False):
    """
    Called inside of SCPI classes to instantiate boolean properties 
    of the device cleanly.
    For example:
    
    >>> my_property = bool_property("BEST:PROPERTY", "ON", "OFF") # doctest: +SKIP
    
    :param str name: Name of the SCPI command corresponding to this property.
    :param str inst_true: String returned and accepted by the instrument for
        `True` values.
    :param str inst_false: String returned and accepted by the instrument for
        `False` values.
    :param str doc: Docstring to be associated with the new property.
    :param bool readonly: If `False`, the returned property does not have a
        setter.
    """
    def getter(self):
        return self.query(name + "?").strip() == inst_true
    def setter(self, newval):
        self.sendcmd("{} {}".format(name, inst_true if newval else inst_false))
        
    return rproperty(fget=getter, fset=setter, doc=doc, readonly=readonly)
    
def enum_property(name, enum, doc=None, input_decoration=None, output_decoration=None, readonly=False):
    """
    Called inside of SCPI classes to instantiate Enum properties 
    of the device cleanly.
    The decorations can be functions which modify the incoming and outgoing 
    values for dumb instruments that do stuff like include superfluous quotes
    that you might not want in your enum.
    Example:
    my_property = bool_property("BEST:PROPERTY", enum_class)
    
    :param str name: Name of the SCPI command corresponding to this property.
    :param type enum: Class derived from `Enum` representing valid values.
    :param callable input_decoration: Function called on responses from
        the instrument before passing to user code.
    :param callable input_decoration: Function called on commands to the
        instrument.
    :param str doc: Docstring to be associated with the new property.
    :param bool readonly: If `False`, the returned property does not have a
        setter.
    """
    def in_decor_fcn(val):
        return val if input_decoration is None else input_decoration(val)
    def out_decor_fcn(val):
        return val if output_decoration is None else output_decoration(val)
    def getter(self):
        return enum[in_decor_fcn(self.query("{}?".format(name)).strip())]
    def setter(self, newval):
        self.sendcmd("{} {}".format(name, out_decor_fcn(enum[newval].value)))
    
    return rproperty(fget=getter, fset=setter, doc=doc, readonly=readonly)

def unitless_property(name, format_code='{:e}', doc=None, readonly=False):
    """
    Called inside of SCPI classes to instantiate properties with unitless 
    numeric values.
    
    :param str name: Name of the SCPI command corresponding to this property.
    :param str format_code: Argument to `str.format` used in sending values
        to the instrument.
    :param str doc: Docstring to be associated with the new property.
    :param bool readonly: If `False`, the returned property does not have a
        setter.
    """
    def getter(self):
        raw = self.query("{}?".format(name))
        return float(raw)
    def setter(self, newval):
        strval = format_code.format(newval)
        self.sendcmd("{} {}".format(name, strval))

    return rproperty(fget=getter, fset=setter, doc=doc, readonly=readonly)

def int_property(name, format_code='{:d}', doc=None, readonly=False, valid_set=None):
    """
    Called inside of SCPI classes to instantiate properties with unitless 
    numeric values.
    
    :param str name: Name of the SCPI command corresponding to this property.
    :param str format_code: Argument to `str.format` used in sending values
        to the instrument.
    :param str doc: Docstring to be associated with the new property.
    :param bool readonly: If `False`, the returned property does not have a
        setter.
    :param valid_set: Set of valid values for the property, or `None` if all
        `int` values are valid.
    """
    def getter(self):
        raw = self.query("{}?".format(name))
        return int(raw)
    if valid_set is None:
        def setter(self, newval):
            strval = format_code.format(newval)
            self.sendcmd("{} {}".format(name, strval))
    else:
        def setter(self, newval):
            if newval not in valid_set:
                raise ValueError(
                    "{} is not an allowed value for this property; "
                    "must be one of {}.".format(newval, valid_set)
                )
            strval = format_code.format(newval)
            self.sendcmd("{} {}".format(name, strval))

    return rproperty(fget=getter, fset=setter, doc=doc, readonly=readonly)

def unitful_property(name, units, format_code='{:e}', doc=None, readonly=False):
    """
    Called inside of SCPI classes to instantiate properties with unitful numeric
    values. This function assumes that the instrument only accepts
    and returns magnitudes without unit annotations, such that all unit
    information is provided by the ``units`` argument. This is not suitable
    for instruments where the units can change dynamically due to front-panel
    interaction or due to remote commands.
    
    :param str name: Name of the SCPI command corresponding to this property.
    :param units: Units to assume in sending and receiving magnitudes to and
        from the instrument.
    :param str format_code: Argument to `str.format` used in sending the
        magnitude of values to the instrument.
    :param str doc: Docstring to be associated with the new property.
    :param bool readonly: If `False`, the returned property does not have a
        setter.
    """
    def getter(self):
        raw = self.query("{}?".format(name))
        return float(raw) * units
    def setter(self, newval):
        # Rescale to the correct unit before printing. This will also catch bad units.
        strval = format_code.format(assume_units(newval, units).rescale(units).item())
        self.sendcmd("{} {}".format(name, strval))

    return rproperty(fget=getter, fset=setter, doc=doc, readonly=readonly)

def string_property(name, bookmark_symbol='"', doc=None, readonly=False):
    """
    Called inside of SCPI classes to instantiate properties with a string value.
    """
    bookmark_length = len(bookmark_symbol)
    def getter(self):
        string = self.query("{}?".format(name))
        string = string[bookmark_length:-bookmark_length] if bookmark_length>0 else string
        return string
    def setter(self, newval):
        self.sendcmd("{} {}{}{}".format(name, bookmark_symbol, newval, bookmark_symbol))

    return rproperty(fget=getter, fset=setter, doc=doc, readonly=readonly)

## CLASSES #####################################################################

class ProxyList(object):
    def __init__(self, parent, proxy_cls, valid_set):
        self._parent = parent
        self._proxy_cls = proxy_cls
        self._valid_set = valid_set
        
        # FIXME: This only checks the next level up the chain!
        if hasattr(valid_set, '__bases__'):
            self._isenum = (Enum in valid_set.__bases__) or (IntEnum in valid_set.__bases__)
        else:
            self._isenum = False
    def __iter__(self):
        for idx in self._valid_set:
            yield self._proxy_cls(self._parent, idx)
    def __getitem__(self, idx):
        # If we have an enum, try to normalize by using getitem. This will
        # allow for things like 'x' to be used instead of enum.x.
        if self._isenum:
            try:
                idx = self._valid_set[idx]
            except ValueError:
                pass
            
        if idx not in self._valid_set:
            raise IndexError("Index out of range. Must be "
                                "in {}.".format(self._valid_set))
        return self._proxy_cls(self._parent, idx)
    def __len__(self):
        return len(self._valid_set)

if sys.version_info[0] == 2 and sys.version_info[1] == 6:

    import logging

    class NullHandler(logging.Handler):
        """
        Emulates the Python 2.7 NullHandler when on Python 2.6.
        """
        def emit(self, record):
            pass

else:

    from logging import NullHandler
