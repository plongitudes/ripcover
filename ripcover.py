#!/usr/bin/python

import argparse
import fnmatch
import os
import rarfile
import re
import string
import zipfile

# source, output dir and global array for unreadable archives
source_dir = ''
destination_dir = ''
existing_files = []
badfiles = []

# argparse section
def parse_the_args():
    parser = argparse.ArgumentParser(description='rip comic archive cover images and store in a central location.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--source', type=str, default='.', help='source directory containing archive files')
    parser.add_argument('-d', '--destination', type=str, default='./comic_covers', help='destination directory for cover images')
    return parser

# test for ouput path and create if missing
def test_output(path):
    #print ("entering dirtest")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

# walk the folder tree and find all files marked as comic archives
def find_all_files(path):
    #print ("entering find all files")
    filelist = []
    for root, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if (fnmatch.fnmatch(filename, '*.cbz')) or (fnmatch.fnmatch(filename, '*.cbr')) or (fnmatch.fnmatch(filename, '*.zip')) or (fnmatch.fnmatch(filename, '*.rar')):
                filelist.append(os.path.join(root, filename))

    return filelist

# grab all existing files and put them in a list
def skip_existing(testfile):
    #print ("entering test")
    for item in existing_files:
        against, against_ext = os.path.splitext(os.path.basename(testfile))
        #print ("testing " + item + " against " + against)
        if (item == against):
            print (testfile + " is valid, but already exists. skipping!")
            return 1
    return 0

# do a test for cbz or cbr since we can't rely on file extensions to be true
def test_for_cbr_cbz(incoming_archive):
    r = 0
    if zipfile.is_zipfile(incoming_archive):
        #print ("zip")
        r = 1
    elif rarfile.is_rarfile(incoming_archive):
        #print ("rar")
        r = 2
    else:
        badfiles.append("neither a zip nor a rar! " + incoming_archive)
        r = 3
    return r

# heavy lifting
def unzip_and_rip(archive, kind, source_dir, destination_dir):
    # if the file isn't bad in some way, move along
    goahead = 0

    # if it's a zip, open up a zip object
    if (kind == 1):
        comic = zipfile.ZipFile(archive)
        try:
            if comic.testzip() is None:
                goahead = 1
        except zipfile.BadZipfile:
            # add bad files to the list
            print ("Bad Zip: " + archive)
            badfiles.append("bad zip:" + archive)
            goahead = 0
        except:
            print ("unspecified zip error: " + archive)
            badfiles.append("unspecified zip error:" + archive)
            goahead = 1
    # otherwise, it must be a rar
    elif (kind == 2):
        comic = rarfile.RarFile(archive)
        try:
            if comic.testrar() is None:
                goahead = 1
        except rarfile.RarCRCError:
            # add bad files to the list
            print ("Bad RAR CRC: " + archive)
            badfiles.append("Bad RAR CRC: " + archive)
            goahead = 0
        except rarfile.RarWarning:
            print ("RAR file warning: " + archive)
            badfiles.append("RAR file warning: " + archive)
            goahead = 1
    elif (kind == 3):
        print ("Bad file: " + archive)
        goahead = 0
    else:
        print("totally unexpected input! exiting.")
        os._exit(1)

    if goahead:
        # sort the list of files in the comic by name
        # cb? is not a real filetype and relies on 
        # the pages being in correct name order. so
        # the first image file we encounter is likely
        # the cover image
        contents = sorted(comic.namelist())
        #print (contents)
        found_image = 0
        current_image = ''
        # find first image in the sorted list
        patterns = ['*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.png']
        for item in contents:
            pats = re.compile('|'.join(fnmatch.translate(p) for p in patterns), re.IGNORECASE)
            # once we have it, let's operate!
            if pats.match(item):
                found_image = 1

                # open the comic object and a binary filehandle
                filelikeobject = comic.open(item)
                # this returns the bytes of the file
                binaryfile = comic.read(item)

                # do some name mangling so that we can name the image as
                # the name of the archive, in case anyone wants to know
                # which comic the image is from.
                comic_name, comic_ext = os.path.splitext(archive)
                comic_name = os.path.basename(comic_name.decode("utf-8"))
                extracted_name, extracted_ext = os.path.splitext(item)
                #extracted_name = os.path.basename(extracted_name.decode("utf-8"))
                extracted_name = os.path.basename(extracted_name)
                finaldest = destination_dir + '/' + comic_name + extracted_ext
                plaindest = comic_name + extracted_ext

                # do the actual writing
                print (archive.decode("utf-8") + " is valid, saving " + extracted_name + " as " + plaindest)
                newfile = open(finaldest, 'wb+')
                newfile.write(binaryfile)
                newfile.close()
                comic.close()

                break
        if not found_image:
            print ("never found a valid imagetype in " + current_image)
            os._exit(1)
        

def main():
    parser = parse_the_args()
    args = parser.parse_args()

    if os.path.isdir(args.source):
        source_dir = args.source
        if args.destination == None:
            destination_dir = "./comic_covers"
        else:
            destination_dir = args.destination

        destination_dir = test_output(destination_dir)
        all_comics = find_all_files(source_dir)
        #print ("all comics are")
        #print (all_comics)

        for file in os.listdir(destination_dir):
            item_to_add, item_to_add_ext = os.path.splitext(os.path.basename(file))
            existing_files.append(item_to_add)
            #print ("adding " + item_to_add)
        #print("we have ")
        #print(existing_files)

        for file in all_comics:
            #print ("starting to do skip test")
            if not skip_existing(file):
                #print ("skip test was false")
                #print ("testing archive")
                valid_archive = test_for_cbr_cbz(file)
                #print ("back from testing")
                if (valid_archive > 0):
                    unzip_and_rip(file, valid_archive, source_dir, destination_dir)
                else: 
                    print (file + " not a valid comic archive.")
                    #badfiles.append(archive)

        if badfiles:
            if os.path.exists(destination_dir + '/error.log'):
                badlog = open(destination_dir + '/error.log', 'a')
            else:
                badlog = open(destination_dir + '/error.log', 'w+')
            print ("some archives read were bad. see error.log for details.")
            for line in badfiles:
                badlog.write(line + '\n')
            badlog.close()
    else:
        parser.print_usage()
main()

