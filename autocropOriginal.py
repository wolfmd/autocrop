import numpy as np
import scipy.ndimage as ndimage
import scipy.spatial as spatial
import scipy.misc as misc
import matplotlib.pyplot as plt
import matplotlib.patches as patches

class BBox(object):
    def __init__(self, x1, y1, x2, y2):
        '''
        (x1, y1) is the upper left corner,
        (x2, y2) is the lower right corner,
        with (0, 0) being in the upper left corner.
        '''
        if x1 > x2: x1, x2 = x2, x1
        if y1 > y2: y1, y2 = y2, y1
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
    def taxicab_diagonal(self):
        '''
        Return the taxicab distance from (x1,y1) to (x2,y2)
        '''
        return self.x2 - self.x1 + self.y2 - self.y1
    def overlaps(self, other):
        '''
        Return True iff self and other overlap.
        '''
        return not ((self.x1 > other.x2)
                    or (self.x2 < other.x1)
                    or (self.y1 > other.y2)
                    or (self.y2 < other.y1))
    def __eq__(self, other):
        return (self.x1 == other.x1
                and self.y1 == other.y1
                and self.x2 == other.x2
                and self.y2 == other.y2)

def find_paws(data, smooth_radius = 5, threshold = 0.0001):
    # https://stackoverflow.com/questions/4087919/how-can-i-improve-my-paw-detection
    """Detects and isolates contiguous regions in the input array"""
    # Blur the input data a bit so the paws have a continous footprint
    data = ndimage.uniform_filter(data, smooth_radius)
    # Threshold the blurred data (this needs to be a bit > 0 due to the blur)
    thresh = data > threshold
    # Fill any interior holes in the paws to get cleaner regions...
    filled = ndimage.morphology.binary_fill_holes(thresh)
    # Label each contiguous paw
    coded_paws, num_paws = ndimage.label(filled)
    # Isolate the extent of each paw
    # find_objects returns a list of 2-tuples: (slice(...), slice(...))
    # which represents a rectangular box around the object
    data_slices = ndimage.find_objects(coded_paws)
    return data_slices

def slice_to_bbox(slices):
    for s in slices:
        dy, dx = s[:2]
        yield BBox(dx.start, dy.start, dx.stop+1, dy.stop+1)

def remove_overlaps(bboxes):
    '''
    Return a set of BBoxes which contain the given BBoxes.
    When two BBoxes overlap, replace both with the minimal BBox that contains both.
    '''
    # list upper left and lower right corners of the Bboxes
    corners = []

    # list upper left corners of the Bboxes
    ulcorners = []

    # dict mapping corners to Bboxes.
    bbox_map = {}

    for bbox in bboxes:
        ul = (bbox.x1, bbox.y1)
        lr = (bbox.x2, bbox.y2)
        bbox_map[ul] = bbox
        bbox_map[lr] = bbox
        ulcorners.append(ul)
        corners.append(ul)
        corners.append(lr)

    # Use a KDTree so we can find corners that are nearby efficiently.
    tree = spatial.KDTree(corners)
    new_corners = []
    for corner in ulcorners:
        bbox = bbox_map[corner]
        # Find all points which are within a taxicab distance of corner
        indices = tree.query_ball_point(
            corner, bbox_map[corner].taxicab_diagonal(), p = 1)
        for near_corner in tree.data[indices]:
            near_bbox = bbox_map[tuple(near_corner)]
            if bbox != near_bbox and bbox.overlaps(near_bbox):
                # Expand both bboxes.
                # Since we mutate the bbox, all references to this bbox in
                # bbox_map are updated simultaneously.
                bbox.x1 = near_bbox.x1 = min(bbox.x1, near_bbox.x1)
                bbox.y1 = near_bbox.y1 = min(bbox.y1, near_bbox.y1)
                bbox.x2 = near_bbox.x2 = max(bbox.x2, near_bbox.x2)
                bbox.y2 = near_bbox.y2 = max(bbox.y2, near_bbox.y2)
    return set(bbox_map.values())

if __name__ == '__main__':
    fig = plt.figure()
    ax = fig.add_subplot(111)

    data = misc.imread('image.png')
    im = ax.imshow(data)
    data_slices = find_paws(255-data, smooth_radius = 20, threshold = 22)

    bboxes = remove_overlaps(slice_to_bbox(data_slices))
    for bbox in bboxes:
        xwidth = bbox.x2 - bbox.x1
        ywidth = bbox.y2 - bbox.y1
        p = patches.Rectangle((bbox.x1, bbox.y1), xwidth, ywidth,
                              fc = 'none', ec = 'red')
        ax.add_patch(p)

    plt.show()
