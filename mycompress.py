#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Program that compresses files in a given folder and logs actions. """

import daemon
import zipfile
import zlib
import os
import sys
import argparse
import smtplib
import logging
import lockfile
from email.message import EmailMessage

def mailresults(results, to_addr):
    """ Emails results to given address using local host.
    
    This module takes output from the compressfiles function and formats the
    data for email and then sends email to given address using local mail
    server.
    
    args:
        results (dict): dictionary from compressefiles function
        to_addr (str): string detailing email address to send results to
    """
    msgtext = ("Dear recipient,\n \n"
               "The compression program has terminated. Below is a list of \n"
               "files that were compressed, as well as files that were "
               "skipped:\n")
    msg_content = (msgtext + ',\n'.join(results['compressed_files']) + '\n \n' 
                   + 'skipped:\n' + ',\n'.join(results['not_compressed_files'])
                   + '\n \n' 
                   + 'total space saved is {} percent'.format(results['saved_memory']))

    msg = EmailMessage()
    msg.set_content(msg_content)

    msg['Subject'] = 'Compression program results'
    msg['From'] = 'localhost' 
    msg['To'] = to_addr

    # Send the message using local SMTP server.
    try:
        s = smtplib.SMTP('localhost')
        s.connect()
        s.send_message(msg, from_addr='', to_addrs=[to_addr])
        s.quit()
        logging.info('Email message sent to: %s', to_addr)
    except:
        logging.error('Unable to send email message')


def compressfiles(dir_name, thresh=0):
    """ Compresses files inside a directory recursively.
    
    This function takes in a directory and threshold argument and compresses
    all files within that directory recursively. Files that do not fulfill the
    threshold requirement are skipped. Does not compress files that it believes
    are already compressed.
    
    args:
        dir_name (str): Name of the directory to point the function to
        thresh (int): Minimum memory size to consider for compression (in
            bytes)
    
    returns: 
        dictionary with the following fields:
            saved_memory: percentage of memory saved by compression
            saved_bytes: Number of memory bytes saved by compression
            compressed_files: list of files that were compressed
            not_compressed_files: list of files skipped because of threshold or
                already compressed.
    """
    if not thresh:
        thresh = 0
    uncompressed_size = 0
    compressed_size = 0
    compressed_files = []
    not_compressed_files = []
    # direcotry loop and file loop
    for dirpath, _, filelist in os.walk(dir_name):
        if not filelist:
            continue
        for filename in filelist:
            filepath = os.path.join(dirpath, filename)
            filesize = os.stat(filepath).st_size
            uncompressed_size += filesize
            # only non-compressed and non-hidden files are considered
            if filename[0] == '.' or iscompressed(filepath):
                logging.info('%s not compressed. File hidden or already compressed', filepath)
                not_compressed_files.append(filename)
                compressed_size += filesize
                continue
            
            # filesize condition
            if filesize < thresh:
                logging.warning('%s not compressed. Below the filesize threshold.', filepath)
                not_compressed_files.append(filename)
                compressed_size += filesize
                continue
            else:
                zipobj = zipfile.ZipFile(filepath+'.zip', 'w')
                try:
                    zipobj.write(filepath, compress_type=zlib.DEFLATED)
                    compressed_size += zipobj.infolist()[0].compress_size
                    logging.info('%s : compressed', filepath)
                    compressed_files.append(filename)
                    os.remove(filepath)
                except OSError as e: 
                    logging.warning('Compression failed with: '+e.strerror) 

    # save output and return results. Account for empty directory
    results = dict()
    if uncompressed_size == 0:
        results['saved_memory'] = 0
        results['saved_bytes'] = 0
        logging.info('No files were found. Check that right path is given')
    else:
        results['saved_memory'] = (1 - (compressed_size/uncompressed_size))*100.0
        results['saved_bytes'] = uncompressed_size - compressed_size
    results['compressed_files'] = compressed_files
    results['not_compressed_files'] = not_compressed_files

    return results


def iscompressed(filepath):
    """ Tests if the given file is already compressed. 
    
    args:
        filepath (str): file name and location of file in question
    
    returns:
        bool : True for compressed, False for not compressed"""
    return zipfile.is_zipfile(filepath)


def main(directory_path, target_email='', threshold=0):    
    """ Main program """
    logging.info('Begin compression')
    logging.info(os.getcwd())
    result = compressfiles(directory_path, thresh=threshold)
    logging.info('Compression completed')
    mailresults(result, to_addr=target_email)
    logging.info('Ending compression program')


if __name__ == "__main__":
    # Parse arguments from command line
    parser = argparse.ArgumentParser(description='Compresses all files within a directory.')
    parser.add_argument('directory', metavar='D', type=str,
                        help='full or relative path to the directory for compression')
    parser.add_argument('email', type=str,
                        help='Email address to send diagnostics of compression to')
    parser.add_argument('--threshold', type=int,
                        help='Minimum file size to consider (in bytes)')
    parser.add_argument('-v', '--verbosity', action='store_true',
                        help='increase verbosity of compression')
    args = parser.parse_args()
    
    # set basic logging configuration
    if args.verbosity:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s : %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING,
                            format='%(asctime)s - %(levelname)s : %(message)s')

    
    # run compresser as daemon service
    if args.directory and args.email:
        with daemon.DaemonContext(working_directory=os.getcwd(), 
                                  stdout=sys.stdout, 
                                  stderr=sys.stderr):
            main(args.directory, target_email=args.email,
                threshold=args.threshold)
            

