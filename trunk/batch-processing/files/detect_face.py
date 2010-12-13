#!/usr/bin/python

# This script fits faces to the images in a file. It is modified from the OpenCV facedetect sample.
# @Required:  OpenCV 2.x Python package installed

import sys
import cv

# Parameters for haar detection
# From the API:
# The default parameters (scale_factor=2, min_neighbors=3, flags=0) are tuned 
# for accurate yet slow object detection. For a faster operation on real video 
# images the settings are: 
# scale_factor=1.2, min_neighbors=2, flags=CV_HAAR_DO_CANNY_PRUNING, 
# min_size=<minimum possible face size

min_size = (20, 20)
image_scale = 2
haar_scale = 1.2
min_neighbors = 2
haar_flags = 0

def detect_and_save(img, cascade, output_name):
    # allocate temporary images
    gray = cv.CreateImage((img.width,img.height), 8, 1)
    small_img = cv.CreateImage((cv.Round(img.width / image_scale),
			       cv.Round (img.height / image_scale)), 8, 1)

    # convert color input image to grayscale
    cv.CvtColor(img, gray, cv.CV_BGR2GRAY)

    # scale input image for faster processing
    cv.Resize(gray, small_img, cv.CV_INTER_LINEAR)

    cv.EqualizeHist(small_img, small_img)

    if(cascade):
        t = cv.GetTickCount()
        faces = cv.HaarDetectObjects(small_img, cascade, cv.CreateMemStorage(0),
                                     haar_scale, min_neighbors, haar_flags, min_size)
        t = cv.GetTickCount() - t
        print "detection time = %gms" % (t/(cv.GetTickFrequency()*1000.))
        f = open(output_name, 'w')
        if faces:
            for ((x, y, w, h), n) in faces:
                f.write("%d %d %d %d\n" % (x, y, w, h))
                

if __name__ == '__main__':

    cascade = cv.Load(sys.argv[1])
    input_name = sys.argv[2]
    output_name = sys.argv[3]


    image = cv.LoadImage(input_name, 1)
    detect_and_save(image, cascade, output_name)