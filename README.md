# autocrop
A small, cobbled-together Python 3 script for automatically cropping an image 
comprised of many images into a individual image files. It works on all files
in a directory.

This is not a pretty script but it does what I need it to do.

![alt text](https://raw.githubusercontent.com/wolfmd/autocrop/master/example.png)

## Usage
This can be invoked such as:

```
pip3 install -r requirements.txt
python3 autocrop.py --dir <dir> --min-width=1000 
```

Or for images with black backgrounds (I've found this to be more effective)

```
python3 autocrop.py --dir <dir> --min-width=1000 --inv
```

Setting min-width makes it less likely that the algorithm will find smaller 
rectangles within the photos

## Thank you
This script was mostly stolen from 
https://stackoverflow.com/users/63550/peter-mortensen
at
https://stackoverflow.com/questions/4087919/how-can-i-improve-my-paw-detection
Thank you for saving me hours of my life.

That script is stored at autocropOriginal.py