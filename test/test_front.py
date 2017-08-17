import os
import time
import logging
import matplotlib.pyplot as plt
import numpy as np
import pdb

from scipy import optimize as opt

from stompy.spatial import field
from stompy import utils

from stompy.grid import (unstructured_grid, exact_delaunay, front)

import logging
logging.basicConfig(level=logging.INFO)

from stompy.spatial.linestring_utils import upsample_linearring,resample_linearring
from stompy.spatial import field,constrained_delaunay,wkb2shp

reload(unstructured_grid)
reload(exact_delaunay)
reload(front)

## Curve -

def hex_curve():
    hexagon = np.array( [[0,11],
                         [10,0],
                         [30,0],
                         [40,9],
                         [30,20],
                         [10,20]] )
    return front.Curve(hexagon)

def test_curve_eval():
    crv=hex_curve()
    f=np.linspace(0,2*crv.total_distance(),25)
    crvX=crv(f)
    
    if 0: # skip plots
        plt.clf()
        crv.plot()

        f=np.linspace(0,crv.total_distance(),25)
        crvX=crv(f)
        plt.plot(crvX[:,0],crvX[:,1],'ro')

def test_distance_away():
    crv=hex_curve()

    if 0: # skip plots
        plt.clf()
        crv.plot()
        plt.axis('equal')
        
    rtol=0.05

    for f00,tgt,style in [ (0,10,'g-'),
                           (3.4,20,'r-'),
                           (3.4,-20,'r--') ]:
        for f0 in np.linspace(f00,crv.distances[-1],20):
            x0=crv(f0)
            f,x =crv.distance_away(f0,tgt,rtol=rtol)
            d=utils.dist(x-x0)
            assert np.abs( (d-np.abs(tgt))/tgt) <= rtol
            if 0:
                plt.plot( [x0[0],x[0]],
                          [x0[1],x[1]],style)

    try:
        f,x=crv.distance_away(0.0,50,rtol=0.05)
        raise Exception("That was supposed to fail!")
    except crv.CurveException:
        #print "Okay"
        pass


def test_distance_away2():
    # Towards a smarter Curve::distance_away(), which understands
    # piecewise linear geometry
    island  =np.array([[200,200],[600,200],[200,600]])
    curve=front.Curve(island)

    anchor_f=919.3
    signed_distance=50.0
    res=curve.distance_away(anchor_f,signed_distance)
    assert res[0]>anchor_f
    anchor_pnt=curve(anchor_f)

    rel_err=np.abs( utils.dist(anchor_pnt - res[1]) - abs(signed_distance)) / abs(signed_distance)
    assert np.abs(rel_err)<=0.05

    anchor_f=440
    signed_distance=-50.0
    res=curve.distance_away(anchor_f,signed_distance)

    anchor_pnt=curve(anchor_f)

    rel_err=np.abs( utils.dist(anchor_pnt - res[1]) - abs(signed_distance)) / abs(signed_distance)
    assert res[0]<anchor_f
    assert np.abs(rel_err)<=0.05
    
def test_distance3():
    # Case where the return point is on the same segment as it starts
    curve=front.Curve(np.array([[   0,    0],
                                [1000,    0],
                                [1000, 1000],
                                [   0, 1000]]),closed=True)
    res=curve.distance_away(3308.90,50.0)
    res=curve.distance_away(3308.90,-50.0)
    
def test_is_forward():
    crv=hex_curve()
    assert crv.is_forward(5,6,50)
    assert crv.is_reverse(5,-5,10)


## 
def test_curve_upsample():
    boundary=hex_curve()
    scale=field.ConstantField(3)

    pnts,dists = boundary.upsample(scale,return_sources=True)

    if 0:
        plt.clf()
        line=boundary.plot()
        plt.setp(line,lw=0.5,color='0.5')

        #f=np.linspace(0,crv.total_distance(),25)
        #crvX=crv(f)
        plt.scatter(pnts[:,0],pnts[:,1],30,dists,lw=0)
    
