#! /usr/bin/env python3

import serial
import argparse
import progressbar
from progressbar.bar import ProgressBar
import socket

UDP_IP = "10.55.0.2"
UDP_PORT = 6502

def main():
    parser = argparse.ArgumentParser(description="Read binary data from serial")
    parser.add_argument(
        "-o", "--output-file", help="output filename", type=str, default=None,
    )
    parser.add_argument(
        "-n", "--netcat", help="mirror output to UDP port", action='store_true',
    )
    parser.add_argument(
        "-s", "--size", help="amount of data to download in bytes. Rounded up to the nearest block size.", type=int, default=1024*1024,
    )
    args = parser.parse_args()

    # fall back to file if neither output format is selected
    if args.netcat == False and args.output_file == None:
        output_file = 'trng.bin'
    elif args.output_file != None:
        output_file = args.output_file
    else:
        output_file = None

    if args.netcat:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect((UDP_IP, UDP_PORT))

    if output_file != None:
        f = open(output_file, 'wb')

    BLOCKSIZE = 64 * 1024
    blocks = args.size // BLOCKSIZE
    if args.size % BLOCKSIZE != 0:
        blocks += 1

    with serial.Serial('/dev/ttyACM0', 460800, timeout=60) as ser:
        progress = ProgressBar(
            min_value=0, max_value=blocks * BLOCKSIZE,
            widgets=[
                progressbar.DataSize(),
                progressbar.FileTransferSpeed(),
                progressbar.Percentage(),
                progressbar.ETA()
            ]
        ).start()
        downloaded = 0
        for b in range(blocks):
            try:
                s = ser.read(BLOCKSIZE)
            except:
                print("Error occured while reading from serial port, aborting")
                exit(1)
            if output_file != None:
                f.write(s)
            if args.netcat:
                packets = [s[i:i+512] for i in range(0, len(s), 512)]
                for packet in packets:
                   sock.send(packet)
            downloaded += BLOCKSIZE
            progress.update(downloaded)
        progress.finish()
        print("Downloaded {} bytes".format(blocks * BLOCKSIZE))

if __name__ == "__main__":
    main()
    exit(0)
   
