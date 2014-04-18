#!/usr/bin/python

import argparse
import fnmatch
import logging
import os
import rarfile
import re
import string
import zipfile

# source, output dir and global array for unreadable archives

logger = logging.getLogger('simple_example')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('debug.log')
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

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
    logger.debug("entering dirtest")
    if not os.path.exists(path):
        os.makedirs(path)
    return path

# walk the folder tree and find all files marked as comic archives
def find_all_files(path):
    logger.debug("entering find all files")
    filelist = []
    for root, dirnames, filenames in os.walk(path):
        for filename in filenames:
            if (fnmatch.fnmatch(filename, '*.cbz')) or (fnmatch.fnmatch(filename, '*.cbr')) or (fnmatch.fnmatch(filename, '*.zip')) or (fnmatch.fnmatch(filename, '*.rar')):
                filelist.append(os.path.join(root, filename))

    return filelist

# grab all existing files and put them in a list
def skip_existing(testfile):
    logger.debug("testing " + testfile + " against existing files in archive")
    for item in existing_files:
        against, against_ext = os.path.splitext(os.path.basename(testfile))
        if (item == against):
            logger.info(testfile + " is valid, but already exists. skipping!")
            return 1
    return 0

# do a test for cbz or cbr since we can't rely on file extensions to be true
def test_for_cbr_cbz(incoming_archive):
    r = 0
    if zipfile.is_zipfile(incoming_archive):
        logger.debug(incoming_archive + " is a zip")
        r = 1
    elif rarfile.is_rarfile(incoming_archive):
        logger.debug(incoming_archive + " is a rar")
        r = 2
    else:
        logger.warn(incoming_archive + "is neither a zip nor a rar!")
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
                logger.debug("zipfile tested ok: " + archive)
                goahead = 1
        except zipfile.BadZipfile:
            logger.error("Bad Zip: " + archive)
            goahead = 0
        except:
            logger.warn("unspecified zip error:" + archive)
            goahead = 1
    # otherwise, it must be a rar
    elif (kind == 2):
        comic = rarfile.RarFile(archive)
        try:
            if comic.testrar() is None:
                logger.debug("rarfile tested ok: " + archive)
                goahead = 1
        except rarfile.RarCRCError:
            logger.error("Bad RAR CRC: " + archive)
            goahead = 0
        except rarfile.RarWarning:
            logger.warn("RAR file warning: " + archive)
            goahead = 1
    elif (kind == 3):
        logger.error("Bad file: " + archive)
        goahead = 0
    else:
        logger.critical("totally unexpected input! exiting.")
        os._exit(1)

    if goahead:
        # sort the list of files in the comic by name
        # cb? is not a real filetype and relies on 
        # the pages being in correct name order. so
        # the first image file we encounter is likely
        # the cover image
        contents = sorted(comic.namelist())
        logger.debug("contents of sorted list:")
        logger.debug(contents)
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
                logger.debug("opening archive")
                filelikeobject = comic.open(item)
                # this returns the bytes of the file
                logger.debug("reading file from archive")
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
                logger.info(archive.decode("utf-8") + " is valid, saving " + extracted_name + " as " + plaindest)
                logger.debug("opening binary file for writing")
                newfile = open(finaldest, 'wb+')
                logger.debug("writing binary file")
                newfile.write(binaryfile)
                logger.debug("closing binary file")
                newfile.close()
                logger.debug("closing archive")
                comic.close()
                break

        if not found_image:
            logger.critical("never found a valid imagetype in " + archive)
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
        logger.debug("all comics are")
        logger.debug(all_comics)

        for file in os.listdir(destination_dir):
            item_to_add, item_to_add_ext = os.path.splitext(os.path.basename(file))
            existing_files.append(item_to_add)
            logger.debug("adding " + item_to_add)
        logger.debug("we have the following cover images already:")
        logger.debug(existing_files)

        for file in all_comics:
            logger.debug("starting to do skip test")
            if not skip_existing(file):
                logger.debug("skip test was false")
                logger.debug("testing archive")
                valid_archive = test_for_cbr_cbz(file)
                logger.debug("back from validating archive integrity")
                if (valid_archive > 0):
                    logger.debug("archive is good as far as we can tell, proceeding to delve inside")
                    unzip_and_rip(file, valid_archive, source_dir, destination_dir)
                else: 
                    logger.info("not a valid comic archive: " + file)

        '''
        if badfiles:
            if os.path.exists(destination_dir + '/error.log'):
                badlog = open(destination_dir + '/error.log', 'a')
            else:
                badlog = open(destination_dir + '/error.log', 'w+')
            print ("some archives read were bad. see error.log for details.")
            for line in badfiles:
                badlog.write(line + '\n')
            badlog.close()
        '''
    else:
        parser.print_usage()
main()

