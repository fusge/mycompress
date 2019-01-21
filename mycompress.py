#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Program that compresses files in a given folder and logs actions. 

The program takes in a directory path and an email address. Compreses all files
within the directory and subdirectories, and sends an email message to the
given email with diagonstic results. For furhter information use -h or --help
option on the command line.
"""

import signal
import zipfile
import zlib
import os
import sys
import argparse
import smtplib
import logging
import daemon
from logging.handlers import SysLogHandler
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
    msgtext = ("Dear recipient,\n\n"
               "The compression program has terminated. Below is a list of \n"
               "files that were compressed, as well as files that were "
               "skipped:\n\nCompressed:\n")
    msg_content = (msgtext + ',\n'.join(results['compressed_files']) + '\n\n'
                   + 'skipped:\n' + ',\n'.join(results['not_compressed_files'])
                   + '\n\n'
                   + 'total space saved is {:.2f} percent'.format(results['saved_memory']))

    msg = EmailMessage()
    msg.set_content(msg_content)

    msg['Subject'] = 'Compression program results'
    msg['From'] = 'localhost'
    msg['To'] = to_addr

    # Send the message using local SMTP server.
    try:
        smtpobj = smtplib.SMTP('localhost')
        smtpobj.connect()
        smtpobj.send_message(msg, from_addr='', to_addrs=[to_addr])
        smtpobj.quit()
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

            # filesize and good compression conditions
            if filesize < thresh:
                logging.warning('%s not compressed. Below the filesize threshold.', filepath)
                not_compressed_files.append(filename)
                compressed_size += filesize
                continue
            elif not compression_ratio(filepath) < 0.95:
                not_compressed_files.append(filename)
                compressed_size += filesize
                logging.warning('%s not compressed. will not produce good '
                                'compression ratio.', filepath)
                continue
            else:
                zipobj = zipfile.ZipFile(filepath+'.zip', 'w')
                try:
                    zipobj.write(filepath, compress_type=zlib.DEFLATED)
                    compressed_size += zipobj.infolist()[0].compress_size
                    logging.info('%s : compressed', filepath)
                    compressed_files.append(filename)
                    os.remove(filepath)
                except OSError as err:
                    logging.warning('Compression failed with: %s', err.strerror)

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


def end_program(signum, frame):
    """ Exits in case of OS signal """
    logging.warning('Process killed with signal %s', signum)
    sys.exit(0)


def compression_ratio(filepath):
    """ estimates compression ratio for given file.

    This function reads a small portion of the input file (10KB) and estimates
    the compression ratio expected from this file.

    args:
        filepath (str): file path to the file

    returns:
        float : estimate percent of file size for compressed file
    """
    compress_ratio = 0
    with open(filepath, 'rb') as fileobj:
        fileobj.seek(int(os.stat(filepath).st_size/2), 0)
        data = fileobj.read(100000)
        compressed_data = zlib.compress(data)
        if sys.getsizeof(data) == 0:
            compress_ratio = 1.0
        else:
            compress_ratio = sys.getsizeof(compressed_data)/sys.getsizeof(data)

    return compress_ratio


def dry_run(dir_name):
    """ Estimates the amount of space that will be saved with compression
    program.

    args:
        dir_name (str): path to directory for estimate

    returns:
        float : percentage of compressed space relative to full file memory
    """
    logging.debug('Estimate compression program memory savings')
    file_bytes = 0
    compressed_bytes = 0
    for dir_path, _, filelist in os.walk(dir_name):
        for filename in filelist:
            filepath = os.path.join(dir_path, filename)
            file_bytes += 1
            comp_ratio = compression_ratio(filepath)
            if comp_ratio > 0.9:
                compressed_bytes += 1
            else:
                compressed_bytes += comp_ratio

    if file_bytes == 0:
        est = 1
    else:
        est = compressed_bytes/file_bytes

    return est


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
                        help=('increase verbosity of logged actions. check '
                              '/dev/log'))
    args = parser.parse_args()

    # set basic logging configuration
    if args.verbosity:
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s : %(message)s')
    else:
        logging.basicConfig(level=logging.WARNING,
                            format='%(asctime)s - %(levelname)s : %(message)s')

    # make sure logging is sent to /var/log/messages using local logger
    logging.getLogger().addHandler(SysLogHandler(address='/dev/log'))

    #run compresser as daemon service
    if args.directory and args.email:
        signalmap = {signal.SIGTERM: end_program,
                     signal.SIGTSTP: end_program}
        estimate = dry_run(args.directory)
        prompt = ('Estimated memory savings is {} percent.'
                  'Continue?[y/n]'.format((1-estimate)*100))
        proceed = input(prompt)
        if proceed == 'y':
            with daemon.DaemonContext(working_directory=os.getcwd(),
                                      signal_map=signalmap):
                main(args.directory, target_email=args.email,
                     threshold=args.threshold)
