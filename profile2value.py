#!/usr/bin/env python
###############################################################################
#
#    profile2value.py
#    
#    Convert a descriptive profile into a single value between 0 -> 1 
#        ---> uses PCA
#
#    Useful for color coding one profile based on info contained in another
#
#    Copyright (C) 2012 Michael Imelfort
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import argparse
import sys
from pprint import pprint

import csv
import copy
import numpy as np
from pylab import plot,subplot,axis,stem,show,figure

###############################################################################
# CODE HERE
###############################################################################

def doWork( options ):
    # determine infile separator and if infile has header
    inCSV = open(options.infile, 'rb')
    has_header = False
    sample = inCSV.read(1024)
    dialect = csv.Sniffer().sniff(sample)
    if(csv.Sniffer().has_header(sample)):
        has_header = True

    # open the input and output files
    outCSV = csv.writer(open(options.outfile, 'wb'), dialect)
    inCSV = csv.reader(open(options.infile, 'rb'), dialect)
    if(has_header):
        inCSV.next()
    
    data_array = np.array([])
    names_array = np.array([])
    
    # convert the input csv into an array
    print "loading data..."
    num_rows = 0
    num_cols = 0
    max_rows = int(options.max_rows)
    for row in inCSV:
        if(0 == num_rows):
            num_cols = len(row)
        num_rows += 1  
        names_array = np.append(names_array, [row[0]])
        data_array = np.append(data_array, [float(x) for x in row[1:num_cols]])
        if((max_rows != 0) and (num_rows >= max_rows)):
            break
    
    # adjust for the row names
    num_cols -= 1
    print "Loaded" ,num_rows, "rows across" , num_cols, "cols"

    # do the PCA and extract the scores    
    data_array = np.reshape(data_array, (num_rows, num_cols))
    print "Performing PCA ..." ,
    Center(data_array,verbose=0)
    p = PCA(data_array)
    components = p.pc()
    
    # scale PC0
    min_score = float(min(components[:,0]))
    max_score = float(max(components[:,0]))-min_score
    scaled_scores = [(float(x)-min_score)/max_score for x in components[:,0]]
    
    # write to file
    outCSV.writerow(["'name'","'value'"])
    for index in range (0,num_rows):
        outCSV.writerow([names_array[index], scaled_scores[index]])
        
    # plot the PCA if we've been asked to...
    if(options.plot):
        figure()
        plot(components[:,0],components[:,1],'*g')
        axis('equal')
        show()   
    
    return 0

class PCA:
    """http://stackoverflow.com/questions/1730600/principal-component-analysis-in-python"""
    def __init__( self, A, fraction=0.90 ):
        assert 0 <= fraction <= 1
            # A = U . diag(d) . Vt, O( m n^2 ), lapack_lite --
        self.U, self.d, self.Vt = np.linalg.svd( A, full_matrices=False )
        assert np.all( self.d[:-1] >= self.d[1:] )  # sorted
        self.eigen = self.d**2
        self.sumvariance = np.cumsum(self.eigen)
        self.sumvariance /= self.sumvariance[-1]
        self.npc = np.searchsorted( self.sumvariance, fraction ) + 1
        self.dinv = np.array([ 1/d if d > self.d[0] * 1e-6  else 0
                                for d in self.d ])

    def pc( self ):
        """ e.g. 1000 x 2 U[:, :npc] * d[:npc], to plot etc. """
        n = self.npc
        return self.U[:, :n] * self.d[:n]

    # These 1-line methods may not be worth the bother;
    # then use U d Vt directly --

    def vars_pc( self, x ):
        n = self.npc
        return self.d[:n] * np.dot( self.Vt[:n], x.T ).T  # 20 vars -> 2 principal

    def pc_vars( self, p ):
        n = self.npc
        return np.dot( self.Vt[:n].T, (self.dinv[:n] * p).T ) .T  # 2 PC -> 20 vars

    def pc_obs( self, p ):
        n = self.npc
        return np.dot( self.U[:, :n], p.T )  # 2 principal -> 1000 obs

    def obs_pc( self, obs ):
        n = self.npc
        return np.dot( self.U[:, :n].T, obs ) .T  # 1000 obs -> 2 principal

    def obs( self, x ):
        return self.pc_obs( self.vars_pc(x) )  # 20 vars -> 2 principal -> 1000 obs

    def vars( self, obs ):
        return self.pc_vars( self.obs_pc(obs) )  # 1000 obs -> 2 principal -> 20 vars

class Center:
    """http://stackoverflow.com/questions/1730600/principal-component-analysis-in-python"""
    """ A -= A.mean() /= A.std(), inplace -- use A.copy() if need be
        uncenter(x) == original A . x
    """
        # mttiw
    def __init__( self, A, axis=0, scale=True, verbose=1 ):
        self.mean = A.mean(axis=axis)
        if verbose:
            print "Center -= A.mean:", self.mean
        A -= self.mean
        if scale:
            std = A.std(axis=axis)
            self.std = np.where( std, std, 1. )
            if verbose:
                print "Center /= A.std:", self.std
            A /= self.std
        else:
            self.std = np.ones( A.shape[-1] )
        self.A = A

    def uncenter( self, x ):
        return np.dot( self.A, x * self.std ) + np.dot( x, self.mean )

###############################################################################
# TEMPLATE SUBS
###############################################################################
#
# Entry point, parse command line args and call out to doWork
#
if __name__ == '__main__':
    
    # intialise the options parser
    parser = argparse.ArgumentParser(description='Convert a descriptive profile into a single value between 0 -> 1')

    # add options here:
    parser.add_argument('infile', help="CSV file of profiles to parse")
    parser.add_argument('outfile', help="The name of the CSV file to write to")

    parser.add_argument('-m', '--max_rows', default=0, help="Load only this many rows of data [default: load all rows]")
    parser.add_argument('-p', '--plot', action="store_true", default=False, help="Plot the PCA")

    # get and check options
    args = parser.parse_args()

    # do what we came here to do
    #
    doWork(args)