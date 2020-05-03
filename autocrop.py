import scipy.ndimage as ndimage
import scipy.spatial as spatial
import imageio
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import argparse
import cv2
import os
from PIL import Image

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
    return bbox_map

if __name__ == '__main__':

    #Some hella basic params
    parser = argparse.ArgumentParser(description='Crop some photos.')
    parser.add_argument('--dir',type=str,help='dir to crop')
    parser.add_argument('--inv',action="store_true", help='inverse color for dark bgs')
    parser.add_argument('--min-height', dest='minheight', type=int, default=50, help='min height of box to pull from the image')
    parser.add_argument('--min-width',dest='minwidth', type=int, default=50, help='min width of box to pull from the image')
    parser.add_argument('-v','--verbose',action="store_true", help='display the plotted paw boxes after saving the files')

    args = parser.parse_args()
    targetdir = args.dir
    targetimages = os.listdir(targetdir)

    for targetimage in targetimages:
        targetimage = "{}/{}".format(targetdir, targetimage)
        print(targetimage)

        #Create a figure to display later
        if args.verbose:
            fig = plt.figure()
            ax = fig.add_subplot(111)

        try:
            data = imageio.imread(targetimage)
        except IOError:
            # ignore anything that can't be construed as an image
            continue
        grayscaled = cv2.cvtColor(data,cv2.COLOR_BGR2GRAY)

        #Optional color inversion
        if args.inv:
            prepped_image = cv2.bitwise_not(grayscaled)
        else:
            prepped_image = grayscaled

        ret,threshed_image = cv2.threshold(prepped_image,200,255,cv2.THRESH_BINARY)

        if args.verbose:
            im = ax.imshow(threshed_image)
        data_slices = find_paws(255-threshed_image, smooth_radius = 20, threshold = 25)

        bboxes = remove_overlaps(slice_to_bbox(data_slices))
        i = 0
        bbx1s = []
        for bbox in bboxes.items():
            bbox = bbox[1]
            print(bbox)
            xwidth = bbox.x2 - bbox.x1
            ywidth = bbox.y2 - bbox.y1
            print(i, xwidth, ywidth, bbox.x1, bbox.x2, bbox.y1, bbox.y2)
            if xwidth > args.minwidth and ywidth > args.minheight and bbox.x1 not in bbx1s:
                #Open original target image
                tim = Image.open(targetimage)
                p = patches.Rectangle((bbox.x1, bbox.y1), xwidth, ywidth,
                                      fc = 'none', ec = 'red')
                #Plot patches
                if args.verbose:
                    ax.add_patch(p)

                #Crop and save that sucka
                tim = tim.crop((bbox.x1, bbox.y1, bbox.x2, bbox.y2))
                tim.save("{}_crop_{}.png".format(targetimage.split('.')[0],i))
                i = i +1
                bbx1s.append(bbox.x1)

    # Show the plots and stuff
    if args.verbose:
        plt.show()