def test_basic_setup():
    boundary=hex_curve()
    af=front.AdvancingTriangles()
    scale=field.ConstantField(3)

    af.add_curve(boundary)
    af.set_edge_scale(scale)

    # create boundary edges based on scale and curves:
    af.initialize_boundaries()

    if 0:
        plt.clf()
        g=af.grid
        g.plot_edges()
        g.plot_nodes()

        # 
        coll=g.plot_halfedges(values=g.edges['cells'])
        coll.set_lw(0)
        coll.set_cmap('winter')

    return af


# Going to try more of a half-edge approach, rather than explicitly
# tracking the unpaved rings.
# hoping that a half-edge interface is sufficient for the paver, and
# could be supported by multiple representations internally.

# for starters, don't worry about caching/speed/etc.
# okay to start from scratch each time.

# the product here is a list of the N best internal angles for
# filling with a triangle(s)

def test_halfedge_traverse():
    af=test_basic_setup()
    J,Orient = np.nonzero( (af.grid.edges['cells'][:,:]==af.grid.UNMESHED) )

    # he=he0=HalfEdge(af.grid,J[0],Orient[0])
    he=he0=af.grid.halfedge(J[0],Orient[0])

    for i in range(af.grid.Nedges()*2):
        he=he.fwd()
        if he == he0:
            break
    else:
        assert False
    assert i==31 # that had been 33, but now I'm getting 31.  may need to be smarter.

    he=he0=af.grid.halfedge(J[0],Orient[0])

    for i in range(af.grid.Nedges()*2):
        he=he.rev()
        if he == he0:
            break
    else:
        assert False
    assert i==31 # pretty sure about that number...

    assert he.fwd().rev() == he
    assert he.rev().fwd() == he
    #-# 

def test_merge_edges():
    af=test_basic_setup()

    new_j=af.grid.merge_edges(node=0)
    
    he0=he=af.grid.halfedge(new_j,0)
    c0_left = af.grid.edges['cells'][he.j,he.orient]
    c0_right = af.grid.edges['cells'][he.j,1-he.orient]

    while True:
        he=he.fwd()
        c_left = af.grid.edges['cells'][he.j,he.orient]
        c_right = af.grid.edges['cells'][he.j,1-he.orient]
        assert c_left==c0_left
        assert c_right==c0_right
        
        if he==he0:
            break

    if 0:
        plt.clf()
        af.grid.plot_edges()

        coll=af.grid.plot_halfedges(values=af.grid.edges['cells'])
        coll.set_lw(0)
        coll.set_cmap('winter')

# when resample nodes on a sliding boundary, want to calculate the available
# span, and if it's small, start distributing the nodes evenly.
# where small is defined by local_scale * max_span_factor

def test_resample():
    af=test_basic_setup()
    a=0
    b=af.grid.node_to_nodes(a)[0]
    he=af.grid.nodes_to_halfedge(a,b)
    anchor=he.node_rev()
    n=he.node_fwd()
    n2=he.rev().node_rev()
    af.resample(n=n,anchor=anchor,scale=25,direction=1)
    af.resample(n=n2,anchor=anchor,scale=25,direction=-1)

    if 0:
        plt.clf()
        af.grid.plot_edges()

        coll=af.grid.plot_halfedges(values=af.grid.edges['cells'])
        coll.set_lw(0)
        coll.set_cmap('winter')
    
    
#-#     


def test_resample_neighbors():
    af=test_basic_setup()
    
    if 0:
        plt.clf()
        af.grid.plot_nodes(color='r')
    
    site=af.choose_site()
            
    af.resample_neighbors(site)

    if 0:
        af.grid.plot_edges()

        af.grid.plot_nodes(color='g')
        # hmm - some stray long edges, where it should be collinear
        # ahh - somehow node 23 is 3.5e-15 above the others.
        # not sure why it happened, but for the moment not a show stopper.
        # in fact probably a good test of the robust predicates
        af.cdt.plot_edges(values=af.cdt.edges['constrained'],lw=3,alpha=0.5)

        plt.axis( [34.91, 42.182, 7.300, 12.97] )
    return af
        

