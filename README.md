# mycompress
A short python script for compressing files in Unix. It takes in a directory, 
and it will compress all files inside it and its subdirectories.
Once done, the utility will remove the old files, leaving the compressed ones. 
Then it will send an email with a summary of the files compressed.
The program wil not compress that will not return a favorable compression ratio.

This command line utility behaves like a Daemon tool, so it accepts sigterm signal
