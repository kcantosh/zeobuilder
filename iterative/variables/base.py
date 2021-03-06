# -*- coding: utf-8 -*-
# Zeobuilder is an extensible GUI-toolkit for molecular model construction.
# Copyright (C) 2007 - 2012 Toon Verstraelen <Toon.Verstraelen@UGent.be>, Center
# for Molecular Modeling (CMM), Ghent University, Ghent, Belgium; all rights
# reserved unless otherwise stated.
#
# This file is part of Zeobuilder.
#
# Zeobuilder is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# In addition to the regulations of the GNU General Public License,
# publications and communications based in parts on this program or on
# parts of this program are required to cite the following article:
#
# "ZEOBUILDER: a GUI toolkit for the construction of complex molecules on the
# nanoscale with building blocks", Toon Verstraelen, Veronique Van Speybroeck
# and Michel Waroquier, Journal of Chemical Information and Modeling, Vol. 48
# (7), 1530-1541, 2008
# DOI:10.1021/ci8000748
#
# Zeobuilder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
#--


__all__ = ["Variable", "Helper", "SanityError"]


class SanityError(Exception):
    pass


class Variable(object):
    dimension = 0

    def __init__(self):
        #self.parent_expression = None
        self.state_index = None
        self.state = None
        self.derivatives = None

    def sanity_check(self):
        if self.dimension == 0:
            raise SanityError("A Variable dimension must be strictly positive.")

    def connect(self, state, derivatives, mass):
        self.state = state[self.state_index: self.state_index + self.dimension]
        self.derivatives = derivatives[self.state_index: self.state_index + self.dimension]
        self.mass = mass[self.state_index: self.state_index + self.dimension]

    def extract_state(self, state_index, state):
        raise NotImplementedError


class Helper(Variable):
    def __init__(self, *input_variables):
        Variable.__init__(self)
        self.input_variables = input_variables
        self.parent_expression = None




