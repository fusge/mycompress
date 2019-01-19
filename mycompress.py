#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Program that compresses files in a given folder and logs actions. """

import daemon
import zipfile
import zlib
import os
import argparse
import smtplib
import logging
from email.message import EmailMessage

# set basic logging configuration
logging.basicConfig(level=logging.DEBUG, filename='compress_logger.log',
                    filemode='w',
                    format='%(asctime)s - %(levelname)s : %(message)s')

def mailresults(results, to_addr):
    msgtext = "Dear recipient,
    The compression program has terminated. Below is a list of files that were compressed, as well as files that were skipped:"
    msg_content = (msgtext + ',\n'.join(results['compressed_files']) + '\n' 
                   + 'skipped:' + ',\n'.join(results['not_compressed_files'])
                   + '\n' 
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
        print('got here')
        s.send_message(msg, from_addr='', to_addrs=[to_addr])
        s.quit()
        logging.info('Email message sent to: %s', to_addr)
    except:
        logging.error('Unable to send email message')


def compressfiles(dir_name, thresh=0):
    if not thresh:
        thresh = 0
    uncompressed_size = 0
    compressed_size = 0
    compressed_files = []
    not_compressed_files = []
    logging.info('Begin compression')
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
                compressed_size += filesize
                continue
            
            # filesize condition
            if filesize < thresh:
                logging.warning('%s not compressed. Below the filesize threshold.', filepath)
                compressed_size += filesize
                continue
            else:
                zipobj = zipfile.ZipFile(filepath+'.zip', 'w')
                try:
                    zipobj.write(filepath, compress_type=zlib.DEFLATED)
                    compressed_size += zipobj.infolist()[0].compress_size
                    logging.info('%s : compressed', filepath)
                    compressed_files.append(filename)
                    print(filepath)
                    os.remove(filepath)
                except OSError as e: 
                    logging.error('Failed with: '+e.strerror) 

    results = dict()
    results['saved_memory'] = (1 - (compressed_size/uncompressed_size))*100.0
    results['compressed_files'] = compressed_files
    results['not_compressed_files'] = not_compressed_files
    return results


def iscompressed(filepath):
    return zipfile.is_zipfile(filepath)


def main(directory_path, target_email='', threshold=0):    
    result = compressfiles(directory_path, thresh=threshold)
    mailresults(result, to_addr=target_email)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compresses all files within a directory.')
    parser.add_argument('directory', metavar='D', type=str,
                        help='full or relative path to the directory for compression')
    parser.add_argument('email', type=str,
                        help='Email address to send results of compression to')
    parser.add_argument('--threshold', type=int,
                        help='Minimum file size to consider (in bytes)')
    args = parser.parse_args()
    if args.directory and args.email:
        main(args.directory, target_email=args.email,
             threshold=args.threshold)