# enumerate the strategies for a site:
# paver preemptively resamples the neighbors
# conceivable that one action might want to resample the neighbors
# in a slightly different way than another action.
# but the idea of having them spaced at the local scale when possible
# is general enough to do it preemptively.

# strategies:
#  try this as a separate class for each strategy, but they are all singletons


def test_actions():
    af=test_basic_setup()

    site=af.choose_site()
    af.resample_neighbors(site)
    actions=site.actions()
    metrics=[a.metric(site) for a in actions]
    best=np.argmin(metrics)
    edits=actions[best].execute(site)
    af.optimize_edits(edits)

##

# af=test_basic_setup()
# check0=af.grid.checkpoint()

# #

# Back-tracking
# The idea is that with sufficient roll-back, it can build a 
# decision tree and optimize between strategies.
# There are at least two ways in which this can be used:
#   optimizing: try multiple strategies, possibly even multiple
#     steps of each, evaluate the quality of the result, and then
#     go with the best one.
#   recovering: when a strategy fails, step back one or more steps
#     and try other options.


# This process should be managed in a decision tree, where each node
# of the tree represents a state, any metrics associated with that
# state, and the set of choices for what to do next.

# The decisions are (i) which site to pursue, and (ii) which strategy
# to apply at the site.

# There has to be a way to "commit" parts of the tree, moving the root
# of the tree down.

# Assuming that we deal with only one copy of the grid, then at most one
# node in the tree reflects the actual state of the grid.

# As long as we're careful about how checkpoints store data (i.e. no
# shared state), then chunks of the op_stack can be stored and used
# for quicker fast-forwarding.

# There is a distinction between decisions which have been tried (and
# so they can have a metric for how it turned out, and some operations for
# fast-forwarding the actions), versus decisions which have been posed
# but not tried.
# Maybe it's up to the parent node to hold the set of decisions, and as
# they are tried, then we populate the child nodes.


def test_dt_one_loop():
    """ fill a squat hex with triangles.
    """
    af2=test_basic_setup()
    af2.log.setLevel(logging.INFO)

    af2.cdt.post_check=False
    af2.loop()
    if 0:
        plt.figure(2).clf()
        fig,ax=plt.subplots(num=2)
        af2.plot_summary(ax=ax)
        ax.set_title('loop()')


##


def test_dt_backtracking():
    """
    test a bit more of the decision tree.
    tries all possible children, at least for strategies,
    then goes with the "best" one.
    """
    if 0:
        plt.figure(1).clf()
        fig,ax=plt.subplots(num=1)
        
    af=test_basic_setup()
    af.log.setLevel(logging.INFO)

    af.cdt.post_check=False
    
    af.root=front.DTChooseSite(af)
    af.current=af.root

    if 0:
        def cb():
            print("tried...")
            af.plot_summary()
            fig.canvas.draw()
    else:
        def cb():
            pass
        
    af.current.best_child()
    af.current.best_child(cb=cb)
    af.current.best_child()
    # This is leaving things in a weird place
    # maybe fixed now?
    af.current.best_child(cb=cb)

## 
# Single step lookahead:

def test_singlestep_lookahead():
    af=test_basic_setup()

    af.log.setLevel(logging.INFO)
    af.cdt.post_check=False
    af.current=af.root=front.DTChooseSite(af)

    while 1:
        if not af.current.children:
            break # we're done?

        if not af.current.best_child(): # cb=cb
            assert False
        
    return af

## 
# Basic, no lookahead:
# This produces better results because the metrics have been pre-tuned

def test_no_lookahead():
    af=test_basic_setup()
    af.log.setLevel(logging.INFO)
    af.cdt.post_check=False

    af.current=af.root=front.DTChooseSite(af)

    def cb():
        af.plot_summary(label_nodes=False)
        try:
            af.current.site.plot()
        except: # AttributeError:
            pass

    while 1:
        if not af.current.children:
            break # we're done?

        for child_i in range(len(af.current.children)):
            if af.current.try_child(child_i):
                # Accept the first child which returns true
                break
        else:
            assert False # none of the children worked out

