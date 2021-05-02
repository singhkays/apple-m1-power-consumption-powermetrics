# Apple Silicon M1 Power Consumption Deep Dive Series
This repository is the source code written by me to parse the powermetrics logs and generate charts used in the following blog https://singhkays.com/blog/apple-silicon-m1-video-power-consumption-pt-1/

# Repostiory structure
Here are the various files and folders and their purposes 
1. `powermetrics-parse.py` - This is the main code that is used to parse logs and generate charts
2. `autorun-local-videos.py` - This is an experimental file that I was trying to use to completely automate logging and playing local videos. I didn't use this for the blog as it needs more testing and fine-tuning.
3. `autorun-local-videos.py` - Equivalent of #2 but for testing browser based videos using Selenium
4. `powermetric-logs` - Folder where the `powermetrics-parse.py` script expects to find the logs to parse
5. `outputs` - Folder where the output charts and files are placed

# Contributions and Use
Feel free to use this code to learn or modify for your investigations. All I ask is an attribution to this repo and the accompanying blog @ https://singhkays.com/blog/apple-silicon-m1-video-power-consumption-pt-1/. 

# Contact
I'm fairly active over on Twitter and my DMs are open. Feel free to reach out with questions/comments, etc.
- https://twitter.com/singhkays 
