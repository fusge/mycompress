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
logging.basicConfig(level=logging.DEBUG, filename='comppress_logger.log',
                    filemode='w', format='%(asctime)s - %(levelname)s: %(message)s')

def mailresults(results, to_addr, from_addr='localhost'):
    msg = EmailMessage()
    msg.set_content(results)

    msg['Subject'] = 'Compresser program log'
    msg['From'] = 'localhost'
    msg['To'] = to_addr

    # Send the message using local SMTP server.
    try:
        s = smtplib.SMTP_SSL()
        s.connect()
        s.send_message(msg)
        s.quit()
        logging.info('Email message sent to: %s', to_addr)
    except:
        logging.error('Unable to send email message')

def compressfiles(dir_name, thresh=0):
    uncompressed_size = 0
    compressed_size = 0
    logging.info('Begin compression')
    # direcotry loop and file loop
    for dirpath, _, filelist in os.walk(dir_name):
        if not filelist:
            continue
        for filename in filelist:
            filesize = os.stat(filepath).st_size()
            uncompressed_size += filesize
            filepath = os.path.join(dirpath, filename)
            # only non-compressed and non-hidden files are considered
            if filename[0] == '.' or iscompressed(filepath):
                logging.info('%s not compressed. File hidden or already compressed', filepath)
                compressed_size += filesize
                continue
            
            # filesize condition
            if filesize > thresh:
                logging.warning('%s not compressed. Below the filesize threshold.', filepath)
                compressed_size += filesize
                continue
            else:
                zipobj = zipfile.ZipFile(filepath+'.zip', 'w')
                compression_info = zipobj.getinfo()
                if compression_info.compress_size/filesize > 0.9:
                    logging.warning('%s : not compressed. compression ratio too high.', filepath)
                    compressed_size += filesize
                    continue
                try:
                    zipobj.write(filepath, compress_type=zlib.DEFLATED)
                    compressed_size += zipobj.getinfo().compress_size
                    logging.info('%s : compressed', filepath)
                    os.remove(filepath)
                except:
                    logging.error('%s : Unable to compress file. Could be already opened ')

def iscompressed(filepath):
    return zipfile.is_zipfile(filepath)

def main(directory_path, target_email='', threshold=0):    
    with daemon.DaemonContext():
        compressfiles(directory_path, thresh=threshold)
        mailresults('compress_logger.log', to_addr=target_email)

    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Compresses all files within a directory.')
    parser.add_argument('directory', metavar='D', type=str,
                        help='full or relative path to the directory for compression')
    parser.add_argument('email', type=str,
                        help='Email address to send results of compression to')
    parser.add_argument('--threshold', type=int,
                        help='sum the integers (default: find the max)')
    main(parser.directory, target_email=parser.email, threshold=parser.threshold)