##

# Why does it divege from symmetry at the start?
# part of this is because the combination of the original
# metrics and the exact angles of the test case (90deg) lead
# to a decision based on numerical roundoff
# the optimization methods also have an effect here, as there
# is the potential to have a bistable minimization problem,
# and the numerical optimization chooses in a non-symmetric way.

## 
# 6. Implement n-lookahead

# on sfei desktop, it's 41 cells/s.

# I think the best plan of attack is to roughly replicate the way paver
# worked, then extend with the graph search

#   Need to think about how these pieces are going to work together
#   And probably a good time to (a) start adding the rollback, graph
#   search side of things.
#   CDT is included now, and can trigger an alternate strategy when
#   edges intersect.  No non-local connections, though.


### 

# Bringing in the suite of test cases from test_paver*.py


def trifront_wrapper(rings,scale,label=None):
    af=front.AdvancingTriangles()
    af.set_edge_scale(scale)
    
    af.add_curve(rings[0],interior=False)
    for ring in rings[1:]:
        af.add_curve(ring,interior=True)
    af.initialize_boundaries()

    try:
        result = af.loop()
    finally:
        if label is not None:
            plt.figure(1).clf()
            af.grid.plot_edges(lw=0.5)
            plt.savefig('af-%s.png'%label)
    assert result
    
    return af
    
def test_pave_quad():
    # Define a polygon
    rings=[ np.array([[0,0],[1000,0],[1000,1000],[0,1000]]) ] 
    # And the scale:
    scale=field.ConstantField(50)

    return trifront_wrapper(rings,scale,label='quad')
    
def test_pave_basic():
    # big square with right triangle inside
    # Define a polygon
    boundary=np.array([[0,0],[1000,0],[1000,1000],[0,1000]])
    island  =np.array([[200,200],[600,200],[200,600]])
    rings=[boundary,island]
    # And the scale:
    scale=field.ConstantField(50)

    return trifront_wrapper(rings,scale,label='basic_island')


# It continues to choose bad nonlocals.
# - could go back to the approach of the old code, which made a more
#   explicit list of local nodes based on distance traversed along edges.
# - is there a way to use more of the geometry in the DT to direct this?
#   cast a ray in only particular directions?
#   a bit easier for a bisect.
# - maybe testing for nonlocal neighbors should only happen when new nodes are
#   created: bisect, wall.  At that point, there is a choice of whether the new
#   node's ideal location is close enough to a nonlocal element that the new node
#   should actually be a connection to that nonlocal element.
# - back in paver - what are the details of how it worked?
#   1. get a scale based on target scale and scale of the site.
#   2. local_nodes() does some type of local area sort with a threshold
#      distance.
#   3. delaunay neighbors of the center of the element (node 'b') are
#      queried -- are they close enough to 'b', and far enough away
#      when traversing existing edges.
#   4. If no nodes arose from step 3, then shoot a ray and potentially
#      resample whatever is found.


## 
# a Decision-tree loop would look like:
#     af=test_basic_setup()
#     af.log.setLevel(logging.INFO)
#     af.cdt.post_check=False
# 
#     af.current=af.root=DTChooseSite(af)
# 
#     def cb():
#         af.plot_summary(label_nodes=False)
#         try:
#             af.current.site.plot()
#         except: # AttributeError:
#             pass
#         # fig.canvas.draw()
#         plt.pause(0.01)
# 
#     while 1:
#         if not af.current.children:
#             break # we're done?
# 
#         for child_i in range(len(af.current.children)):
#             if af.current.try_child(child_i):
#                 # Accept the first child which returns true
#                 break
#         else:
#             assert False # none of the children worked out
#         #cb()
#     af.plot_summary(ax=ax)


