#!./bin/python3

# EXPERIMENTAL
# Used for fully automated way of running powermetrics and YouTube files in browser.

from selenium import webdriver
import os
import subprocess
import time

def loadSafari():
    driver = webdriver.Safari() 
    return driver

def loadChrome():
    options = webdriver.ChromeOptions()

    # Control whether the VP9 experimental flag chrome://flags/#videotoolbox-vp9-decoding is enabled or disabled
    # @1 is enabled, @2 is disabled
    experimentalFlags = ['videotoolbox-vp9-decoding@2']
    chromeLocalStatePrefs = { 'browser.enabled_labs_experiments' : experimentalFlags}
    options.add_experimental_option('localState',chromeLocalStatePrefs)

    # Block ad that runs before the video. Load uBlock origin on local disk
    path_to_extension = r'/Users/k/Downloads/uBlock0.chromium'
    options.add_argument('load-extension=' + path_to_extension)

    driver = webdriver.Chrome(chrome_options=options)
    return driver

def main():
    start_time = time.time()
    print("Starting at = ", time.ctime(start_time))
    directory_path = os.getcwd()

    time.sleep(5) 

    cmd = "sudo powermetrics -i 1000 --samplers cpu_power,gpu_power -a --hide-cpu-duty-cycle --show-usage-summary --show-extra-power-info -u ./powerLogs/chrome-vp9-hw-off" 
    pr = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    print("Process spawned with PID: %s" % pr.pid)
    pgid = os.getpgid(pr.pid)
    print("Process spawned with Group ID: %s" % pgid)

    # Sleep before the video kicks off
    time.sleep(60)

    driver = loadChrome()
    # driver = loadSafari()

    driver.get("https://www.youtube.com/watch?v=m1jY2VLCRmY") 
    driver.maximize_window()
    # driver.get("https://www.youtube.com/watch?v=N50gs13VJzE") # 5s test video

    driver.find_element_by_css_selector('button.ytp-button.ytp-settings-button').click()
    driver.find_element_by_xpath("//div[contains(text(),'Quality')]").click()

    time.sleep(1)   # you can adjust this time
    quality = driver.find_element_by_xpath("//span[contains(string(),'2160p')]")
    quality.click()

    fullScreenButton = driver.find_element_by_css_selector("button[title='Full screen (f)']")
    driver.execute_script("arguments[0].click();", fullScreenButton)

    # Sleep while the video is running. 143 because the video is 142 seconds. 
    time.sleep(143)
    # driver.close()
    driver.quit()

    # Sleep after the video is done
    time.sleep(60)

    # Kill the powermetrics process
    os.system("sudo pkill -u root powermetrics")

    end_time = time.time()
    print("Ending at = ", time.ctime(end_time))
    print(f"It took {end_time-start_time:.2f} seconds to compute")

if __name__ == "__main__":
    main()