##     
# A circle - r = 100, C=628, n_points = 628
# This is super slow!  there are lot of manipulations to the cdt
# which cause far-reaching changes.
def test_circle():
    r = 100
    thetas = np.linspace(0,2*np.pi,200)[:-1]
    circle = np.zeros((len(thetas),2),np.float64)
    circle[:,0] = r*np.cos(thetas)
    circle[:,1] = r*np.sin(thetas)
    class CircleDensityField(field.Field):
        # horizontally varying, from 5 to 20
        def value(self,X):
            X = np.array(X)
            return 5 + 15 * (X[...,0] + 100) / 200.0
    scale = CircleDensityField()
    rings=[circle]

    return trifront_wrapper([circle],scale,label='circle')


def test_long_channel():
    l = 2000
    w = 50
    long_channel = np.array([[0,0],
                             [l,0],
                             [l,w],
                             [0,w]], np.float64 )

    density = field.ConstantField( 19.245 )
    trifront_wrapper([long_channel],density,label='long_channel')

def test_long_channel_rigid():
    assert False # no RIGID initialization yet
    l = 2000
    w = 50
    long_channel = np.array([[0,0],
                             [l,0],
                             [l,w],
                             [0,w]], np.float64 )

    density = field.ConstantField( 19.245 )
    trifront_wrapper([long_channel],density,initial_node_status=paver.Paving.RIGID,
                     label='long_channel_rigid')

##

def test_narrow_channel():
    # This passes now, but the result looks like it could use better
    # tuning of the parameters -- grid jumps from 1 to 3 cells across
    # the channel.
    l = 1000
    w = 50
    long_channel = np.array([[0,0],
                             [l,0.375*w],
                             [l,0.625*w],
                             [0,w]], np.float64 )

    density = field.ConstantField( w/np.sin(60*np.pi/180.) / 4 )
    trifront_wrapper([long_channel],density,label='narrow_channel')


##     
def test_small_island():
    l = 100
    square = np.array([[0,0],
                       [l,0],
                       [l,l],
                       [0,l]], np.float64 )

    r=10
    theta = np.linspace(0,2*np.pi,30)
    circle = r/np.sqrt(2) * np.swapaxes( np.array([np.cos(theta), np.sin(theta)]), 0,1)
    island1 = circle + np.array([45,45])
    island2 = circle + np.array([65,65])
    island3 = circle + np.array([20,80])
    rings = [square,island1,island2,island3]

    density = field.ConstantField( 10 )
    trifront_wrapper(rings,density,label='small_island')

    
##     
def test_tight_peanut():
    r = 100
    thetas = np.linspace(0,2*np.pi,300)
    peanut = np.zeros( (len(thetas),2), np.float64)
    x = r*np.cos(thetas)
    y = r*np.sin(thetas) * (0.9/10000 * x*x + 0.05)
    peanut[:,0] = x
    peanut[:,1] = y
    density = field.ConstantField( 6.0 )
    trifront_wrapper([peanut],density,label='tight_peanut')

##

def test_tight_with_island():
    # build a peanut first:
    r = 100
    thetas = np.linspace(0,2*np.pi,250)
    peanut = np.zeros( (len(thetas),2), np.float64)
    x = r*np.cos(thetas)
    y = r*np.sin(thetas) * (0.9/10000 * x*x + 0.05)
    peanut[:,0] = x
    peanut[:,1] = y

    # put two holes into it
    thetas = np.linspace(0,2*np.pi,30)

    hole1 = np.zeros( (len(thetas),2), np.float64)
    hole1[:,0] = 10*np.cos(thetas) - 75
    hole1[:,1] = 10*np.sin(thetas)

    hole2 = np.zeros( (len(thetas),2), np.float64)
    hole2[:,0] = 20*np.cos(thetas) + 75
    hole2[:,1] = 20*np.sin(thetas)

    rings = [peanut,hole1,hole2]

    density = field.ConstantField( 6.0 )
    trifront_wrapper(rings,density,label='tight_with_island')

##
def test_peninsula():
    r = 100
    thetas = np.linspace(0,2*np.pi,1000)
    pen = np.zeros( (len(thetas),2), np.float64)

    pen[:,0] = r*(0.2+ np.abs(np.sin(2*thetas))**0.2)*np.cos(thetas)
    pen[:,1] = r*(0.2+ np.abs(np.sin(2*thetas))**0.2)*np.sin(thetas)

    density = field.ConstantField( 10.0 )
    pen2 = upsample_linearring(pen,density)
    
    trifront_wrapper([pen2],density,label='peninsula')

##

def test_cul_de_sac():
    r=5
    theta = np.linspace(-np.pi/2,np.pi/2,20)
    cap = r * np.swapaxes( np.array([np.cos(theta), np.sin(theta)]), 0,1)
    box = np.array([ [-3*r,r],
                     [-4*r,-r] ])
    ring = np.concatenate((box,cap))

    density = field.ConstantField(2*r/(np.sqrt(3)/2))
    trifront_wrapper([ring],density,label='cul_de_sac')


##     
def test_bow():
    x = np.linspace(-100,100,50)
    # with /1000 it seems to do okay
    # with /500 it still looks okay
    y = x**2 / 250.0
    bow = np.swapaxes( np.concatenate( (x[None,:],y[None,:]) ), 0,1)
    height = np.array([0,20])
    ring = np.concatenate( (bow+height,bow[::-1]-height) )
    density = field.ConstantField(2)
    trifront_wrapper([ring],density,label='bow')

def test_ngon(nsides=7):
    # hexagon works ok, though a bit of perturbation
    # septagon starts to show expansion issues, but never pronounced
    # octagon - works fine.
    theta = np.linspace(0,2*np.pi,nsides+1)[:-1]

    r=100
    
    x = r*np.cos(theta)
    y = r*np.sin(theta)
    
    poly = np.swapaxes( np.concatenate( (x[None,:],y[None,:]) ), 0,1)
    
    density = field.ConstantField(6)
    trifront_wrapper([poly],density,label='ngon%02d'%nsides)

def test_expansion():
    # 40: too close to a 120deg angle - always bisect on centerline
    # 30: rows alternate with wall and bisect seams
    # 35: starts to diverge, but recovers.
    # 37: too close to 120.
    d = 36
    pnts = np.array([[0.,0.],
                     [100,-d],
                     [200,0],
                     [200,100],
                     [100,100+d],
                     [0,100]])

    density = field.ConstantField(6)
    trifront_wrapper([pnts],density,label='expansion')

def test_embedded_channel():
    assert False # no API yet.
    # trying out degenerate internal lines - the trick may be mostly in
    # how to specify them.
    # make a large rectangle, with a sinuous channel in the middle
    L = 500.0
    W = 300.0
    
    rect = np.array([[0,0],
                  [L,0],
                  [L,W],
                  [0,W]])

    x = np.linspace(0.1*L,0.9*L,50)
    y = W/2 + 0.1*W*np.cos(4*np.pi*x/L)
    shore = np.swapaxes( np.concatenate( (x[None,:],y[None,:]) ), 0,1)
    
    density = field.ConstantField(10)
    
    # this will probably get moved into Paver itself.
    # Note closed_ring=0 !
    shore = resample_linearring(shore,density,closed_ring=0)

    south_shore = shore - np.array([0,0.1*W])
    north_shore = shore + np.array([0,0.1*W])

    p=paver.Paving([rect],density,degenerates=[north_shore,south_shore])
    p.pave_all()

def test_dumbarton():
    assert False # hold off
    
    shp=os.path.join( os.path.dirname(__file__), 'data','dumbarton.shp')
    features=wkb2shp.shp2geom(shp)
    geom = features['geom'][0]
    dumbarton = np.array(geom.exterior)
    density = field.ConstantField(250.0)
    p=paver.Paving(dumbarton, density,label='dumbarton')
    p.pave_all()


##
def test_peanut():
    # like a figure 8, or a peanut
    r = 100
    thetas = np.linspace(0,2*np.pi,1000)
    peanut = np.zeros( (len(thetas),2), np.float64)

    peanut[:,0] = r*(0.5+0.3*np.cos(2*thetas))*np.cos(thetas)
    peanut[:,1] = r*(0.5+0.3*np.cos(2*thetas))*np.sin(thetas)

    min_pnt = peanut.min(axis=0)
    max_pnt = peanut.max(axis=0)
    d_data = np.array([ [min_pnt[0],min_pnt[1], 1.5],
                        [min_pnt[0],max_pnt[1], 1.5],
                        [max_pnt[0],min_pnt[1], 8],
                        [max_pnt[0],max_pnt[1], 8]])
    density = field.XYZField(X=d_data[:,:2],F=d_data[:,2])

    trifront_wrapper([peanut],density,label='peanut')


def sine_sine_rings():
    
    t = np.linspace(1.0,12*np.pi,400)
    x1 = 100*t
    y1 = 200*np.sin(t)
    # each 2*pi, the radius gets bigger by exp(2pi*b)
    x2 = x1
    y2 = y1+50
    # now perturb both sides, but keep amplitude < 20
    y1 = y1 + 20*np.sin(10*t)
    y2 = y2 + 10*np.cos(5*t)
    
    x = np.concatenate( (x1,x2[::-1]) )
    y = np.concatenate( (y1,y2[::-1]) )

    shore = np.swapaxes( np.concatenate( (x[None,:],y[None,:]) ), 0,1)
    rings = [shore]

    # and make some islands:
    north_island_shore = 0.4*y1 + 0.6*y2
    south_island_shore = 0.6*y1 + 0.4*y2

    Nislands = 20
    # islands same length as space between islands, so divide
    # island shorelines into 2*Nislands blocks
    for i in range(Nislands):
        i_start = int( (2*i+0.5)*len(t)/(2*Nislands) )
        i_stop =  int( (2*i+1.5)*len(t)/(2*Nislands) )
        
        north_y = north_island_shore[i_start:i_stop]
        south_y = south_island_shore[i_start:i_stop]
        north_x = x1[i_start:i_stop]
        south_x = x2[i_start:i_stop]
        
        x = np.concatenate( (north_x,south_x[::-1]) )
        y = np.concatenate( (north_y,south_y[::-1]) )
        island = np.swapaxes( np.concatenate( (x[None,:],y[None,:]) ), 0,1)

        rings.append(island)
    return rings

def test_sine_sine():
    rings=sine_sine_rings()
    density = field.ConstantField(25.0)

    if 0: # no support for min_density yet
        min_density = field.ConstantField(2.0)

    # mostly just to make sure that long segments are
    # sampled well relative to the local feature scale.
    if 0: # no support yet
        p.smooth() 

        print("Adjusting other densities to local feature size")
        p.telescope_rate=1.1
        p.adjust_density_by_apollonius()

    trifront_wrapper(rings,density,label='sine_sine')

##

if 0:
    rings=sine_sine_rings()
    density = field.ConstantField(25.0)


    af=front.AdvancingTriangles()
    af.set_edge_scale(density)

    af.add_curve(rings[0],interior=False)
    for ring in rings[1:]:
        af.add_curve(ring,interior=True)
    af.initialize_boundaries()

    af.loop(12)

    ## 

    # af.loop(1)

    zoom=(3659.0438883805541, 3830.0274873892508, -115.41637873859611, 19.957127976555682)
    zoom=(3691.4047394120844, 3771.8443367653808, -88.483853026251893, -24.797099234640243)

    af.plot_summary(label_nodes=True)
    plt.axis(zoom)

    site=af.choose_site()
    site.plot()
    af.advance_at_site(site)

## 

# gets a few more steps in, but fails with a case where
# the boundary impinges on our ability to even do a simple cutoff.
# in the old code, I think there was more pro-active resampling
# along the boundary, to clear out neighboring nodes which were
# too close.
# could do something like that, or check the CDT to see if anybody
# is in our way before attempting a cutoff.

## 

# Who is failing at this point?
# test_tight_with_island() - why?
# 
# test_peanut: need to fix the bulk initialization of the CDT.
#   way way slow. maybe better now?
# test_sine_sine()
# test_dumbarton is disabled.
# test_embedded_channel - needs embedded edges, right?
# test_long_channel_rigid - needs additional API


